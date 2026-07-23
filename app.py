from __future__ import annotations

from datetime import date, datetime, time
import json
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

try:
    import tex_v25_atualizacao as _atualizacao
except Exception:
    _atualizacao = None

from tex_v25_core import CFG, LEAGUES, normalize_zip
from tex_v25_storage import (
    COLUNAS_ANALISES,
    COLUNAS_COTACOES,
    google_configurado,
    salvar_analises,
    salvar_cotacoes,
    url_planilha_configurada,
)
from tex_v26_operacional import VERSION, analyze_batch, operational_columns

ROOT = Path(__file__).resolve().parent
DATA_ZIP = ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip"
ZONE_METRICS = ROOT / "output" / "v25_zone_season_metrics.csv"
FUSO = ZoneInfo("America/Sao_Paulo")

GAME_COLUMNS = [
    "Data", "Hora", "Liga", "Mandante", "Visitante", "Casa de apostas",
    "Cotação mandante", "Cotação empate", "Cotação visitante",
    "Cotação mais de 2,5", "Cotação menos de 2,5",
]

st.set_page_config(
    page_title=VERSION,
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


def now_br() -> datetime:
    return datetime.now(FUSO)


def style() -> None:
    st.markdown(
        """
        <style>
        .block-container{max-width:1440px;padding-top:1rem;padding-bottom:4rem}
        [data-testid="stMetric"]{border:1px solid rgba(120,120,120,.22);border-radius:14px;padding:.7rem}
        [data-testid="stDataFrame"]{border:1px solid rgba(120,120,120,.22);border-radius:12px;overflow:hidden}
        .tex-head{padding:1rem 1.2rem;border-radius:18px;background:linear-gradient(120deg,#111827,#263b5e);color:white;margin-bottom:1rem}
        .tex-head h1{margin:0;font-size:2rem}.tex-head p{margin:.35rem 0 0;color:#dbeafe}
        .box{padding:.9rem 1rem;border-radius:12px;background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.28);margin-bottom:1rem}
        .operar{padding:.9rem 1rem;border-radius:12px;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.35)}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="tex-head"><h1>{VERSION}</h1>'
        '<p>As ligas e os times já estão no aplicativo. Você informa somente data, horário e cotações.</p></div>',
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner="Carregando histórico e catálogo das 24 ligas...")
def load_matches():
    errors: list[str] = []
    if _atualizacao is not None:
        direct_loader = getattr(_atualizacao, "carregar_base_football_data", None)
        if callable(direct_loader):
            try:
                matches, report = direct_loader(date.today())
                return matches, report, "Football-Data.co.uk — histórico direto"
            except Exception as exc:
                errors.append(f"consulta direta: {exc}")
        legacy_loader = getattr(_atualizacao, "carregar_base_com_atualizacao", None)
        if callable(legacy_loader):
            try:
                matches, report, _ = legacy_loader(DATA_ZIP, date.today())
                return matches, report, "Football-Data.co.uk + histórico local"
            except Exception as exc:
                errors.append(f"atualizador compatível: {exc}")
    try:
        matches = normalize_zip(DATA_ZIP, include_incomplete_annual_2026=True)
        return matches, [], "Histórico local de contingência"
    except Exception as local_exc:
        detail = " | ".join(errors) if errors else "sem detalhes"
        raise RuntimeError(
            f"Falha ao carregar histórico. Atualização: {detail}. Local: {local_exc}"
        ) from local_exc


@st.cache_data(show_spinner=False)
def load_zone_metrics() -> pd.DataFrame:
    return pd.read_csv(ZONE_METRICS)


@st.cache_data(show_spinner=False)
def latest_team_catalog(serialized_matches: tuple[tuple[str, int, str, str], ...]) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Devolve apenas os clubes da temporada mais recente de cada liga."""
    rows = pd.DataFrame(serialized_matches, columns=["Code", "Season", "Home", "Away"])
    teams_by_code: dict[str, list[str]] = {}
    season_by_code: dict[str, int] = {}
    for code in LEAGUES:
        league_rows = rows[rows["Code"].eq(code)]
        if league_rows.empty:
            teams_by_code[code] = []
            continue
        latest_season = int(pd.to_numeric(league_rows["Season"], errors="coerce").max())
        latest_rows = league_rows[league_rows["Season"].eq(latest_season)]
        teams = sorted(
            set(latest_rows["Home"].dropna().astype(str))
            | set(latest_rows["Away"].dropna().astype(str))
        )
        teams_by_code[code] = teams
        season_by_code[code] = latest_season
    return teams_by_code, season_by_code


def format_portfolio(frame: pd.DataFrame) -> pd.DataFrame:
    output = operational_columns(frame)
    if output.empty:
        return output
    output["DateParsed"] = pd.to_datetime(output["DateParsed"]).dt.strftime("%d/%m/%Y")
    return output.rename(columns={
        "Decision": "Decisão",
        "WeekID": "Semana",
        "DateParsed": "Data",
        "League": "Liga",
        "Home": "Mandante",
        "Away": "Visitante",
        "MarketName": "Mercado",
        "Selection": "Seleção",
        "ExecutableOdd": "Cotação",
        "MarketProbability": "Prob. mercado",
        "SportsProbability": "Prob. modelo",
        "HistoricalHitRate": "Acerto histórico",
        "HistoricalROI": "ROI histórico",
        "HistoricalBets": "Amostra histórica",
        "Stake": "Entrada",
        "WeeklyRank": "Posição semanal",
        "Reason": "Motivo",
    })


def get_games() -> list[dict]:
    if "games_v271" not in st.session_state:
        st.session_state.games_v271 = []
    return st.session_state.games_v271


def games_frame() -> pd.DataFrame:
    games = get_games()
    return pd.DataFrame(games, columns=GAME_COLUMNS) if games else pd.DataFrame(columns=GAME_COLUMNS)


def game_key(game: dict) -> tuple[str, str, str, str]:
    return (
        str(game.get("Data", "")),
        str(game.get("Liga", "")),
        str(game.get("Mandante", "")),
        str(game.get("Visitante", "")),
    )


def add_or_update_game(game: dict) -> bool:
    games = get_games()
    key = game_key(game)
    for index, current in enumerate(games):
        if game_key(current) == key:
            games[index] = game
            return False
    games.append(game)
    return True


def catalog_records(batch_id: str, batch: pd.DataFrame, bankroll: float) -> list[dict]:
    now = now_br().strftime("%d/%m/%Y %H:%M:%S")
    records: list[dict] = []
    market_map = [
        ("Cotação mandante", "Vitória Casa", lambda row: row["Mandante"], "Resultado final 1X2"),
        ("Cotação empate", "Empate", lambda row: "Empate", "Resultado final 1X2"),
        ("Cotação visitante", "Vitória Fora", lambda row: row["Visitante"], "Resultado final 1X2"),
        ("Cotação mais de 2,5", "Mais de 2.5 gols", lambda row: "Mais de 2.5 gols", "Total de gols 2.5"),
        ("Cotação menos de 2,5", "Menos de 2.5 gols", lambda row: "Menos de 2.5 gols", "Total de gols 2.5"),
    ]
    for row_number, row in batch.iterrows():
        row_id = f"{batch_id}-{row_number + 1:03d}"
        for odd_column, market, selection_fn, group in market_map:
            odd = pd.to_numeric(row.get(odd_column), errors="coerce")
            if pd.isna(odd) or float(odd) <= 1:
                continue
            record = {column: "" for column in COLUNAS_COTACOES}
            record.update({
                "ID Coleta": row_id,
                "Registrado em": now,
                "Casa de apostas": str(row.get("Casa de apostas") or "Não informada"),
                "Liga": str(row.get("Liga") or ""),
                "Jogo": f"{row.get('Mandante', '')} x {row.get('Visitante', '')}",
                "Mandante": str(row.get("Mandante") or ""),
                "Visitante": str(row.get("Visitante") or ""),
                "Data do jogo": str(row.get("Data") or ""),
                "Hora do jogo": str(row.get("Hora") or ""),
                "Mercado": market,
                "Seleção": selection_fn(row),
                "Cotação": float(odd),
                "Grupo do mercado": group,
                "Probabilidade implícita bruta %": 100.0 / float(odd),
                "Banca no momento": bankroll,
                "Perfil": VERSION,
                "Origem": "Aplicativo com seletores",
                "Observação": "Liga e times selecionados no aplicativo; horário e odds informados manualmente.",
            })
            records.append(record)
    return records


def analysis_records(batch_id: str, portfolio: pd.DataFrame, batch: pd.DataFrame, unit_fraction: float) -> list[dict]:
    now = now_br().strftime("%d/%m/%Y %H:%M:%S")
    records: list[dict] = []
    time_map = {
        (str(row["Liga"]), str(row["Mandante"]), str(row["Visitante"]), str(row["Data"])): str(row.get("Hora", ""))
        for _, row in batch.iterrows()
    }
    for index, row in portfolio.iterrows():
        date_text = pd.to_datetime(row.get("DateParsed")).strftime("%d/%m/%Y")
        time_text = time_map.get((str(row.get("League", "")), str(row.get("Home", "")), str(row.get("Away", "")), date_text), "")
        record = {column: "" for column in COLUNAS_ANALISES}
        record.update({
            "ID Análise": f"{batch_id}-{index + 1:03d}",
            "ID Coleta": batch_id,
            "Registrado em": now,
            "Liga": row.get("League", ""),
            "Jogo": f"{row.get('Home', '')} x {row.get('Away', '')}",
            "Mandante": row.get("Home", ""),
            "Visitante": row.get("Away", ""),
            "Data do jogo": pd.to_datetime(row.get("DateParsed")).strftime("%Y-%m-%d"),
            "Hora do jogo": time_text,
            "Casa de apostas": row.get("Source", ""),
            "Origem": "Aplicativo com seletores",
            "Mercado": row.get("Selection", ""),
            "Cotação": row.get("ExecutableOdd", ""),
            "Probabilidade operacional %": float(row.get("SportsProbability", 0)) * 100,
            "Probabilidade Poisson %": float(row.get("SportsProbability", 0)) * 100,
            "Probabilidade empírica %": float(row.get("HistoricalHitRate", 0)) * 100,
            "Probabilidade de mercado ajustada %": float(row.get("MarketProbability", 0)) * 100,
            "Cotação justa": row.get("FairOddSports", ""),
            "Valor esperado %": float(row.get("SportsEV", 0)) * 100,
            "Gols projetados casa": row.get("LambdaHome", ""),
            "Gols projetados fora": row.get("LambdaAway", ""),
            "Gols projetados total": float(row.get("LambdaHome", 0)) + float(row.get("LambdaAway", 0)),
            "Estabilidade": row.get("Decision", ""),
            "Situação": row.get("Decision", ""),
            "Entrada %": unit_fraction * 100 if row.get("Decision") == "OPERAR" else 0,
            "Versão do modelo": VERSION,
            "Configuração JSON": json.dumps({"unit_fraction": unit_fraction}, ensure_ascii=False),
            "Probabilidade mínima exigida %": float(row.get("BreakEvenProbability", 0)) * 100,
            "Diferença modelo–mercado (p.p.)": float(row.get("ProbabilityDifference", 0)) * 100,
            "Amostra histórica": int(row.get("HistoricalBets", 0)),
            "Retorno histórico %": float(row.get("HistoricalROI", 0)) * 100,
            "Motivo da decisão": row.get("Reason", ""),
            "Resultado confirmado": "NÃO",
        })
        records.append(record)
    return records


style()
matches, update_report, history_source = load_matches()
zone_metrics = load_zone_metrics()
serialized = tuple(
    (str(item.get("Code", "")), int(item.get("Season", 0)), str(item.get("Home", "")), str(item.get("Away", "")))
    for item in matches
)
teams_by_code, season_by_code = latest_team_catalog(serialized)
league_codes = [code for code in LEAGUES if teams_by_code.get(code)]

with st.sidebar:
    st.header("Operação")
    bankroll = st.number_input("Banca atual", min_value=0.0, value=1000.0, step=10.0, format="%.2f")
    unit_percent = st.number_input("Unidade fixa (%)", min_value=0.10, max_value=2.00, value=1.00, step=0.10, format="%.2f")
    weekly_limit = st.number_input("Máximo por semana", min_value=1, max_value=4, value=4, step=1)
    unit_fraction = float(unit_percent) / 100.0
    unit_value = float(bankroll) * unit_fraction
    st.metric("Valor da unidade", f"R$ {unit_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.caption("Sem Kelly, progressão ou multiplicador de confiança.")
    st.divider()
    st.caption(f"Histórico: {history_source}")
    st.caption(f"Partidas históricas: {len(matches):,}".replace(",", "."))
    st.caption(f"Ligas disponíveis: {len(league_codes)}")
    if google_configurado(st.secrets):
        st.success("Planilha Google conectada")
        st.link_button("Abrir planilha", url_planilha_configurada(st.secrets), use_container_width=True)

panel_tab, audit_tab = st.tabs(["MONTAR RODADA", "AUDITORIA E EXPORTAÇÃO"])

with panel_tab:
    st.markdown(
        '<div class="box"><strong>Você não digita liga nem nome de time.</strong><br>'
        'Escolha a liga e os clubes nos seletores. Digite somente data, horário, casa de apostas e cotações.</div>',
        unsafe_allow_html=True,
    )

    league_code = st.selectbox(
        "Liga",
        league_codes,
        format_func=lambda code: LEAGUES[code],
        help="As 24 ligas vêm do núcleo do aplicativo.",
    )
    teams = teams_by_code.get(league_code, [])
    season = season_by_code.get(league_code)
    st.caption(f"Times carregados da temporada mais recente disponível: {season} • {len(teams)} clubes")

    c1, c2 = st.columns(2)
    home = c1.selectbox("Mandante", teams, key=f"home_{league_code}")
    away_options = [team for team in teams if team != home]
    away = c2.selectbox("Visitante", away_options, key=f"away_{league_code}")

    d1, d2, d3 = st.columns([1, 1, 1.5])
    game_date = d1.date_input("Data", value=date.today(), format="DD/MM/YYYY")
    game_time = d2.time_input("Horário", value=time(16, 0), step=300)
    bookmaker = d3.text_input("Casa de apostas", value=st.session_state.get("last_bookmaker_v271", "Pixbet"))

    st.markdown("**Cotações de resultado final — obrigatórias**")
    o1, o2, o3 = st.columns(3)
    odd_home = o1.number_input(f"{home}", min_value=1.01, max_value=100.0, value=1.80, step=0.01, format="%.2f")
    odd_draw = o2.number_input("Empate", min_value=1.01, max_value=100.0, value=3.40, step=0.01, format="%.2f")
    odd_away = o3.number_input(f"{away}", min_value=1.01, max_value=100.0, value=4.20, step=0.01, format="%.2f")

    st.markdown("**Total de 2,5 gols — opcional**")
    g1, g2 = st.columns(2)
    odd_over = g1.number_input("Mais de 2,5", min_value=0.0, max_value=100.0, value=0.0, step=0.01, format="%.2f", help="Deixe 0,00 para não analisar este mercado.")
    odd_under = g2.number_input("Menos de 2,5", min_value=0.0, max_value=100.0, value=0.0, step=0.01, format="%.2f", help="Deixe 0,00 para não analisar este mercado.")

    if st.button("ADICIONAR PARTIDA À RODADA", type="primary", use_container_width=True):
        if (odd_over > 0) != (odd_under > 0):
            st.error("Para analisar total de gols, informe as duas cotações: mais e menos de 2,5.")
        else:
            game = {
                "Data": game_date.strftime("%d/%m/%Y"),
                "Hora": game_time.strftime("%H:%M"),
                "Liga": LEAGUES[league_code],
                "Mandante": home,
                "Visitante": away,
                "Casa de apostas": bookmaker.strip() or "Não informada",
                "Cotação mandante": float(odd_home),
                "Cotação empate": float(odd_draw),
                "Cotação visitante": float(odd_away),
                "Cotação mais de 2,5": float(odd_over) if odd_over > 1 else None,
                "Cotação menos de 2,5": float(odd_under) if odd_under > 1 else None,
            }
            added = add_or_update_game(game)
            st.session_state.last_bookmaker_v271 = bookmaker.strip() or "Pixbet"
            st.session_state.pop("input_v271", None)
            st.session_state.pop("result_v271", None)
            st.session_state.pop("diag_v271", None)
            st.success("Partida adicionada." if added else "Partida atualizada.")
            st.rerun()

    batch = games_frame()
    st.divider()
    st.subheader(f"Rodada montada — {len(batch)} partida(s)")

    if batch.empty:
        st.info("Adicione a primeira partida usando os seletores acima.")
    else:
        display = batch.copy()
        display.insert(2, "Jogo", display["Mandante"] + " x " + display["Visitante"])
        display = display.drop(columns=["Mandante", "Visitante"])
        st.dataframe(display, use_container_width=True, hide_index=True)

        labels = {
            index: f"{row['Data']} {row['Hora']} — {row['Liga']} — {row['Mandante']} x {row['Visitante']}"
            for index, row in batch.iterrows()
        }
        r1, r2 = st.columns([3, 1])
        remove_index = r1.selectbox("Remover partida", options=list(labels), format_func=lambda index: labels[index])
        if r2.button("REMOVER", use_container_width=True):
            del st.session_state.games_v271[int(remove_index)]
            st.session_state.pop("result_v271", None)
            st.session_state.pop("diag_v271", None)
            st.rerun()

        clear_col, analyze_col = st.columns([1, 3])
        if clear_col.button("LIMPAR RODADA", use_container_width=True):
            st.session_state.games_v271 = []
            st.session_state.pop("result_v271", None)
            st.session_state.pop("diag_v271", None)
            st.rerun()

        run = analyze_col.button("ANALISAR E MONTAR CARTEIRA", type="primary", use_container_width=True)
        if run:
            with st.spinner("Analisando a rodada e montando a carteira..."):
                portfolio, diagnostics = analyze_batch(
                    batch,
                    matches,
                    zone_metrics,
                    bankroll=float(bankroll),
                    unit_fraction=unit_fraction,
                    weekly_top_n=int(weekly_limit),
                    cfg=CFG,
                )
            st.session_state.input_v271 = batch.copy()
            st.session_state.result_v271 = portfolio
            st.session_state.diag_v271 = diagnostics
            st.session_state.batch_id_v271 = uuid4().hex[:12]

    portfolio = st.session_state.get("result_v271", pd.DataFrame())
    diagnostics = st.session_state.get("diag_v271", pd.DataFrame())

    if not diagnostics.empty:
        errors = diagnostics[diagnostics["Situação"].eq("ERRO")]
        if not errors.empty:
            st.warning(f"{len(errors)} partida(s) ficaram fora por erro de validação.")
            st.dataframe(errors, use_container_width=True, hide_index=True)

    if not portfolio.empty:
        operating = portfolio[portfolio["Decision"].eq("OPERAR")].copy()
        reserves = portfolio[portfolio["Decision"].eq("RESERVA")].copy()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entradas operacionais", len(operating))
        c2.metric("Reservas", len(reserves))
        c3.metric("Exposição", f"R$ {operating['Stake'].sum():.2f}")
        c4.metric("Ligas com entrada", operating["League"].nunique() if not operating.empty else 0)
        if operating.empty:
            st.warning("Nenhuma seleção passou pela regra operacional nesta rodada.")
        else:
            st.markdown('<div class="operar"><strong>CARTEIRA OPERACIONAL</strong><br>Somente estas linhas recebem entrada.</div>', unsafe_allow_html=True)
            display = format_portfolio(operating)
            st.dataframe(
                display.style.format({
                    "Cotação": "{:.2f}",
                    "Prob. mercado": "{:.2%}",
                    "Prob. modelo": "{:.2%}",
                    "Acerto histórico": "{:.2%}",
                    "ROI histórico": "{:.2%}",
                    "Entrada": "R$ {:.2f}",
                }, na_rep="—"),
                use_container_width=True,
                hide_index=True,
            )
        if not reserves.empty:
            with st.expander(f"Reservas aprovadas fora do limite semanal ({len(reserves)})"):
                st.dataframe(format_portfolio(reserves), use_container_width=True, hide_index=True)

with audit_tab:
    batch = st.session_state.get("input_v271", games_frame())
    portfolio = st.session_state.get("result_v271", pd.DataFrame())
    diagnostics = st.session_state.get("diag_v271", pd.DataFrame())
    if batch.empty:
        st.info("Monte a rodada no primeiro painel para liberar a auditoria.")
    else:
        st.subheader("Arquivos auditáveis")
        st.download_button(
            "BAIXAR RODADA",
            batch.to_csv(index=False).encode("utf-8-sig"),
            "rodada_tex_v27_1.csv",
            "text/csv",
            use_container_width=True,
        )
        if not portfolio.empty:
            export = format_portfolio(portfolio)
            st.download_button(
                "BAIXAR CARTEIRA E RESERVAS",
                export.to_csv(index=False).encode("utf-8-sig"),
                "carteira_operacional_v27_1.csv",
                "text/csv",
                use_container_width=True,
            )
        if not diagnostics.empty:
            st.download_button(
                "BAIXAR DIAGNÓSTICO",
                diagnostics.to_csv(index=False).encode("utf-8-sig"),
                "diagnostico_v27_1.csv",
                "text/csv",
                use_container_width=True,
            )
        st.subheader("Gravar na planilha histórica")
        st.caption("A gravação é por acréscimo e não apaga linhas existentes.")
        if google_configurado(st.secrets):
            if st.button("SALVAR RODADA E DECISÕES NO GOOGLE", use_container_width=True):
                batch_id = st.session_state.get("batch_id_v271", uuid4().hex[:12])
                try:
                    n_quotes = salvar_cotacoes(st.secrets, catalog_records(batch_id, batch, float(bankroll)))
                    n_analysis = salvar_analises(
                        st.secrets,
                        analysis_records(batch_id, portfolio, batch, unit_fraction),
                    ) if not portfolio.empty else 0
                    st.success(f"Salvo: {n_quotes} cotações e {n_analysis} decisões, sem substituir o histórico.")
                except Exception as exc:
                    st.error(f"Falha ao salvar: {exc}")
        else:
            st.info("A conexão Google não está disponível nesta execução.")

st.caption("Ligas e times vêm do catálogo interno; você informa apenas data, horário e odds. Resultados futuros não são garantidos.")
