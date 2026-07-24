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

# Importação por módulo, em vez de uma lista rígida de símbolos.
# Isso evita o ImportError genérico quando app.py e o núcleo ficam em versões
# diferentes durante um deploy parcial do GitHub/Streamlit.
try:
    import tex_v28_core_2814 as _v28
except Exception as exc:
    st.error("O módulo tex_v28_core_2814.py não foi carregado no deploy.")
    st.code(f"{type(exc).__name__}: {exc}", language="text")
    st.info("Confirme no GitHub que app.py e tex_v28_core_2814.py foram enviados no mesmo commit.")
    st.stop()

import tex_operacional_core as _operacional

EXPECTED_CORE_API = "28.1.4"
APP_NAME = getattr(_v28, "APP_NAME", "Tex Statistics V28.1.4")

_REQUIRED_V28 = (
    "analyze_games", "build_ai_summary", "display_frame",
    "load_v28_model", "lot_fingerprint", "validate_market_odds",
)
_REQUIRED_OPERACIONAL = (
    "INPUT_COLUMNS", "enrich_with_standings", "latest_team_catalog",
    "parse_odd", "standings_context",
)
_IMPORT_PROBLEMS = [f"tex_v28_core_2814.{name}" for name in _REQUIRED_V28 if not hasattr(_v28, name)]
_IMPORT_PROBLEMS += [
    f"tex_operacional_core.{name}" for name in _REQUIRED_OPERACIONAL
    if not hasattr(_operacional, name)
]
if getattr(_v28, "CORE_API_VERSION", None) != EXPECTED_CORE_API:
    _IMPORT_PROBLEMS.append(
        f"CORE_API_VERSION esperado {EXPECTED_CORE_API}; encontrado "
        f"{getattr(_v28, 'CORE_API_VERSION', 'ausente')}"
    )

analyze_games = getattr(_v28, "analyze_games", None)
build_ai_summary = getattr(_v28, "build_ai_summary", None)
display_frame = getattr(_v28, "display_frame", None)
load_v28_model = getattr(_v28, "load_v28_model", None)
lot_fingerprint = getattr(_v28, "lot_fingerprint", None)
validate_market_odds = getattr(_v28, "validate_market_odds", None)
INPUT_COLUMNS = getattr(_operacional, "INPUT_COLUMNS", [])
enrich_with_standings = getattr(_operacional, "enrich_with_standings", None)
latest_team_catalog = getattr(_operacional, "latest_team_catalog", None)
parse_odd = getattr(_operacional, "parse_odd", None)
standings_context = getattr(_operacional, "standings_context", None)

ROOT = Path(__file__).resolve().parent
DATA_ZIP = ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip"
MODEL_DIR = ROOT / "model"
FUSO = ZoneInfo("America/Sao_Paulo")

