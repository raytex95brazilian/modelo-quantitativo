from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

try:
    import tex_v25_atualizacao as _atualizacao
except Exception:
    _atualizacao = None

from tex_v25_core import LEAGUES, normalize_zip
from tex_v25_storage import (
    COLUNAS_ANALISES,
    COLUNAS_COTACOES,
    google_configurado,
    salvar_analises,
    salvar_cotacoes,
    url_planilha_configurada,
)
from tex_v28_core import (
    APP_NAME,
    INPUT_COLUMNS,
    analyze_games,
    build_ai_summary,
    display_frame,
    enrich_with_standings,
    latest_team_catalog,
    load_v28_model,
    no_vig_probabilities,
    parse_odd,
    standings_context,
)

ROOT = Path(__file__).resolve().parent
DATA_ZIP = ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip"
MODEL_DIR = ROOT / "model"
FUSO = ZoneInfo("America/Sao_Paulo")

st.set_page_config(page_title=APP_NAME, page_icon="⚽", layout="wide", initial_sidebar_state="expanded")


def now_br() -> datetime:
    return datetime.now(FUSO)


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .block-container{max-width:1500px;padding-top:1rem;padding-bottom:4rem}
        .tex-head{padding:1.15rem 1.25rem;border-radius:18px;background:linear-gradient(125deg,#0f172a,#164e63);color:#fff;margin-bottom:1rem}
        .tex-head h1{margin:0;font-size:2rem}.tex-head p{margin:.45rem 0 0;color:#dbeafe}
        .rule-box{padding:.9rem 1rem;border-radius:13px;border:1px solid rgba(14,116,144,.30);background:rgba(14,116,144,.07);margin:.5rem 0 1rem}
        [data-testid="stMetric"],[data-testid="stDataFrame"]{border:1px solid rgba(120,120,120,.22);border-radius:13px;padding:.45rem}
        .game-card{padding:.85rem 1rem;border:1px solid rgba(120,120,120,.22);border-radius:13px;margin:.35rem 0}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="tex-head"><h1>{APP_NAME}</h1>'
        '<p>Liga e times por seleção. Resultado completo por partida, classificação corrente, confiança das amostras e resumo copiável para IA.</p></div>',
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner="Carregando histórico das 24 ligas...")
def load_matches():
    errors: list[str] = []
    if _atualizacao is not None:
        direct = getattr(_atualizacao, "carregar_base_football_data", None)
        if callable(direct):
            try:
                matches, report = direct(date.today())
                return matches, report, "Football-Data.co.uk — histórico atualizado"
            except Exception as exc:
                errors.append(f"consulta direta: {exc}")
        compatible = getattr(_atualizacao, "carregar_base_com_atualizacao", None)
        if callable(compatible):
            try:
                matches, report, _ = compatible(DATA_ZIP, date.today())
                return matches, report, "Football-Data.co.uk + base local"
            except Exception as exc:
                errors.append(f"atualizador compatível: {exc}")
    try:
        matches = normalize_zip(DATA_ZIP, include_incomplete_annual_2026=True)
        return matches, [], "Base histórica local"
    except Exception as exc:
        details = " | ".join(errors) if errors else "sem retorno do atualizador"
        raise RuntimeError(f"Falha ao carregar a base: {details}. Base local: {exc}") from exc


@st.cache_resource(show_spinner="Carregando motor V28...")
def load_model():
    return load_v28_model(MODEL_DIR)


@st.cache_data(show_spinner=False)
def team_catalog(serialized: tuple[tuple[str, int, str, str], ...]):
    rows = [
        {"Code": code, "Season": season, "Home": home, "Away": away}
        for code, season, home, away in serialized
    ]
    return latest_team_catalog(rows)


def games() -> list[dict]:
    if "tex_games" not in st.session_state:
        st.session_state.tex_games = []
    return st.session_state.tex_games


def upsert_game(game: dict) -> str:
    key = (game["Data"], game["Código da liga"], game["Mandante"], game["Visitante"])
    for index, current in enumerate(games()):
        current_key = (current["Data"], current["Código da liga"], current["Mandante"], current["Visitante"])
        if key == current_key:
            game["ID"] = current["ID"]
            games()[index] = game
            return "atualizada"
    games().append(game)
    return "adicionada"


def games_frame() -> pd.DataFrame:
    return pd.DataFrame(games(), columns=INPUT_COLUMNS) if games() else pd.DataFrame(columns=INPUT_COLUMNS)


def make_catalog_records(evaluations: pd.DataFrame, bankroll: float) -> list[dict]:
    if evaluations.empty:
        return []
    registered = now_br().strftime("%d/%m/%Y %H:%M:%S")
    records: list[dict] = []
    for row in evaluations.itertuples(index=False):
        record = {column: "" for column in COLUNAS_COTACOES}
        record.update(
            {
                "ID Coleta": f"{row.InputID}-{row.Market}-{row.Side}",
                "Registrado em": registered,
                "Casa de apostas": row.Bookmaker,
                "Liga": row.League,
                "Jogo": f"{row.Home} x {row.Away}",
                "Mandante": row.Home,
                "Visitante": row.Away,
                "Data do jogo": pd.Timestamp(row.DateParsed).strftime("%d/%m/%Y"),
                "Hora do jogo": row.Time,
                "Mercado": row.MarketName,
                "Seleção": row.Selection,
                "Cotação": float(row.Odd),
                "Grupo do mercado": row.Market,
                "Mercado completo": "Sim",
                "Probabilidade implícita bruta %": 100.0 / float(row.Odd),
                "Margem do mercado %": max(0.0, (100.0 / float(row.Odd)) - float(row.MarketProbability) * 100),
                "Probabilidade ajustada sem margem %": float(row.MarketProbability) * 100,
                "Banca no momento": bankroll,
                "Perfil": APP_NAME,
                "Origem": "Tex Statistics V28",
                "Observação": "V28: mercado sem margem + Poisson dinâmico + LightGBM; odd efetiva com desconto de 2%.",
                "Temporada": int(getattr(row, "Season", 0) or 0),
                "Posição do mandante": getattr(row, "HomePosition", ""),
                "Posição do visitante": getattr(row, "AwayPosition", ""),
                "Pontos do mandante": getattr(row, "HomePoints", ""),
                "Pontos do visitante": getattr(row, "AwayPoints", ""),
                "Pontos por jogo do mandante": getattr(row, "HomePPG", ""),
                "Pontos por jogo do visitante": getattr(row, "AwayPPG", ""),
            }
        )
        records.append(record)
    return records


def make_analysis_records(evaluations: pd.DataFrame, unit_fraction: float) -> list[dict]:
    if evaluations.empty:
        return []
    registered = now_br().strftime("%d/%m/%Y %H:%M:%S")
    records: list[dict] = []
    for row in evaluations.itertuples(index=False):
        record = {column: "" for column in COLUNAS_ANALISES}
        record.update(
            {
                "ID Análise": f"{row.InputID}-{row.Market}-{row.Side}",
                "ID Coleta": f"{row.InputID}-{row.Market}-{row.Side}",
                "Registrado em": registered,
                "Liga": row.League,
                "Jogo": f"{row.Home} x {row.Away}",
                "Mandante": row.Home,
                "Visitante": row.Away,
                "Data do jogo": pd.Timestamp(row.DateParsed).strftime("%d/%m/%Y"),
                "Hora do jogo": row.Time,
                "Casa de apostas": row.Bookmaker,
                "Origem": "Tex Statistics V28",
                "Mercado": f"{row.MarketName} — {row.Selection}",
                "Cotação": float(row.Odd),
                "Probabilidade operacional %": float(row.DecisionProbability) * 100,
                "Probabilidade Poisson %": float(row.RawSportsProbability) * 100,
                "Probabilidade empírica %": float(row.EmpiricalHitRate) * 100,
                "Probabilidade de mercado ajustada %": float(row.MarketProbability) * 100,
                "Cotação justa": 1.0 / max(float(row.DecisionProbability), 1e-9),
                "Valor esperado %": float(row.ExpectedValue) * 100,
                "Gols projetados casa": float(row.LambdaHome),
                "Gols projetados fora": float(row.LambdaAway),
                "Gols projetados total": float(row.LambdaHome + row.LambdaAway),
                "Amostra casa": int(row.SportsSample),
                "Amostra fora": int(row.SportsSample),
                "Estabilidade": float(row.Reliability),
                "Situação": row.Status,
                "Entrada %": unit_fraction * 100 if row.Status == "OPERAR" else 0,
                "Versão do modelo": APP_NAME,
                "Probabilidade mínima exigida %": float(row.BreakEvenProbability) * 100,
                "Diferença modelo–mercado (p.p.)": float(row.ModelMarketDifference) * 100,
                "Amostra histórica": int(row.ProfileSample),
                "Retorno histórico %": "",
                "Motivo da decisão": row.Reason,
                "Posição do mandante": getattr(row, "HomePosition", ""),
                "Posição do visitante": getattr(row, "AwayPosition", ""),
                "Pontos do mandante": getattr(row, "HomePoints", ""),
                "Pontos do visitante": getattr(row, "AwayPoints", ""),
                "Pontos por jogo do mandante": getattr(row, "HomePPG", ""),
                "Pontos por jogo do visitante": getattr(row, "AwayPPG", ""),
                "Observações": f"Confiança da amostra: {row.SampleConfidence}. Estabilidade: {float(row.Reliability):.1%}. Odd mínima operacional: {float(row.RequiredOddForOperation):.2f}.",
            }
        )
        records.append(record)
    return records


apply_style()

try:
    matches, update_report, source = load_matches()
    v28_model = load_model()
except Exception as exc:
    st.error(str(exc))
    st.stop()

serialized = tuple(
    (str(item["Code"]), int(item["Season"]), str(item["Home"]), str(item["Away"]))
    for item in matches
)
teams_by_code, season_by_code = team_catalog(serialized)

with st.sidebar:
    st.header("Operação")
    bankroll = st.number_input("Banca atual (R$)", min_value=0.0, value=1000.0, step=10.0)
    unit_percent = st.number_input("Unidade fixa (%)", min_value=0.1, max_value=2.0, value=1.0, step=0.1)
    max_entries = st.number_input("Alvo de entradas por semana", min_value=3, max_value=5, value=4, step=1)
    st.divider()
    st.caption(f"Fonte: {source}")
    st.caption(f"Partidas históricas: {len(matches):,}".replace(",", "."))
    st.caption(f"Ligas: {len(LEAGUES)}")
    st.caption("Walk-forward 2022–2025: 893 entradas | 3,97/semana | ROI +11,62% usando melhor preço com desconto de 2%.")
    st.caption("Proxy Pinnacle: ROI +4,36%; intervalo bootstrap cruza zero. Preço competitivo é obrigatório.")
    if google_configurado(st.secrets):
        st.success("Planilha Google conectada")
        st.link_button("Abrir planilha", url_planilha_configurada(st.secrets))
    else:
        st.info("Análise funciona normalmente. A gravação Google está desativada.")

st.markdown(
    '<div class="rule-box"><b>Correção do fracasso da V25:</b> não existe mais o portão histórico que bloqueava quase tudo. '
    'Cada jogo sempre recebe uma leitura principal. A indicação <b>OPERAR</b> é separada e só aparece quando a odd também supera o preço mínimo.</div>',
    unsafe_allow_html=True,
)

st.subheader("1. Adicionar partidas")
league_names = list(LEAGUES.values())
name_to_code = {name: code for code, name in LEAGUES.items()}

with st.form("game_form", clear_on_submit=False):
    row1 = st.columns([1.1, 0.8, 1.8, 1.8, 1.8])
    game_date = row1[0].date_input("Data", value=date.today())
    game_time = row1[1].time_input("Horário", value=time(16, 0))
    league_name = row1[2].selectbox("Liga", league_names)
    code = name_to_code[league_name]
    available_teams = teams_by_code.get(code, [])
    home = row1[3].selectbox("Mandante", available_teams, key=f"home_{code}") if available_teams else ""
    away_options = [team for team in available_teams if team != home]
    away = row1[4].selectbox("Visitante", away_options, key=f"away_{code}") if away_options else ""

    bookmaker = st.text_input("Casa de apostas", value="Pixbet")
    include_1x2, include_ou, include_btts = st.columns(3)
    with include_1x2:
        use_1x2 = st.checkbox("Resultado final 1X2", value=True)
        if use_1x2:
            a, b, c = st.columns(3)
            odd_h = a.number_input("Odd mandante", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            odd_d = b.number_input("Odd empate", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            odd_a = c.number_input("Odd visitante", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        else:
            odd_h = odd_d = odd_a = 0.0
    with include_ou:
        use_ou = st.checkbox("Mais/menos de 2,5 gols", value=True)
        if use_ou:
            a, b = st.columns(2)
            odd_o = a.number_input("Odd mais de 2,5", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            odd_u = b.number_input("Odd menos de 2,5", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        else:
            odd_o = odd_u = 0.0
    with include_btts:
        use_btts = st.checkbox("Ambas marcam", value=True)
        if use_btts:
            a, b = st.columns(2)
            odd_by = a.number_input("Odd ambas — Sim", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            odd_bn = b.number_input("Odd ambas — Não", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        else:
            odd_by = odd_bn = 0.0

    submitted = st.form_submit_button("ADICIONAR OU ATUALIZAR PARTIDA", type="primary", use_container_width=True)
    if submitted:
        if not home or not away or home == away:
            st.error("Selecione duas equipes diferentes.")
        elif not any((use_1x2, use_ou, use_btts)):
            st.error("Ative ao menos um mercado.")
        else:
            game = {
                "ID": uuid4().hex[:12],
                "Data": game_date.isoformat(),
                "Hora": game_time.strftime("%H:%M"),
                "Código da liga": code,
                "Liga": league_name,
                "Mandante": home,
                "Visitante": away,
                "Casa de apostas": bookmaker.strip() or "Não informada",
                "Odd mandante": odd_h if use_1x2 else None,
                "Odd empate": odd_d if use_1x2 else None,
                "Odd visitante": odd_a if use_1x2 else None,
                "Odd mais de 2,5": odd_o if use_ou else None,
                "Odd menos de 2,5": odd_u if use_ou else None,
                "Odd ambas marcam — Sim": odd_by if use_btts else None,
                "Odd ambas marcam — Não": odd_bn if use_btts else None,
            }
            action = upsert_game(game)
            st.success(f"Partida {action}: {home} x {away}.")

st.subheader("2. Partidas do lote")
if not games():
    st.info("Adicione a primeira partida acima.")
else:
    visible = games_frame().copy()
    visible["Jogo"] = visible["Mandante"] + " x " + visible["Visitante"]
    st.dataframe(
        visible[[
            "Data", "Hora", "Liga", "Jogo", "Casa de apostas",
            "Odd mandante", "Odd empate", "Odd visitante",
            "Odd mais de 2,5", "Odd menos de 2,5",
            "Odd ambas marcam — Sim", "Odd ambas marcam — Não",
        ]],
        hide_index=True,
        use_container_width=True,
    )
    remove_col, clear_col = st.columns([3, 1])
    labels = [f"{index + 1}. {item['Mandante']} x {item['Visitante']} — {item['Liga']}" for index, item in enumerate(games())]
    remove_label = remove_col.selectbox("Remover partida", ["Nenhuma"] + labels)
    if remove_col.button("REMOVER SELECIONADA", use_container_width=True) and remove_label != "Nenhuma":
        index = labels.index(remove_label)
        games().pop(index)
        st.rerun()
    if clear_col.button("LIMPAR LOTE", use_container_width=True):
        st.session_state.tex_games = []
        for key in ("tex_entries", "tex_readings", "tex_evaluations", "tex_diagnostics"):
            st.session_state.pop(key, None)
        st.rerun()

    if st.button("ANALISAR TODO O LOTE", type="primary", use_container_width=True):
        current_games = games_frame()
        entries, readings, evaluations, diagnostics = analyze_games(
            current_games,
            matches,
            v28_model,
            bankroll=bankroll,
            unit_fraction=unit_percent / 100.0,
            max_entries=int(max_entries),
        )
        entries = enrich_with_standings(entries, current_games, matches)
        readings = enrich_with_standings(readings, current_games, matches)
        evaluations = enrich_with_standings(evaluations, current_games, matches)
        st.session_state.tex_entries = entries
        st.session_state.tex_readings = readings
        st.session_state.tex_evaluations = evaluations
        st.session_state.tex_diagnostics = diagnostics
        st.session_state.tex_ai_summary = build_ai_summary(
            current_games, readings, evaluations, diagnostics, matches
        )

entries = st.session_state.get("tex_entries", pd.DataFrame())
readings = st.session_state.get("tex_readings", pd.DataFrame())
evaluations = st.session_state.get("tex_evaluations", pd.DataFrame())
diagnostics = st.session_state.get("tex_diagnostics", pd.DataFrame())
ai_summary = st.session_state.get("tex_ai_summary", "")


def pct(value: float) -> str:
    return f"{float(value):.1%}"


def money(value: float) -> str:
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def evaluation_table(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    columns = [
        "Status", "MarketName", "Selection", "Odd", "EffectiveOdd", "MarketProbability",
        "CalibratedSportsProbability", "DecisionProbability", "EmpiricalHitRate",
        "ProfileSample", "SampleConfidence", "Reliability",
        "RequiredOddForOperation", "OddGapToOperation", "ExpectedValue", "Reason",
    ]
    out = frame[[column for column in columns if column in frame.columns]].copy()
    for column in (
        "MarketProbability", "CalibratedSportsProbability", "DecisionProbability",
        "EmpiricalHitRate", "Reliability", "ExpectedValue",
    ):
        if column in out:
            out[column] = pd.to_numeric(out[column], errors="coerce") * 100.0
    return out.rename(
        columns={
            "Status": "Situação",
            "MarketName": "Mercado",
            "Selection": "Seleção",
            "Odd": "Odd atual",
            "EffectiveOdd": "Odd efetiva (-2%)",
            "MarketProbability": "Mercado sem margem",
            "CalibratedSportsProbability": "Poisson dinâmico",
            "DecisionProbability": "Probabilidade V28",
            "EmpiricalHitRate": "Acerto empírico da faixa",
            "ProfileSample": "Amostra",
            "SampleConfidence": "Confiança da amostra",
            "Reliability": "Estabilidade OOS",
            "RequiredOddForOperation": "Odd mínima operacional",
            "OddGapToOperation": "Diferença da odd",
            "ExpectedValue": "EV após desconto",
            "Reason": "Motivo",
        }
    )


if not readings.empty or not diagnostics.empty:
    st.subheader("3. Resultado completo")
    analyzed_games = int((diagnostics["Situação"] == "ANALISADO").sum()) if not diagnostics.empty else 0
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Partidas analisadas", analyzed_games)
    m2.metric("Entradas V28", len(entries))
    m3.metric("Alvo semanal", int(max_entries))
    m4.metric("Leituras principais", len(readings))
    m5.metric("Mercados avaliados", len(evaluations))

    if entries.empty and not readings.empty:
        st.warning(
            f"Nenhuma cotação atingiu a odd mínima V28 neste lote. As {len(readings)} leituras e os preços necessários aparecem abaixo."
        )
    elif not entries.empty:
        week_counts = entries.groupby("WeekID").size().to_dict() if "WeekID" in entries else {}
        st.success(f"{len(entries)} entrada(s) na carteira. Distribuição semanal: {week_counts}.")

    st.markdown("### Carteira semanal V28")
    if entries.empty:
        closest = readings.sort_values("OddGapToOperation", ascending=False).head(int(max_entries)).copy()
        st.warning(f"0/{int(max_entries)} preços qualificados. O aplicativo não cria entrada com EV negativo. Veja abaixo quanto falta na odd.")
        if not closest.empty:
            st.dataframe(evaluation_table(closest), hide_index=True, use_container_width=True)
    else:
        qualified_weeks = entries.groupby("WeekID").size().to_dict() if "WeekID" in entries else {}
        st.success(f"Carteira formada: {len(entries)} entrada(s). Quantidade por semana: {qualified_weeks}.")
        st.dataframe(
            display_frame(entries),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Probabilidade V28": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Mercado sem margem": st.column_config.NumberColumn(format="%.1f%%"),
                "Poisson dinâmico": st.column_config.NumberColumn(format="%.1f%%"),
                "EV após desconto": st.column_config.NumberColumn(format="%.1f%%"),
                "Acerto OOS": st.column_config.NumberColumn(format="%.1f%%"),
                "Estabilidade": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Entrada fixa": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )
    if len(games()) < int(max_entries):
        st.info(f"O lote contém {len(games())} partida(s); com uma seleção por jogo, o máximo físico é {len(games())}. Para buscar {int(max_entries)} entradas, inclua jogos suficientes das 24 ligas.")

    st.markdown("### Análise de cada partida")
    for game_index, game in enumerate(games(), start=1):
        input_id = str(game["ID"])
        game_reading = readings[readings["InputID"].astype(str).eq(input_id)] if not readings.empty else pd.DataFrame()
        game_evaluations = evaluations[evaluations["InputID"].astype(str).eq(input_id)] if not evaluations.empty else pd.DataFrame()
        context = standings_context(
            matches,
            str(game["Código da liga"]),
            pd.to_datetime(game["Data"]).date(),
            str(game["Mandante"]),
            str(game["Visitante"]),
        )

        with st.container(border=True):
            st.markdown(
                f"#### {game_index}. {game['Mandante']} x {game['Visitante']} — {game['Liga']}"
            )
            st.caption(
                f"{pd.to_datetime(game['Data']).strftime('%d/%m/%Y')} às {game['Hora']} | "
                f"Cotações: {game['Casa de apostas']}"
            )

            st.markdown("**Classificação do campeonato antes da partida**")
            if context.get("Available"):
                c1, c2 = st.columns(2)
                c1.metric(
                    str(game["Mandante"]),
                    f"{context['HomePosition']}º lugar",
                    f"{context['HomePoints']} pts em {context['HomeGames']} jogos | {context['HomePPG']:.2f} PPG",
                )
                c2.metric(
                    str(game["Visitante"]),
                    f"{context['AwayPosition']}º lugar",
                    f"{context['AwayPoints']} pts em {context['AwayGames']} jogos | {context['AwayPPG']:.2f} PPG",
                )
                with st.expander(f"Ver classificação completa — temporada {context['Season']}"):
                    st.dataframe(
                        context["Table"],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Pontos por jogo": st.column_config.NumberColumn(format="%.2f"),
                            "Gols por jogo": st.column_config.NumberColumn(format="%.2f"),
                            "Gols sofridos por jogo": st.column_config.NumberColumn(format="%.2f"),
                        },
                    )
            else:
                st.info(
                    f"A classificação da temporada {context.get('Season', '')} ainda não pôde ser reconstruída "
                    "para as duas equipes com os resultados carregados."
                )

            if game_reading.empty:
                st.error("A partida não produziu leitura. Consulte o diagnóstico no fim da página.")
                continue

            row = game_reading.iloc[0]
            status = str(row["Status"])
            headline = (
                f"{status}: {row['Selection']} | odd {float(row['Odd']):.2f} | "
                f"probabilidade V28 {pct(row['DecisionProbability'])}"
            )
            if status == "OPERAR":
                st.success(headline)
            elif status in ("AGUARDAR PREÇO", "RESERVA", "QUALIFICADA"):
                st.warning(headline)
            else:
                st.info(headline)

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Mercado sem margem", pct(row["MarketProbability"]))
            p2.metric("Poisson dinâmico", pct(row["RawSportsProbability"]))
            p3.metric("Probabilidade V28", pct(row["DecisionProbability"]))
            p4.metric("Acerto empírico da faixa", pct(row["EmpiricalHitRate"]))

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Amostra fora da amostra", int(row["ProfileSample"]))
            a2.metric("Confiança da amostra", str(row["SampleConfidence"]))
            a3.metric("Estabilidade OOS", pct(row["Reliability"]))
            a4.metric("Nível do perfil", str(row["ProfileLevel"]))

            o1, o2, o3, o4 = st.columns(4)
            o1.metric("Odd atual", f"{float(row['Odd']):.2f}")
            o2.metric("Odd mínima operacional", f"{float(row['RequiredOddForOperation']):.2f}")
            o3.metric("Diferença da odd", f"{float(row['OddGapToOperation']):+.2f}")
            o4.metric("EV após desconto", pct(row["ExpectedValue"]))

            g1, g2, g3 = st.columns(3)
            g1.metric(f"Gols projetados — {game['Mandante']}", f"{float(row['LambdaHome']):.2f}")
            g2.metric(f"Gols projetados — {game['Visitante']}", f"{float(row['LambdaAway']):.2f}")
            g3.metric("Total projetado", f"{float(row['LambdaHome'] + row['LambdaAway']):.2f}")

            st.write(f"**Motivo da decisão:** {row['Reason']}")
            st.caption(f"Qualidade da amostra: {row['SampleConfidenceReason']}")

            with st.expander("Ver todos os mercados avaliados", expanded=True):
                st.dataframe(
                    evaluation_table(
                        game_evaluations.sort_values(
                            ["StatusOrder", "Score"], ascending=[True, False]
                        )
                    ),
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Mercado sem margem": st.column_config.NumberColumn(format="%.1f%%"),
                        "Poisson dinâmico": st.column_config.NumberColumn(format="%.1f%%"),
                        "Probabilidade V28": st.column_config.NumberColumn(format="%.1f%%"),
                        "Acerto empírico da faixa": st.column_config.NumberColumn(format="%.1f%%"),
                        "Estabilidade OOS": st.column_config.NumberColumn(format="%.1f%%"),
                        "EV após desconto": st.column_config.NumberColumn(format="%.1f%%"),
                        "Odd atual": st.column_config.NumberColumn(format="%.2f"),
                        "Odd efetiva (-2%)": st.column_config.NumberColumn(format="%.2f"),
                        "Odd mínima operacional": st.column_config.NumberColumn(format="%.2f"),
                        "Diferença da odd": st.column_config.NumberColumn(format="%+.2f"),
                    },
                )

    st.markdown("### Carteira e auditoria")
    tab_entries, tab_all, tab_errors, tab_ai = st.tabs(
        ["Carteira V28", "Todos os mercados", "Diagnóstico", "Resumo para IA"]
    )
    with tab_entries:
        if entries.empty:
            closest = readings.sort_values("OddGapToOperation", ascending=False).head(5).copy()
            st.info("Nenhuma entrada qualificada neste lote. Abaixo estão as leituras mais próximas da odd mínima V28.")
            st.dataframe(evaluation_table(closest), hide_index=True, use_container_width=True)
        else:
            st.dataframe(
                display_frame(entries),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Probabilidade V28": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Probabilidade mínima da odd": st.column_config.NumberColumn(format="%.1f%%"),
                    "Margem estimada": st.column_config.NumberColumn(format="%.1f%%"),
                    "Acerto empírico da faixa": st.column_config.NumberColumn(format="%.1f%%"),
                    "Estabilidade da calibração": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Entrada fixa": st.column_config.NumberColumn(format="R$ %.2f"),
                },
            )
    with tab_all:
        st.dataframe(
            evaluation_table(evaluations.sort_values(["MatchID", "StatusOrder", "Score"], ascending=[True, True, False])),
            hide_index=True,
            use_container_width=True,
        )
    with tab_errors:
        st.dataframe(diagnostics, hide_index=True, use_container_width=True)
    with tab_ai:
        if not ai_summary:
            ai_summary = build_ai_summary(games_frame(), readings, evaluations, diagnostics, matches)
        st.caption("Use o ícone de copiar no canto do bloco ou baixe o arquivo de texto.")
        st.code(ai_summary, language=None, wrap_lines=True)
        st.download_button(
            "BAIXAR RESUMO PARA IA",
            ai_summary.encode("utf-8"),
            "resumo_tex_statistics_para_ia.txt",
            "text/plain",
            use_container_width=True,
        )

    st.subheader("4. Salvar cotações e probabilidades")
    st.caption("O clique grava as odds e todas as probabilidades avaliadas. Analisar não grava automaticamente.")
    if st.button("SALVAR COTAÇÕES E PROBABILIDADES", type="primary", use_container_width=True):
        if google_configurado(st.secrets):
            try:
                saved_odds = salvar_cotacoes(st.secrets, make_catalog_records(evaluations, bankroll))
                saved_analysis = salvar_analises(st.secrets, make_analysis_records(evaluations, unit_percent / 100.0))
                st.success(
                    f"Gravação concluída: {saved_odds} registros de cotações e "
                    f"{saved_analysis} registros de probabilidades."
                )
            except Exception as exc:
                st.error(f"Não foi possível gravar na planilha: {exc}")
        else:
            st.error("A Planilha Google não está conectada nos Secrets deste aplicativo.")

    export1, export2, export3 = st.columns(3)
    export1.download_button(
        "BAIXAR PROBABILIDADES CSV",
        pd.DataFrame(make_analysis_records(evaluations, unit_percent / 100.0)).to_csv(index=False).encode("utf-8-sig"),
        "probabilidades_lote.csv",
        "text/csv",
        use_container_width=True,
    )
    export2.download_button(
        "BAIXAR COTAÇÕES CSV",
        pd.DataFrame(make_catalog_records(evaluations, bankroll)).to_csv(index=False).encode("utf-8-sig"),
        "cotacoes_lote.csv",
        "text/csv",
        use_container_width=True,
    )
    export3.download_button(
        "BAIXAR RESUMO PARA IA",
        (ai_summary or build_ai_summary(games_frame(), readings, evaluations, diagnostics, matches)).encode("utf-8"),
        "resumo_lote_para_ia.txt",
        "text/plain",
        use_container_width=True,
    )
