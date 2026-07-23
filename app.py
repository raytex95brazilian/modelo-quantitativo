from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from tex_v25_core import (
    ANNUAL_CODES,
    CFG,
    LEAGUES,
    VERSION,
    build_current_state,
    evaluate_live_market,
    no_vig_probabilities,
    normalize_zip,
    sports_probabilities_for_match,
)

ROOT = Path(__file__).resolve().parent
DATA_ZIP = ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip"
ZONE_METRICS = ROOT / "output" / "v25_zone_season_metrics.csv"
REGISTRY = ROOT / "output" / "v25_registry.json"

st.set_page_config(page_title="TEX V25", page_icon="📊", layout="wide")
st.title("TEX V25 — Núcleo Simples e Robusto")
st.caption("Sem IA e sem machine learning: mercado sem margem + Poisson/Dixon-Coles + estabilidade histórica de quatro temporadas.")


@st.cache_resource(show_spinner="Carregando as 24 ligas e construindo o estado histórico...")
def load_engine():
    matches = normalize_zip(DATA_ZIP, include_incomplete_annual_2026=True)
    state = build_current_state(matches, CFG)
    zone_metrics = pd.read_csv(ZONE_METRICS)
    teams_by_code = {}
    for code in LEAGUES:
        teams = sorted(
            {
                row["Home"] for row in matches if row["Code"] == code
            }
            | {
                row["Away"] for row in matches if row["Code"] == code
            }
        )
        teams_by_code[code] = teams
    return matches, state, zone_metrics, teams_by_code


matches, state, zone_metrics, teams_by_code = load_engine()
league_to_code = {name: code for code, name in LEAGUES.items()}


def default_season(code: str, reference: date | None = None) -> int:
    reference = reference or date.today()
    if code in ANNUAL_CODES:
        return reference.year
    return reference.year if reference.month >= 7 else reference.year - 1


def side_label(side: str, home: str, away: str) -> str:
    return {
        "H": f"Vitória — {home}",
        "D": "Empate",
        "A": f"Vitória — {away}",
        "O25": "Mais de 2,5 gols",
        "U25": "Menos de 2,5 gols",
    }.get(side, side)


def number_input(label: str, key: str, value: float = 0.0) -> float:
    return st.number_input(label, min_value=0.0, max_value=100.0, value=value, step=0.01, format="%.2f", key=key)


with st.sidebar:
    st.subheader("Regra operacional")
    st.write("Até **4 seleções por semana**, classificadas pela probabilidade sem margem do mercado.")
    st.write("Uma zona só é aceita quando teve **≥60% de acerto**, **ROI ≥2%** e resultado positivo em pelo menos **3 das últimas 4 temporadas**.")
    st.write("A odd conservadora é a melhor cotação encontrada com desconto de **2%**.")
    st.warning("O app pode bloquear todas as seleções de uma partida. Não há preenchimento artificial de entradas.")

individual_tab, batch_tab, audit_tab = st.tabs(["Jogo individual", "Lote semanal", "Auditoria"])