st.set_page_config(page_title=APP_NAME, page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

if _IMPORT_PROBLEMS:
    st.error("Arquivos da V28 desencontrados no deploy.")
    st.code("\n".join(_IMPORT_PROBLEMS), language="text")
    st.info(
        "Substitua juntos app.py, tex_v28_core_2814.py, tex_operacional_core.py e "
        "tex_v25_core.py pelo mesmo patch e faça novo deploy."
    )
    st.stop()


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
        '<p>Sete seleções por partida, correção pelo acerto histórico e até cinco entradas autorizadas por semana.</p></div>',
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


@st.cache_resource(show_spinner="Carregando o modelo de análise...")
def load_model():
    return load_v28_model(MODEL_DIR)


@st.cache_data(show_spinner=False)
def team_catalog(serialized: tuple[tuple[str, int, str, str], ...]):
    rows = [
        {"Code": code, "Season": season, "Home": home, "Away": away}
        for code, season, home, away in serialized
    ]
    return latest_team_catalog(rows)


RESULT_STATE_KEYS = (
    "tex_entries", "tex_readings", "tex_evaluations", "tex_diagnostics",
    "tex_ai_summary", "tex_analysis_fingerprint",
)


def games() -> list[dict]:
    if "tex_games" not in st.session_state:
        st.session_state.tex_games = []
    return st.session_state.tex_games


def invalidate_analysis() -> None:
    for key in RESULT_STATE_KEYS:
        st.session_state.pop(key, None)


def upsert_game(game: dict) -> str:
    key = (game["Data"], game["Código da liga"], game["Mandante"], game["Visitante"])
    for index, current in enumerate(games()):
        current_key = (current["Data"], current["Código da liga"], current["Mandante"], current["Visitante"])
        if key == current_key:
            snapshot = dict(game)
            snapshot["ID"] = current["ID"]
            games()[index] = snapshot
            invalidate_analysis()
            return "atualizada"
    games().append(dict(game))
    invalidate_analysis()
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
                "Observação": "Análise ampliada: mercado sem margem, modelo esportivo, modelo de árvores e correção pelo histórico; cotação com desconto de 2%.",
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
                "Amostra casa": int(row.ProfileSample),
                "Amostra fora": "",
                "Estabilidade": float(row.Reliability),
                "Situação": row.Status,
                "Entrada %": unit_fraction * 100 if row.Status == "AUTORIZADA" else 0,
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
                "Observações": f"Probabilidade original: {float(row.OriginalProbability):.1%}. Casos históricos semelhantes: {int(row.ProfileSample)}. Confiança: {row.SampleConfidence}. Estabilidade: {float(row.Reliability):.1%}. Cotação mínima: {float(row.RequiredOddForOperation):.2f}.",
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
    max_entries = st.number_input("Máximo de entradas por semana", min_value=1, max_value=5, value=5, step=1)
    st.divider()
    st.caption(f"Fonte: {source}")
    st.caption(f"Partidas históricas: {len(matches):,}".replace(",", "."))
    st.caption(f"Ligas: {len(LEAGUES)}")
    st.caption("Validação temporal do motor original, de 2022 a 2025: 893 entradas, média de 3,97 por semana e retorno de +11,62% com o melhor preço disponível.")
    st.caption("Referência de preço da Pinnacle: retorno de +4,36%, ainda com incerteza estatística. Conseguir boa cotação continua essencial.")
    if google_configurado(st.secrets):
        st.success("Planilha Google conectada")
        st.link_button("Abrir planilha", url_planilha_configurada(st.secrets))
    else:
        st.info("Análise funciona normalmente. A gravação Google está desativada.")

st.markdown(
    '<div class="rule-box"><b>Análise ampliada:</b> resultado final, mais ou menos de 2,5 gols e ambas marcam concorrem entre si. '
    'A probabilidade é corrigida pelo acerto de previsões históricas semelhantes. O aplicativo autoriza no máximo uma seleção por jogo e cinco por semana.</div>',
    unsafe_allow_html=True,
)

st.subheader("1. Adicionar partidas")
league_names = list(LEAGUES.values())
name_to_code = {name: code for code, name in LEAGUES.items()}

if st.session_state.pop("tex_flash", None):
    st.success(st.session_state.pop("tex_flash_message", "Partida salva."))
form_version = int(st.session_state.get("tex_form_version", 0))

with st.form(f"game_form_{form_version}", clear_on_submit=False):
    row1 = st.columns([1.1, 0.8, 1.8, 1.8, 1.8])
    game_date = row1[0].date_input("Data", value=date.today(), key=f"game_date_{form_version}")
    game_time = row1[1].time_input("Horário", value=time(16, 0), key=f"game_time_{form_version}")
    league_name = row1[2].selectbox("Liga", league_names, key=f"league_{form_version}")
    code = name_to_code[league_name]
    available_teams = teams_by_code.get(code, [])
    home = row1[3].selectbox("Mandante", available_teams, key=f"home_{form_version}_{code}") if available_teams else ""
    away_options = [team for team in available_teams if team != home]
    away = row1[4].selectbox("Visitante", away_options, key=f"away_{form_version}_{code}") if away_options else ""

    bookmaker = st.text_input("Casa de apostas", value="Pixbet", key=f"bookmaker_{form_version}")
    include_1x2, include_ou, include_btts = st.columns(3)
    with include_1x2:
        use_1x2 = st.checkbox("Resultado final 1X2", value=True, key=f"use_1x2_{form_version}")
        if use_1x2:
            a, b, c = st.columns(3)
            odd_h = a.number_input("Cotação do mandante", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_h_{form_version}")
            odd_d = b.number_input("Cotação do empate", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_d_{form_version}")
            odd_a = c.number_input("Cotação do visitante", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_a_{form_version}")
        else:
            odd_h = odd_d = odd_a = 0.0
    with include_ou:
        use_ou = st.checkbox("Mais/menos de 2,5 gols", value=True, key=f"use_ou_{form_version}")
        if use_ou:
            a, b = st.columns(2)
            odd_o = a.number_input("Cotação de mais de 2,5", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_o_{form_version}")
            odd_u = b.number_input("Cotação de menos de 2,5", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_u_{form_version}")
        else:
            odd_o = odd_u = 0.0
    with include_btts:
        use_btts = st.checkbox("Ambas marcam", value=True, key=f"use_btts_{form_version}")
        if use_btts:
            a, b = st.columns(2)
            odd_by = a.number_input("Cotação — Sim", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_by_{form_version}")
            odd_bn = b.number_input("Cotação — Não", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_bn_{form_version}")
        else:
            odd_by = odd_bn = 0.0

    submitted = st.form_submit_button("ADICIONAR OU ATUALIZAR PARTIDA", type="primary", use_container_width=True)
    if submitted:
        if not home or not away or home == away:
            st.error("Selecione duas equipes diferentes.")
        elif not any((use_1x2, use_ou, use_btts)):
            st.error("Ative ao menos um mercado.")
        else:
            try:
                if use_1x2:
                    validate_market_odds("1X2", [odd_h, odd_d, odd_a])
                if use_ou:
                    validate_market_odds("OU25", [odd_o, odd_u])
                if use_btts:
                    validate_market_odds("BTTS", [odd_by, odd_bn])
            except ValueError as exc:
                st.error(str(exc))
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
                    "Odd mandante": float(odd_h) if use_1x2 else None,
                    "Odd empate": float(odd_d) if use_1x2 else None,
                    "Odd visitante": float(odd_a) if use_1x2 else None,
                    "Odd mais de 2,5": float(odd_o) if use_ou else None,
                    "Odd menos de 2,5": float(odd_u) if use_ou else None,
                    "Odd ambas marcam — Sim": float(odd_by) if use_btts else None,
                    "Odd ambas marcam — Não": float(odd_bn) if use_btts else None,
                }
                action = upsert_game(game)
                st.session_state.tex_form_version = form_version + 1
                st.session_state.tex_flash = True
                st.session_state.tex_flash_message = (
                    f"Partida {action}: {home} x {away}. A análise anterior foi invalidada e "
                    "os campos de cotações foram reiniciados para impedir reaproveitamento entre jogos."
                )
                st.rerun()

st.subheader("2. Partidas do lote")
if not games():
    st.info("Adicione a primeira partida acima.")
else:
    visible = games_frame().copy()
    visible["Jogo"] = visible["Mandante"] + " x " + visible["Visitante"]
    visible = visible.rename(columns={
        "Odd mandante": "Cotação do mandante",
        "Odd empate": "Cotação do empate",
        "Odd visitante": "Cotação do visitante",
        "Odd mais de 2,5": "Cotação de mais de 2,5",
        "Odd menos de 2,5": "Cotação de menos de 2,5",
        "Odd ambas marcam — Sim": "Cotação de ambas marcam — Sim",
        "Odd ambas marcam — Não": "Cotação de ambas marcam — Não",
    })
    st.dataframe(
        visible[[
            "Data", "Hora", "Liga", "Jogo", "Casa de apostas",
            "Cotação do mandante", "Cotação do empate", "Cotação do visitante",
            "Cotação de mais de 2,5", "Cotação de menos de 2,5",
            "Cotação de ambas marcam — Sim", "Cotação de ambas marcam — Não",
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
        invalidate_analysis()
        st.rerun()
    if clear_col.button("LIMPAR LOTE", use_container_width=True):
        st.session_state.tex_games = []
        invalidate_analysis()
        st.rerun()

    if st.button("ANALISAR TODO O LOTE", type="primary", use_container_width=True):
        current_games = games_frame()
        with st.spinner(
            "Analisando as sete seleções e reconstruindo o histórico de Ambas Marcam. "
            "Na primeira análise de uma liga, isso pode levar mais tempo."
        ):
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
            st.session_state.tex_analysis_fingerprint = lot_fingerprint(current_games)

current_fingerprint = lot_fingerprint(games_frame())
saved_fingerprint = st.session_state.get("tex_analysis_fingerprint")
if saved_fingerprint and saved_fingerprint != current_fingerprint:
    invalidate_analysis()
    st.warning("O lote foi alterado depois da última análise. Os resultados antigos foram descartados; clique em ANALISAR TODO O LOTE novamente.")

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
        "Status", "MarketName", "Selection", "Odd", "EffectiveOdd",
        "OriginalProbability", "DecisionProbability", "HistoricalAdjustment",
        "MarketProbability", "RawSportsProbability", "EmpiricalHitRate",
        "ProfileSample", "SampleConfidence", "Reliability",
        "RequiredOddForOperation", "OddGapToOperation", "ExpectedValue", "Reason",
    ]
    out = frame[[column for column in columns if column in frame.columns]].copy()
    for column in (
        "OriginalProbability", "DecisionProbability", "HistoricalAdjustment",
        "MarketProbability", "RawSportsProbability", "EmpiricalHitRate",
        "Reliability", "ExpectedValue",
    ):
        if column in out:
            out[column] = pd.to_numeric(out[column], errors="coerce") * 100.0
    return out.rename(
        columns={
            "Status": "Situação",
            "MarketName": "Mercado",
            "Selection": "Seleção",
            "Odd": "Cotação atual",
            "EffectiveOdd": "Cotação após desconto de 2%",
            "OriginalProbability": "Probabilidade original",
            "DecisionProbability": "Probabilidade corrigida pelo histórico",
            "HistoricalAdjustment": "Correção histórica",
            "MarketProbability": "Probabilidade do mercado sem margem",
            "RawSportsProbability": "Probabilidade esportiva",
            "EmpiricalHitRate": "Acerto histórico",
            "ProfileSample": "Casos históricos semelhantes",
            "SampleConfidence": "Confiança da amostra",
            "Reliability": "Estabilidade histórica",
            "RequiredOddForOperation": "Cotação mínima",
            "OddGapToOperation": "Folga da cotação",
            "ExpectedValue": "Valor esperado após desconto",
            "Reason": "Motivo",
        }
    )


if not readings.empty or not diagnostics.empty:
    st.subheader("3. Resultado completo")
    analyzed_games = int((diagnostics["Situação"] == "ANALISADO").sum()) if not diagnostics.empty else 0
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Partidas analisadas", analyzed_games)
    m2.metric("Entradas autorizadas", len(entries))
    m3.metric("Máximo semanal", int(max_entries))
    m4.metric("Leituras principais", len(readings))
    m5.metric("Seleções avaliadas", len(evaluations))

    if entries.empty and not readings.empty:
        st.warning(
            "Nenhuma seleção atingiu simultaneamente valor esperado não negativo, histórico suficiente "
            "e confiança moderada ou forte."
        )
    elif not entries.empty:
        week_counts = entries.groupby("WeekID").size().to_dict() if "WeekID" in entries else {}
        st.success(f"{len(entries)} entrada(s) autorizada(s). Distribuição semanal: {week_counts}.")

    st.markdown("### Entradas autorizadas")
    if entries.empty:
        closest = readings.sort_values("OddGapToOperation", ascending=False).head(int(max_entries)).copy()
        st.info("Estas são as seleções mais próximas da cotação mínima:")
        if not closest.empty:
            st.dataframe(evaluation_table(closest), hide_index=True, use_container_width=True)
    else:
        st.dataframe(display_frame(entries), hide_index=True, use_container_width=True)

    if len(games()) < int(max_entries):
        st.info(
            f"O lote contém {len(games())} partida(s). Como existe no máximo uma entrada por jogo, "
            f"o limite físico deste lote é {len(games())}."
        )

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
            st.markdown(f"#### {game_index}. {game['Mandante']} x {game['Visitante']} — {game['Liga']}")
            st.caption(
                f"{pd.to_datetime(game['Data']).strftime('%d/%m/%Y')} às {game['Hora']} | "
                f"Cotações: {game['Casa de apostas']}"
            )

            st.markdown("**Classificação antes da partida**")
            if context.get("Available"):
                c1, c2 = st.columns(2)
                c1.metric(
                    str(game["Mandante"]),
                    f"{context['HomePosition']}º lugar",
                    f"{context['HomePoints']} pontos em {context['HomeGames']} jogos | {context['HomePPG']:.2f} pontos por jogo",
                )
                c2.metric(
                    str(game["Visitante"]),
                    f"{context['AwayPosition']}º lugar",
                    f"{context['AwayPoints']} pontos em {context['AwayGames']} jogos | {context['AwayPPG']:.2f} pontos por jogo",
                )
                with st.expander(f"Ver classificação completa — temporada {context['Season']}"):
                    st.dataframe(context["Table"], hide_index=True, use_container_width=True)
            else:
                st.info("A classificação ainda não pôde ser reconstruída para as duas equipes.")

            if game_reading.empty:
                st.error("A partida não produziu leitura. Consulte o diagnóstico no fim da página.")
                continue

            row = game_reading.iloc[0]
            status = str(row["Status"])
            headline = (
                f"{status}: {row['Selection']} | cotação {float(row['Odd']):.2f} | "
                f"probabilidade corrigida {pct(row['DecisionProbability'])}"
            )
            if status == "AUTORIZADA":
                st.success(headline)
            elif status in ("AGUARDAR COTAÇÃO", "ALTERNATIVA", "QUALIFICADA"):
                st.warning(headline)
            else:
                st.info(headline)

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Probabilidade original", pct(row["OriginalProbability"]))
            p2.metric("Probabilidade corrigida", pct(row["DecisionProbability"]))
            p3.metric("Acerto histórico", pct(row["EmpiricalHitRate"]))
            p4.metric("Probabilidade do mercado", pct(row["MarketProbability"]))

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Casos históricos semelhantes", int(row["ProfileSample"]))
            a2.metric("Confiança da amostra", str(row["SampleConfidence"]))
            a3.metric("Estabilidade histórica", pct(row["Reliability"]))
            a4.metric("Correção histórica", f"{float(row['HistoricalAdjustment']):+.1%}")

            o1, o2, o3, o4 = st.columns(4)
            o1.metric("Cotação atual", f"{float(row['Odd']):.2f}")
            o2.metric("Cotação mínima", f"{float(row['RequiredOddForOperation']):.2f}")
            o3.metric("Folga da cotação", f"{float(row['OddGapToOperation']):+.2f}")
            o4.metric("Valor esperado", pct(row["ExpectedValue"]))

            g1, g2, g3 = st.columns(3)
            g1.metric(f"Gols projetados — {game['Mandante']}", f"{float(row['LambdaHome']):.2f}")
            g2.metric(f"Gols projetados — {game['Visitante']}", f"{float(row['LambdaAway']):.2f}")
            g3.metric("Total projetado", f"{float(row['LambdaHome'] + row['LambdaAway']):.2f}")

            st.write(f"**Motivo da decisão:** {row['Reason']}")
            st.caption(f"Qualidade da amostra: {row['SampleConfidenceReason']}")

            with st.expander("Ver as sete seleções avaliadas", expanded=True):
                st.dataframe(
                    evaluation_table(
                        game_evaluations.sort_values(
                            ["StatusOrder", "Score", "Reliability"], ascending=[True, False, False]
                        )
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

    st.markdown("### Carteira e conferência")
    tab_entries, tab_all, tab_errors, tab_ai = st.tabs(
        ["Entradas autorizadas", "Todas as seleções", "Diagnóstico", "Resumo para IA"]
    )
    with tab_entries:
        if entries.empty:
            closest = readings.sort_values("OddGapToOperation", ascending=False).head(5).copy()
            st.info("Nenhuma entrada autorizada neste lote. Abaixo estão as mais próximas da cotação mínima.")
            st.dataframe(evaluation_table(closest), hide_index=True, use_container_width=True)
        else:
            st.dataframe(display_frame(entries), hide_index=True, use_container_width=True)
    with tab_all:
        st.dataframe(
            evaluation_table(
                evaluations.sort_values(["MatchID", "StatusOrder", "Score"], ascending=[True, True, False])
            ),
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
    st.caption("O clique grava as cotações e todas as probabilidades avaliadas. Analisar não grava automaticamente.")
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
            st.error("A Planilha Google não está conectada nos segredos deste aplicativo.")

    export1, export2, export3 = st.columns(3)
    export1.download_button(
        "BAIXAR PLANILHA DE PROBABILIDADES",
        pd.DataFrame(make_analysis_records(evaluations, unit_percent / 100.0)).to_csv(index=False).encode("utf-8-sig"),
        "probabilidades_lote.csv",
        "text/csv",
        use_container_width=True,
    )
    export2.download_button(
        "BAIXAR PLANILHA DE COTAÇÕES",
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
