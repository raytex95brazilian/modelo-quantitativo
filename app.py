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
from tex_operacional_core import (
    APP_NAME,
    INPUT_COLUMNS,
    analyze_games,
    display_frame,
    latest_team_catalog,
    load_calibration_book,
    no_vig_probabilities,
    parse_odd,
)

ROOT = Path(__file__).resolve().parent
DATA_ZIP = ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip"
CALIBRATION_DIR = ROOT / "calibration"
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
        '<p>Liga e times por seleção. Você digita somente data, horário e odds. 1X2, gols e ambas marcam estão disponíveis.</p></div>',
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


@st.cache_resource(show_spinner=False)
def load_book():
    return load_calibration_book(CALIBRATION_DIR)


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
                "Probabilidade ajustada sem margem %": float(row.MarketProbability) * 100,
                "Banca no momento": bankroll,
                "Perfil": APP_NAME,
                "Origem": "Aplicativo com seletores",
                "Observação": "Liga e times selecionados; data, horário e odds informados manualmente.",
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
                "Origem": "Aplicativo com seletores",
                "Mercado": f"{row.MarketName} — {row.Selection}",
                "Cotação": float(row.Odd),
                "Probabilidade operacional %": float(row.DecisionProbability) * 100,
                "Probabilidade Poisson %": float(row.RawSportsProbability) * 100,
                "Probabilidade empírica %": float(row.CalibratedMarketProbability) * 100,
                "Probabilidade de mercado ajustada %": float(row.MarketProbability) * 100,
                "Cotação justa": 1.0 / max(float(row.DecisionProbability), 1e-9),
                "Valor esperado %": float(row.ExpectedValue) * 100,
                "Gols projetados casa": float(row.LambdaHome),
                "Gols projetados fora": float(row.LambdaAway),
                "Gols projetados total": float(row.LambdaHome + row.LambdaAway),
                "Amostra casa": int(row.ProfileSample),
                "Estabilidade": float(row.Reliability),
                "Situação": row.Status,
                "Entrada %": unit_fraction * 100 if row.Status == "OPERAR" else 0,
                "Versão do modelo": APP_NAME,
                "Probabilidade mínima exigida %": float(row.BreakEvenProbability) * 100,
                "Diferença modelo–mercado (p.p.)": float(row.ModelMarketDifference) * 100,
                "Amostra histórica": int(row.ProfileSample),
                "Motivo da decisão": row.Reason,
                "Observações": "O portão binário da V25 não é usado. O mercado é a âncora e o modelo esportivo é secundário.",
            }
        )
        records.append(record)
    return records


apply_style()

try:
    matches, update_report, source = load_matches()
    calibration_book = load_book()
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
    max_entries = st.number_input("Máximo de entradas no lote", min_value=1, max_value=20, value=4, step=1)
    st.divider()
    st.caption(f"Fonte: {source}")
    st.caption(f"Partidas históricas: {len(matches):,}".replace(",", "."))
    st.caption(f"Ligas: {len(LEAGUES)}")
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
        entries, readings, evaluations, diagnostics = analyze_games(
            games_frame(),
            matches,
            calibration_book,
            bankroll=bankroll,
            unit_fraction=unit_percent / 100.0,
            max_entries=int(max_entries),
        )
        st.session_state.tex_entries = entries
        st.session_state.tex_readings = readings
        st.session_state.tex_evaluations = evaluations
        st.session_state.tex_diagnostics = diagnostics

entries = st.session_state.get("tex_entries", pd.DataFrame())
readings = st.session_state.get("tex_readings", pd.DataFrame())
evaluations = st.session_state.get("tex_evaluations", pd.DataFrame())
diagnostics = st.session_state.get("tex_diagnostics", pd.DataFrame())

if not readings.empty or not diagnostics.empty:
    st.subheader("3. Resultado")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Partidas analisadas", int((diagnostics["Situação"] == "ANALISADO").sum()) if not diagnostics.empty else 0)
    m2.metric("Entradas", len(entries))
    m3.metric("Leituras principais", len(readings))
    m4.metric("Mercados avaliados", len(evaluations))

    tab_entries, tab_readings, tab_all, tab_errors = st.tabs(
        ["Entradas com preço", "Leitura principal de cada jogo", "Todos os mercados", "Diagnóstico"]
    )
    with tab_entries:
        if entries.empty:
            st.warning("Nenhuma odd do lote atingiu o preço mínimo. As melhores leituras continuam disponíveis na próxima aba; o aplicativo não fica vazio como a V25.")
        else:
            st.dataframe(
                display_frame(entries),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Probabilidade operacional": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Probabilidade mínima da odd": st.column_config.NumberColumn(format="%.1f%%"),
                    "Margem estimada": st.column_config.NumberColumn(format="%.1f%%"),
                    "Estabilidade": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Entrada fixa": st.column_config.NumberColumn(format="R$ %.2f"),
                },
            )
    with tab_readings:
        st.caption("Sempre há uma leitura principal por partida. Ela não é automaticamente uma entrada.")
        st.dataframe(display_frame(readings), hide_index=True, use_container_width=True)
    with tab_all:
        st.dataframe(display_frame(evaluations.sort_values(["MatchID", "Score"], ascending=[True, False])), hide_index=True, use_container_width=True)
    with tab_errors:
        st.dataframe(diagnostics, hide_index=True, use_container_width=True)

    if google_configurado(st.secrets):
        if st.button("SALVAR COTAÇÕES E ANÁLISES NA PLANILHA", use_container_width=True):
            try:
                saved_odds = salvar_cotacoes(st.secrets, make_catalog_records(evaluations, bankroll))
                saved_analysis = salvar_analises(st.secrets, make_analysis_records(evaluations, unit_percent / 100.0))
                st.success(f"Salvos: {saved_odds} registros de odds e {saved_analysis} análises.")
            except Exception as exc:
                st.error(f"Não foi possível gravar na planilha: {exc}")