with individual_tab:
    col1, col2, col3 = st.columns([1.4, 1.2, 1.2])
    with col1:
        league_name = st.selectbox("Liga", list(league_to_code), key="individual_league")
        code = league_to_code[league_name]
    with col2:
        season = st.number_input("Temporada inicial", min_value=2016, max_value=2035, value=default_season(code), step=1)
    with col3:
        analysis_date = st.date_input("Data da análise", value=date.today())

    teams = teams_by_code[code]
    c1, c2 = st.columns(2)
    with c1:
        home = st.selectbox("Mandante", teams, key="home_team")
    with c2:
        away_options = [team for team in teams if team != home]
        away = st.selectbox("Visitante", away_options, key="away_team")

    st.markdown("### Odds médias do mercado")
    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        avg_h = number_input("Casa", "avg_h")
    with a2:
        avg_d = number_input("Empate", "avg_d")
    with a3:
        avg_a = number_input("Fora", "avg_a")
    with a4:
        avg_o = number_input("Mais 2,5", "avg_o")
    with a5:
        avg_u = number_input("Menos 2,5", "avg_u")

    st.markdown("### Melhores odds realmente disponíveis")
    b1, b2, b3, b4, b5 = st.columns(5)
    with b1:
        best_h = number_input("Melhor Casa", "best_h")
    with b2:
        best_d = number_input("Melhor Empate", "best_d")
    with b3:
        best_a = number_input("Melhor Fora", "best_a")
    with b4:
        best_o = number_input("Melhor Mais 2,5", "best_o")
    with b5:
        best_u = number_input("Melhor Menos 2,5", "best_u")

    btts1, btts2 = st.columns(2)
    with btts1:
        avg_btts_y = number_input("BTTS Sim — odd média (somente projeção)", "avg_btts_y")
    with btts2:
        avg_btts_n = number_input("BTTS Não — odd média (somente projeção)", "avg_btts_n")

    if st.button("Analisar jogo", type="primary"):
        try:
            sports = sports_probabilities_for_match(code, home, away, state, CFG)
            average_odds = {"H": avg_h, "D": avg_d, "A": avg_a}
            best_odds = {"H": best_h or avg_h, "D": best_d or avg_d, "A": best_a or avg_a}
            if avg_o > 1 and avg_u > 1:
                average_odds.update({"O25": avg_o, "U25": avg_u})
                best_odds.update({"O25": best_o or avg_o, "U25": best_u or avg_u})

            result = evaluate_live_market(code, int(season), home, away, average_odds, best_odds, sports, zone_metrics, CFG)
            if result.empty:
                st.error("Preencha pelo menos as três odds médias de 1X2.")
            else:
                result["Seleção"] = result["Side"].map(lambda value: side_label(value, home, away))
                display = result[
                    [
                        "Status", "Seleção", "MarketProbability", "SportsProbability",
                        "AverageOdd", "BestOdd", "ExecutableOdd", "HistoricalBets",
                        "HistoricalHitRate", "HistoricalROI", "HistoricalEVAtCurrentPrice",
                    ]
                ].rename(
                    columns={
                        "MarketProbability": "Prob. mercado",
                        "SportsProbability": "Prob. esportiva",
                        "AverageOdd": "Odd média",
                        "BestOdd": "Melhor odd",
                        "ExecutableOdd": "Odd conservadora",
                        "HistoricalBets": "Amostra",
                        "HistoricalHitRate": "Acerto histórico",
                        "HistoricalROI": "ROI histórico",
                        "HistoricalEVAtCurrentPrice": "EV histórico no preço",
                    }
                )
                st.dataframe(
                    display.style.format(
                        {
                            "Prob. mercado": "{:.2%}",
                            "Prob. esportiva": "{:.2%}",
                            "Odd média": "{:.2f}",
                            "Melhor odd": "{:.2f}",
                            "Odd conservadora": "{:.2f}",
                            "Acerto histórico": "{:.2%}",
                            "ROI histórico": "{:.2%}",
                            "EV histórico no preço": "{:.2%}",
                        },
                        na_rep="—",
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                m1, m2, m3 = st.columns(3)
                m1.metric("Gols esperados — casa", f"{sports['LambdaHome']:.2f}")
                m2.metric("Gols esperados — fora", f"{sports['LambdaAway']:.2f}")
                m3.metric("BTTS Sim — projeção esportiva", f"{sports['BTTS_Y']:.2%}")
                if avg_btts_y > 1 and avg_btts_n > 1:
                    btts_market = no_vig_probabilities([avg_btts_y, avg_btts_n])
                    st.info(
                        f"BTTS Sim: mercado sem margem {btts_market[0]:.2%}; projeção esportiva {sports['BTTS_Y']:.2%}. "
                        "A V25 não autoriza financeiramente BTTS porque a base histórica fornecida não contém odds antigas desse mercado."
                    )
        except Exception as exc:
            st.error(str(exc))

with batch_tab:
    st.write("Envie os jogos da semana. O app analisa as 24 ligas e retorna **até quatro seleções principais por semana civil**.")
    template = pd.DataFrame(
        [
            {
                "Date": date.today().isoformat(),
                "League": "Inglaterra - Premier League",
                "Home": "Arsenal",
                "Away": "Liverpool",
                "AvgH": 2.10,
                "AvgD": 3.40,
                "AvgA": 3.50,
                "BestH": 2.18,
                "BestD": 3.55,
                "BestA": 3.70,
                "AvgO25": 1.80,
                "AvgU25": 2.00,
                "BestO25": 1.87,
                "BestU25": 2.08,
            }
        ]
    )
    st.download_button("Baixar modelo CSV", template.to_csv(index=False).encode("utf-8-sig"), "modelo_jogos_v25.csv", "text/csv")
    uploaded = st.file_uploader("CSV dos jogos", type=["csv"])
    if uploaded is not None:
        try:
            games = pd.read_csv(uploaded)
            required = {"Date", "League", "Home", "Away", "AvgH", "AvgD", "AvgA", "BestH", "BestD", "BestA"}
            missing = required - set(games.columns)
            if missing:
                raise ValueError("Colunas ausentes: " + ", ".join(sorted(missing)))
            evaluated = []
            for row in games.to_dict(orient="records"):
                league = str(row["League"])
                if league not in league_to_code:
                    continue
                league_code = league_to_code[league]
                match_date = pd.to_datetime(row["Date"]).date()
                match_season = default_season(league_code, match_date)
                sports = sports_probabilities_for_match(league_code, str(row["Home"]), str(row["Away"]), state, CFG)
                average = {"H": float(row["AvgH"]), "D": float(row["AvgD"]), "A": float(row["AvgA"])}
                best = {"H": float(row["BestH"]), "D": float(row["BestD"]), "A": float(row["BestA"])}
                if pd.notna(row.get("AvgO25")) and pd.notna(row.get("AvgU25")):
                    average.update({"O25": float(row["AvgO25"]), "U25": float(row["AvgU25"])})
                    best.update({
                        "O25": float(row.get("BestO25") or row["AvgO25"]),
                        "U25": float(row.get("BestU25") or row["AvgU25"]),
                    })
                analysis = evaluate_live_market(
                    league_code,
                    match_season,
                    str(row["Home"]),
                    str(row["Away"]),
                    average,
                    best,
                    sports,
                    zone_metrics,
                    CFG,
                )
                approved = analysis[analysis["Status"] == "APROVADA"].copy()
                if approved.empty:
                    continue
                approved["DateParsed"] = match_date
                approved["WeekID"] = f"{match_date.isocalendar().year}-{match_date.isocalendar().week:02d}"
                approved["Seleção"] = approved["Side"].map(lambda value, h=row["Home"], a=row["Away"]: side_label(value, str(h), str(a)))
                approved = approved.sort_values(["MarketProbability", "HistoricalHitRate"], ascending=False).head(1)
                evaluated.append(approved)
            if not evaluated:
                st.warning("Nenhuma zona aprovada foi encontrada no lote.")
            else:
                final = pd.concat(evaluated, ignore_index=True)
                final = (
                    final.sort_values(["WeekID", "MarketProbability", "HistoricalHitRate"], ascending=[True, False, False])
                    .groupby("WeekID", as_index=False)
                    .head(CFG.weekly_top_n)
                )
                st.dataframe(
                    final[
                        ["WeekID", "League", "Home", "Away", "Seleção", "MarketProbability", "ExecutableOdd", "HistoricalHitRate", "HistoricalROI"]
                    ].style.format(
                        {
                            "MarketProbability": "{:.2%}",
                            "ExecutableOdd": "{:.2f}",
                            "HistoricalHitRate": "{:.2%}",
                            "HistoricalROI": "{:.2%}",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
        except Exception as exc:
            st.error(str(exc))

with audit_tab:
    registry = pd.read_json(REGISTRY, typ="series")
    test = registry["test"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entradas no teste final", int(test["bets"]))
    c2.metric("Taxa de acerto", f"{test['hit_rate']:.2%}")
    c3.metric("ROI", f"{test['roi']:.2%}")
    c4.metric("Média por semana ativa", f"{test['average_bets_per_active_week']:.2f}")
    st.write(
        f"Teste final: 2022–2025; {int(test['wins'])} vitórias em {int(test['bets'])} seleções; "
        f"lucro de {test['profit_units']:.2f} unidades; drawdown máximo de {test['max_drawdown_units']:.2f} unidades."
    )
    st.warning(
        f"Intervalo bootstrap semanal de 95% do ROI: {test['roi_ci_lower']:.2%} a {test['roi_ci_upper']:.2%}. "
        "O limite inferior ainda cruza zero; o resultado é promissor, não uma garantia de renda."
    )
    st.dataframe(pd.read_csv(ROOT / "output" / "v25_price_stress.csv"), use_container_width=True, hide_index=True)
