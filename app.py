from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
import json

import pandas as pd
import streamlit as st

_MODULE_IMPORT_ERRORS: list[str] = []


def _load_required_module(name: str):
    try:
        return __import__(name)
    except Exception as exc:
        _MODULE_IMPORT_ERRORS.append(f"{name}: {type(exc).__name__}: {exc}")
        return None


try:
    import tex_v25_atualizacao as _atualizacao
except Exception:
    _atualizacao = None

_v25 = _load_required_module("tex_v25_core")
_storage = _load_required_module("tex_v25_storage")
_finance = _load_required_module("tex_v28_finance")
_v28 = _load_required_module("tex_v28_core_2812")
_operacional = _load_required_module("tex_operacional_core")

EXPECTED_CORE_API = "28.1.2"
EXPECTED_STORAGE_API = "28.1.5.1"
EXPECTED_FINANCE_API = "28.1.5.1"
INTERFACE_VERSION = "V28.1.5.1"
APP_NAME = "Tex Statistics V28.1.5.1 — Hotfix de Deploy e Compatibilidade"
CORE_NAME = getattr(_v28, "APP_NAME", "Tex Statistics V28.1.2 — Estado Isolado")
MODEL_VERSION = getattr(_v28, "MODEL_VERSION", "V28.0")
ENGINE_VERSION = getattr(_v28, "ENGINE_VERSION", "V28.1.2-estado-isolado")

_REQUIRED_V25 = ("LEAGUES", "normalize_zip")
_REQUIRED_STORAGE = (
    "COLUNAS_ANALISES", "COLUNAS_COTACOES", "carregar_apostas",
    "google_configurado", "identificadores_analises", "identificadores_apostas",
    "identificadores_cotacoes", "liquidar_aposta", "salvar_analises",
    "salvar_apostas", "salvar_cotacoes", "url_planilha_configurada",
)
_REQUIRED_FINANCE = (
    "COLUNAS_APOSTAS", "atualizar_registro", "carregar_ledger_local",
    "contagens_semanais", "criar_registros_apostas", "identificador_registro",
    "identificadores_partidas_registradas", "liquidar_registro", "mesclar_registros",
    "normalizar_ledger", "reconciliar_ledgers", "resumo_financeiro",
    "salvar_ledger_local",
)
_REQUIRED_V28 = (
    "analyze_games", "build_ai_summary", "display_frame",
    "load_v28_model", "lot_fingerprint", "validate_market_odds",
)
_REQUIRED_OPERACIONAL = (
    "INPUT_COLUMNS", "enrich_with_standings", "latest_team_catalog",
    "parse_odd", "standings_context",
)

_IMPORT_PROBLEMS = list(_MODULE_IMPORT_ERRORS)
for module_name, module, required in (
    ("tex_v25_core", _v25, _REQUIRED_V25),
    ("tex_v25_storage", _storage, _REQUIRED_STORAGE),
    ("tex_v28_finance", _finance, _REQUIRED_FINANCE),
    ("tex_v28_core_2812", _v28, _REQUIRED_V28),
    ("tex_operacional_core", _operacional, _REQUIRED_OPERACIONAL),
):
    if module is not None:
        _IMPORT_PROBLEMS.extend(
            f"{module_name}.{name} ausente" for name in required if not hasattr(module, name)
        )

if _v28 is not None and getattr(_v28, "CORE_API_VERSION", None) != EXPECTED_CORE_API:
    _IMPORT_PROBLEMS.append(
        f"CORE_API_VERSION esperado {EXPECTED_CORE_API}; encontrado "
        f"{getattr(_v28, 'CORE_API_VERSION', 'ausente')}"
    )
if _storage is not None and getattr(_storage, "STORAGE_API_VERSION", None) != EXPECTED_STORAGE_API:
    _IMPORT_PROBLEMS.append(
        f"STORAGE_API_VERSION esperado {EXPECTED_STORAGE_API}; encontrado "
        f"{getattr(_storage, 'STORAGE_API_VERSION', 'ausente')}"
    )
if _finance is not None and getattr(_finance, "FINANCE_API_VERSION", None) != EXPECTED_FINANCE_API:
    _IMPORT_PROBLEMS.append(
        f"FINANCE_API_VERSION esperado {EXPECTED_FINANCE_API}; encontrado "
        f"{getattr(_finance, 'FINANCE_API_VERSION', 'ausente')}"
    )

LEAGUES = getattr(_v25, "LEAGUES", {})
normalize_zip = getattr(_v25, "normalize_zip", None)
COLUNAS_ANALISES = getattr(_storage, "COLUNAS_ANALISES", [])
COLUNAS_COTACOES = getattr(_storage, "COLUNAS_COTACOES", [])
carregar_apostas = getattr(_storage, "carregar_apostas", None)
google_configurado = getattr(_storage, "google_configurado", None)
identificadores_analises = getattr(_storage, "identificadores_analises", None)
identificadores_apostas = getattr(_storage, "identificadores_apostas", None)
identificadores_cotacoes = getattr(_storage, "identificadores_cotacoes", None)
liquidar_aposta = getattr(_storage, "liquidar_aposta", None)
salvar_analises = getattr(_storage, "salvar_analises", None)
salvar_apostas = getattr(_storage, "salvar_apostas", None)
salvar_cotacoes = getattr(_storage, "salvar_cotacoes", None)
url_planilha_configurada = getattr(_storage, "url_planilha_configurada", None)
COLUNAS_APOSTAS = getattr(_finance, "COLUNAS_APOSTAS", [])
atualizar_registro = getattr(_finance, "atualizar_registro", None)
carregar_ledger_local = getattr(_finance, "carregar_ledger_local", None)
contagens_semanais = getattr(_finance, "contagens_semanais", None)
criar_registros_apostas = getattr(_finance, "criar_registros_apostas", None)
identificador_registro = getattr(_finance, "identificador_registro", None)
identificadores_partidas_registradas = getattr(_finance, "identificadores_partidas_registradas", None)
liquidar_registro = getattr(_finance, "liquidar_registro", None)
mesclar_registros = getattr(_finance, "mesclar_registros", None)
normalizar_ledger = getattr(_finance, "normalizar_ledger", None)
reconciliar_ledgers = getattr(_finance, "reconciliar_ledgers", None)
resumo_financeiro = getattr(_finance, "resumo_financeiro", None)
salvar_ledger_local = getattr(_finance, "salvar_ledger_local", None)
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
LOCAL_LEDGER_PATH = ROOT / "data" / "tex_v28_apostas.csv"
CONSERVATIVE_BACKTEST_PATH = ROOT / "backtest" / "V28_1_5_FILTRO_CONSERVADOR_RESUMO.json"
FUSO = ZoneInfo("America/Fortaleza")

st.set_page_config(page_title=APP_NAME, page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

if _IMPORT_PROBLEMS:
    st.error("Arquivos da V28 desencontrados no deploy.")
    st.code("\n".join(_IMPORT_PROBLEMS), language="text")
    st.info(
        "O deploy misturou arquivos de versões diferentes. Substitua TODO o conteúdo da raiz "
        "pelo mesmo pacote V28.1.5.1, confirme tex_v25_storage.py e tex_v28_finance.py no GitHub, "
        "faça commit e execute Reboot app no Streamlit Cloud."
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
        '<p>Análise completa por partida, probabilidade conservadora, carteira limitada e controle financeiro com liquidação.</p></div>',
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Carregando histórico das 24 ligas...", ttl=21600)
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
def load_conservative_backtest_summary() -> dict:
    if not CONSERVATIVE_BACKTEST_PATH.is_file():
        return {}
    try:
        import json

        return json.loads(CONSERVATIVE_BACKTEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


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
        identifier = identificador_registro(row)
        record = {column: "" for column in COLUNAS_COTACOES}
        record.update(
            {
                "ID Coleta": identifier,
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
                "Margem do mercado %": float(getattr(row, "MarketMargin", 0.0)) * 100.0,
                "Probabilidade ajustada sem margem %": float(row.MarketProbability) * 100.0,
                "Banca no momento": float(bankroll),
                "Perfil": CORE_NAME,
                "Origem": APP_NAME,
                "Observação": (
                    "Mercado sem margem, modelo dinâmico de gols, árvores regularizadas e "
                    "desconto operacional de 2%."
                ),
                "Temporada": int(getattr(row, "Season", 0) or 0),
                "Posição do mandante": getattr(row, "HomePosition", ""),
                "Posição do visitante": getattr(row, "AwayPosition", ""),
                "Pontos do mandante": getattr(row, "HomePoints", ""),
                "Pontos do visitante": getattr(row, "AwayPoints", ""),
                "Pontos por jogo do mandante": getattr(row, "HomePPG", ""),
                "Pontos por jogo do visitante": getattr(row, "AwayPPG", ""),
                "Versão da interface": INTERFACE_VERSION,
                "Versão da API do núcleo": EXPECTED_CORE_API,
                "Versão do modelo": MODEL_VERSION,
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
        identifier = identificador_registro(row)
        configuration = {
            "percentual_unidade": float(unit_fraction),
            "desconto_cotacao": float(row.PriceHaircut),
            "modelo": MODEL_VERSION,
            "api_nucleo": EXPECTED_CORE_API,
            "filtro": "probabilidade conservadora e casos semelhantes",
        }
        record = {column: "" for column in COLUNAS_ANALISES}
        record.update(
            {
                "ID Análise": identifier,
                "ID Coleta": identifier,
                "Registrado em": registered,
                "Liga": row.League,
                "Jogo": f"{row.Home} x {row.Away}",
                "Mandante": row.Home,
                "Visitante": row.Away,
                "Data do jogo": pd.Timestamp(row.DateParsed).strftime("%d/%m/%Y"),
                "Hora do jogo": row.Time,
                "Casa de apostas": row.Bookmaker,
                "Origem": APP_NAME,
                "Mercado": f"{row.MarketName} — {row.Selection}",
                "Cotação": float(row.Odd),
                "Probabilidade operacional %": float(row.ConservativeProbability) * 100.0,
                "Probabilidade Poisson %": float(row.RawSportsProbability) * 100.0,
                "Probabilidade empírica %": float(row.EmpiricalHitRate) * 100.0,
                "Probabilidade de mercado ajustada %": float(row.MarketProbability) * 100.0,
                "Cotação justa": 1.0 / max(float(row.ConservativeProbability), 1e-9),
                "Valor esperado %": float(row.ExpectedValue) * 100.0,
                "Gols projetados casa": float(row.LambdaHome),
                "Gols projetados fora": float(row.LambdaAway),
                "Gols projetados total": float(row.LambdaHome + row.LambdaAway),
                "Chance mandante marcar %": float(row.HomeScoreProbability) * 100.0,
                "Chance visitante marcar %": float(row.AwayScoreProbability) * 100.0,
                "Amostra casa": int(row.HomeSample),
                "Amostra fora": int(row.AwaySample),
                "Estabilidade": float(row.Reliability),
                "Situação": row.Status,
                "Entrada %": unit_fraction * 100.0 if row.Status == "OPERAR" else 0.0,
                "Versão do modelo": MODEL_VERSION,
                "Configuração JSON": json.dumps(configuration, ensure_ascii=False, sort_keys=True),
                "Probabilidade mínima exigida %": float(row.BreakEvenProbability) * 100.0,
                "Diferença modelo–mercado (p.p.)": float(row.ModelMarketDifference) * 100.0,
                "Amostra histórica": int(row.ProfileSample),
                "Retorno histórico %": "",
                "Motivo da decisão": row.Reason,
                "Posição do mandante": getattr(row, "HomePosition", ""),
                "Posição do visitante": getattr(row, "AwayPosition", ""),
                "Pontos do mandante": getattr(row, "HomePoints", ""),
                "Pontos do visitante": getattr(row, "AwayPoints", ""),
                "Pontos por jogo do mandante": getattr(row, "HomePPG", ""),
                "Pontos por jogo do visitante": getattr(row, "AwayPPG", ""),
                "Observações": (
                    f"Confiança: {row.SampleConfidence}. Estabilidade: {float(row.Reliability):.1%}. "
                    f"Cotação mínima conservadora: {float(row.RequiredOddForOperation):.2f}."
                ),
                "Versão da interface": INTERFACE_VERSION,
                "Versão da API do núcleo": EXPECTED_CORE_API,
                "Probabilidade conservadora %": float(row.ConservativeProbability) * 100.0,
                "Valor esperado do modelo %": float(row.ModelExpectedValue) * 100.0,
                "Valor esperado conservador %": float(row.ConservativeExpectedValue) * 100.0,
                "Limite conservador dos casos semelhantes %": float(row.SimilarCasesLowerProbability) * 100.0,
                "Código do mercado": row.Market,
                "Código da seleção": row.Side,
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

if "tex_ledger" not in st.session_state:
    try:
        initial_ledger = carregar_ledger_local(LOCAL_LEDGER_PATH)
    except Exception:
        initial_ledger = pd.DataFrame(columns=COLUNAS_APOSTAS)
    if google_configurado(st.secrets):
        try:
            remote_ledger = carregar_apostas(st.secrets)
            initial_ledger = reconciliar_ledgers(remote_ledger, initial_ledger)
            try:
                salvar_ledger_local(LOCAL_LEDGER_PATH, initial_ledger)
            except Exception:
                pass
        except Exception as exc:
            st.session_state.tex_ledger_sync_warning = str(exc)
    st.session_state.tex_ledger = normalizar_ledger(initial_ledger)

ledger = normalizar_ledger(st.session_state.get("tex_ledger"))
registered_week_counts = contagens_semanais(ledger)
registered_match_ids = identificadores_partidas_registradas(ledger)
backtest_summary = load_conservative_backtest_summary()

with st.sidebar:
    st.header("Operação")
    bankroll = st.number_input("Banca informada para a análise (R$)", min_value=0.0, value=1000.0, step=10.0)
    unit_percent = st.number_input("Unidade fixa (%)", min_value=0.1, max_value=2.0, value=1.0, step=0.1)
    max_entries = st.number_input("Máximo de entradas por semana", min_value=1, max_value=5, value=5, step=1)
    st.divider()
    st.caption(f"Fonte: {source}")
    st.caption(f"Partidas históricas: {len(matches):,}".replace(",", "."))
    st.caption(f"Ligas: {len(LEAGUES)}")
    if backtest_summary:
        st.caption(
            "Recalculo retrospectivo do filtro conservador 2022–2025: "
            f"{int(backtest_summary.get('entries', 0))} entradas | "
            f"{float(backtest_summary.get('average_entries_per_week', 0.0)):.2f} por semana | "
            f"retorno de {float(backtest_summary.get('roi', 0.0)):+.2%}."
        )
        st.caption(
            "Verificação operacional retrospectiva; não é novo teste final independente "
            "nem garantia de resultado futuro."
        )
    if registered_week_counts:
        st.caption(f"Apostas já registradas por semana: {registered_week_counts}")
    if st.session_state.get("tex_ledger_sync_warning"):
        st.warning(
            "A planilha não pôde ser sincronizada. O limite semanal está usando somente "
            "o histórico local desta instalação até uma nova sincronização bem-sucedida."
        )
    if google_configurado(st.secrets):
        st.success("Planilha Google conectada")
        st.link_button("Abrir planilha", url_planilha_configurada(st.secrets))
    else:
        st.info("Análise funciona normalmente. A gravação Google está desativada.")

st.markdown(
    '<div class="rule-box"><b>Regra operacional:</b> cada jogo recebe uma leitura principal. '
    'A indicação <b>OPERAR</b> só aparece quando a cotação supera o preço mínimo conservador, '
    'a amostra é suficiente e a estabilidade é aceitável. O máximo semanal não obriga o aplicativo a preencher apostas.</div>',
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
            odd_h = a.number_input("Cotação mandante", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_h_{form_version}")
            odd_d = b.number_input("Cotação empate", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_d_{form_version}")
            odd_a = c.number_input("Cotação visitante", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_a_{form_version}")
        else:
            odd_h = odd_d = odd_a = 0.0
    with include_ou:
        use_ou = st.checkbox("Mais/menos de 2,5 gols", value=True, key=f"use_ou_{form_version}")
        if use_ou:
            a, b = st.columns(2)
            odd_o = a.number_input("Cotação mais de 2,5", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_o_{form_version}")
            odd_u = b.number_input("Cotação menos de 2,5", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_u_{form_version}")
        else:
            odd_o = odd_u = 0.0
    with include_btts:
        use_btts = st.checkbox("Ambas marcam — análise complementar", value=True, key=f"use_btts_{form_version}")
        if use_btts:
            a, b = st.columns(2)
            odd_by = a.number_input("Cotação ambas — Sim", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_by_{form_version}")
            odd_bn = b.number_input("Cotação ambas — Não", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"odd_bn_{form_version}")
        else:
            odd_by = odd_bn = 0.0

    submitted = st.form_submit_button("ADICIONAR OU ATUALIZAR PARTIDA", type="primary", use_container_width=True)
    if submitted:
        game_start = datetime.combine(game_date, game_time, tzinfo=FUSO)
        if not home or not away or home == away:
            st.error("Selecione duas equipes diferentes.")
        elif game_start <= now_br():
            st.error(
                "A partida precisa estar programada para um horário futuro. "
                "O aplicativo é exclusivamente pré-jogo."
            )
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
        "Odd mandante": "Cotação mandante",
        "Odd empate": "Cotação empate",
        "Odd visitante": "Cotação visitante",
        "Odd mais de 2,5": "Cotação mais de 2,5",
        "Odd menos de 2,5": "Cotação menos de 2,5",
        "Odd ambas marcam — Sim": "Cotação ambas marcam — Sim",
        "Odd ambas marcam — Não": "Cotação ambas marcam — Não",
    })
    st.dataframe(
        visible[[
            "Data", "Hora", "Liga", "Jogo", "Casa de apostas",
            "Cotação mandante", "Cotação empate", "Cotação visitante",
            "Cotação mais de 2,5", "Cotação menos de 2,5",
            "Cotação ambas marcam — Sim", "Cotação ambas marcam — Não",
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
        entries, readings, evaluations, diagnostics = analyze_games(
            current_games,
            matches,
            v28_model,
            bankroll=bankroll,
            unit_fraction=unit_percent / 100.0,
            max_entries=int(max_entries),
            existing_week_counts=registered_week_counts,
            existing_match_ids=registered_match_ids,
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
        st.session_state.tex_analysis_fingerprint = lot_fingerprint(
            current_games,
            bankroll,
            unit_percent / 100.0,
            int(max_entries),
            registered_week_counts,
            registered_match_ids,
        )

current_fingerprint = lot_fingerprint(
    games_frame(),
    bankroll,
    unit_percent / 100.0,
    int(max_entries),
    registered_week_counts,
    registered_match_ids,
)
saved_fingerprint = st.session_state.get("tex_analysis_fingerprint")
if saved_fingerprint and saved_fingerprint != current_fingerprint:
    invalidate_analysis()
    st.warning("O lote ou os parâmetros financeiros foram alterados depois da última análise. Os resultados antigos foram descartados; analise novamente.")

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
        "RawSportsProbability", "DecisionProbability", "ConservativeProbability",
        "EmpiricalHitRate", "ProfileSample", "SampleConfidence", "Reliability",
        "RequiredOddForOperation", "OddGapToOperation", "ModelExpectedValue",
        "ConservativeExpectedValue", "Reason",
    ]
    out = frame[[column for column in columns if column in frame.columns]].copy()
    percentage_columns = (
        "MarketProbability", "RawSportsProbability", "DecisionProbability",
        "ConservativeProbability", "EmpiricalHitRate", "Reliability",
        "ModelExpectedValue", "ConservativeExpectedValue",
    )
    for column in percentage_columns:
        if column in out:
            out[column] = pd.to_numeric(out[column], errors="coerce") * 100.0
    return out.rename(
        columns={
            "Status": "Situação",
            "MarketName": "Mercado",
            "Selection": "Seleção",
            "Odd": "Cotação atual",
            "EffectiveOdd": "Cotação após desconto de 2%",
            "MarketProbability": "Mercado sem margem",
            "RawSportsProbability": "Probabilidade esportiva",
            "DecisionProbability": "Probabilidade do modelo",
            "ConservativeProbability": "Probabilidade conservadora",
            "EmpiricalHitRate": "Acerto dos casos semelhantes",
            "ProfileSample": "Casos semelhantes",
            "SampleConfidence": "Confiança da amostra",
            "Reliability": "Estabilidade",
            "RequiredOddForOperation": "Cotação mínima conservadora",
            "OddGapToOperation": "Diferença da cotação",
            "ModelExpectedValue": "Valor esperado do modelo",
            "ConservativeExpectedValue": "Valor esperado conservador",
            "Reason": "Motivo",
        }
    )


if not readings.empty or not diagnostics.empty:
    st.subheader("3. Resultado completo")
    analyzed_games = int((diagnostics["Situação"] == "ANALISADO").sum()) if not diagnostics.empty else 0
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Partidas analisadas", analyzed_games)
    m2.metric("Entradas V28", len(entries))
    m3.metric("Máximo semanal", int(max_entries))
    m4.metric("Leituras principais", len(readings))
    m5.metric("Mercados avaliados", len(evaluations))

    if entries.empty and not readings.empty:
        st.warning(
            f"Nenhuma cotação atingiu os critérios conservadores neste lote. As {len(readings)} leituras e os preços necessários aparecem abaixo."
        )
    elif not entries.empty:
        week_counts = entries.groupby("WeekID").size().to_dict() if "WeekID" in entries else {}
        st.success(f"{len(entries)} entrada(s) na carteira. Distribuição semanal: {week_counts}.")

    st.markdown("### Carteira validada")
    if entries.empty:
        closest = readings.sort_values("OddGapToOperation", ascending=False).head(int(max_entries)).copy()
        st.warning(f"Nenhuma entrada atingiu os critérios conservadores, respeitando o máximo de {int(max_entries)}. Veja abaixo quanto falta na cotação.")
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
                "Probabilidade do modelo": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Mercado sem margem": st.column_config.NumberColumn(format="%.1f%%"),
                "Probabilidade esportiva": st.column_config.NumberColumn(format="%.1f%%"),
                "Valor esperado conservador": st.column_config.NumberColumn(format="%.1f%%"),
                "Acerto dos casos semelhantes": st.column_config.NumberColumn(format="%.1f%%"),
                "Estabilidade": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Entrada fixa": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )
    if len(games()) < int(max_entries):
        st.info(f"O lote contém {len(games())} partida(s); com uma seleção por jogo, o máximo físico é {len(games())}. O aplicativo não completa artificialmente o limite de {int(max_entries)} entradas.")

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
                    f"{context['HomePoints']} pontos em {context['HomeGames']} jogos | {context['HomePPG']:.2f} ponto(s) por jogo",
                )
                c2.metric(
                    str(game["Visitante"]),
                    f"{context['AwayPosition']}º lugar",
                    f"{context['AwayPoints']} pontos em {context['AwayGames']} jogos | {context['AwayPPG']:.2f} ponto(s) por jogo",
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
                f"{status}: {row['Selection']} | cotação {float(row['Odd']):.2f} | "
                f"probabilidade conservadora {pct(row['ConservativeProbability'])}"
            )
            if status == "OPERAR":
                st.success(headline)
            elif status in ("AGUARDAR PREÇO", "RESERVA", "QUALIFICADA"):
                st.warning(headline)
            else:
                st.info(headline)

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Mercado sem margem", pct(row["MarketProbability"]))
            p2.metric("Probabilidade esportiva", pct(row["RawSportsProbability"]))
            p3.metric("Probabilidade do modelo", pct(row["DecisionProbability"]))
            p4.metric("Probabilidade conservadora", pct(row["ConservativeProbability"]))

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Casos semelhantes", int(row["ProfileSample"]))
            a2.metric("Confiança da amostra", str(row["SampleConfidence"]))
            a3.metric("Estabilidade", pct(row["Reliability"]))
            a4.metric("Acerto dos casos semelhantes", pct(row["EmpiricalHitRate"]))

            o1, o2, o3, o4 = st.columns(4)
            o1.metric("Cotação atual", f"{float(row['Odd']):.2f}")
            o2.metric("Cotação mínima conservadora", f"{float(row['RequiredOddForOperation']):.2f}")
            o3.metric("Diferença da cotação", f"{float(row['OddGapToOperation']):+.2f}")
            o4.metric("Valor esperado conservador", pct(row["ExpectedValue"]))

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
                        "Probabilidade esportiva": st.column_config.NumberColumn(format="%.1f%%"),
                        "Probabilidade do modelo": st.column_config.NumberColumn(format="%.1f%%"),
                        "Acerto dos casos semelhantes": st.column_config.NumberColumn(format="%.1f%%"),
                        "Estabilidade": st.column_config.NumberColumn(format="%.1f%%"),
                        "Valor esperado conservador": st.column_config.NumberColumn(format="%.1f%%"),
                        "Cotação atual": st.column_config.NumberColumn(format="%.2f"),
                        "Cotação após desconto de 2%": st.column_config.NumberColumn(format="%.2f"),
                        "Cotação mínima conservadora": st.column_config.NumberColumn(format="%.2f"),
                        "Diferença da cotação": st.column_config.NumberColumn(format="%+.2f"),
                    },
                )

    st.markdown("### Carteira e auditoria")
    tab_entries, tab_all, tab_errors, tab_ai = st.tabs(
        ["Carteira validada", "Todos os mercados", "Diagnóstico", "Resumo para análise"]
    )
    with tab_entries:
        if entries.empty:
            closest = readings.sort_values("OddGapToOperation", ascending=False).head(5).copy()
            st.info("Nenhuma entrada qualificada neste lote. Abaixo estão as leituras mais próximas da cotação mínima conservadora.")
            st.dataframe(evaluation_table(closest), hide_index=True, use_container_width=True)
        else:
            st.dataframe(
                display_frame(entries),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Probabilidade do modelo": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Probabilidade conservadora": st.column_config.NumberColumn(format="%.1f%%"),
                    "Mercado sem margem": st.column_config.NumberColumn(format="%.1f%%"),
                    "Acerto dos casos semelhantes": st.column_config.NumberColumn(format="%.1f%%"),
                    "Estabilidade": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
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
            "BAIXAR RESUMO PARA ANÁLISE",
            ai_summary.encode("utf-8"),
            "resumo_tex_statistics_para_analise.txt",
            "text/plain",
            use_container_width=True,
        )

    st.subheader("4. Salvar cotações e probabilidades")
    st.caption("O clique grava as cotações e todas as probabilidades avaliadas. Analisar não grava automaticamente.")
    if st.button("SALVAR COTAÇÕES E PROBABILIDADES", type="primary", use_container_width=True):
        if google_configurado(st.secrets):
            try:
                catalog_records = make_catalog_records(evaluations, bankroll)
                analysis_records = make_analysis_records(evaluations, unit_percent / 100.0)
                existing_catalog = identificadores_cotacoes(st.secrets)
                existing_analysis = identificadores_analises(st.secrets)
                catalog_records = [
                    record for record in catalog_records
                    if str(record["ID Coleta"]) not in existing_catalog
                ]
                analysis_records = [
                    record for record in analysis_records
                    if str(record["ID Análise"]) not in existing_analysis
                ]
                saved_odds = salvar_cotacoes(st.secrets, catalog_records)
                saved_analysis = salvar_analises(st.secrets, analysis_records)
                st.success(
                    f"Gravação concluída: {saved_odds} novo(s) registro(s) de cotações e "
                    f"{saved_analysis} novo(s) registro(s) de probabilidades. Duplicidades foram ignoradas."
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
        "BAIXAR RESUMO PARA ANÁLISE",
        (ai_summary or build_ai_summary(games_frame(), readings, evaluations, diagnostics, matches)).encode("utf-8"),
        "resumo_lote_para_analise.txt",
        "text/plain",
        use_container_width=True,
    )

st.subheader("5. Controle financeiro e liquidação")
st.caption(
    "Apostas são registradas somente por clique explícito. A liquidação calcula retorno e lucro ou prejuízo pelo placar informado."
)

if st.session_state.pop("tex_finance_flash", False):
    st.success(st.session_state.pop("tex_finance_flash_message", "Controle financeiro atualizado."))
if st.session_state.get("tex_ledger_sync_warning"):
    st.warning(
        "O histórico local foi carregado, mas a sincronização automática com a planilha falhou: "
        f"{st.session_state.get('tex_ledger_sync_warning')}"
    )

ledger = normalizar_ledger(st.session_state.get("tex_ledger"))

sync_col, register_col = st.columns(2)
if sync_col.button("CARREGAR APOSTAS DA PLANILHA", use_container_width=True):
    if google_configurado(st.secrets):
        try:
            remote_ledger = normalizar_ledger(carregar_apostas(st.secrets))
            remote_by_id = {
                str(row["ID Aposta"]): row
                for _, row in remote_ledger.iterrows()
                if str(row.get("ID Aposta", "")).strip()
            }
            for _, local_row in ledger.iterrows():
                bet_id = str(local_row.get("ID Aposta", "")).strip()
                remote_row = remote_by_id.get(bet_id)
                if (
                    bet_id
                    and remote_row is not None
                    and str(local_row.get("Situação da liquidação", "")) == "LIQUIDADA"
                    and str(remote_row.get("Situação da liquidação", "")) != "LIQUIDADA"
                ):
                    liquidar_aposta(
                        st.secrets,
                        bet_id,
                        int(float(local_row.get("Gols do mandante", 0) or 0)),
                        int(float(local_row.get("Gols do visitante", 0) or 0)),
                        str(local_row.get("Observações", "")),
                    )
            remote_ids = identificadores_apostas(st.secrets)
            local_only = [
                record for record in ledger.to_dict("records")
                if str(record.get("ID Aposta", "")) not in remote_ids
            ]
            uploaded = salvar_apostas(st.secrets, local_only)
            remote_ledger = normalizar_ledger(carregar_apostas(st.secrets))
            ledger = reconciliar_ledgers(remote_ledger, ledger)
            st.session_state.tex_ledger = normalizar_ledger(ledger)
            st.session_state.pop("tex_ledger_sync_warning", None)
            try:
                salvar_ledger_local(LOCAL_LEDGER_PATH, ledger)
            except Exception:
                pass
            invalidate_analysis()
            st.session_state.tex_finance_flash = True
            st.session_state.tex_finance_flash_message = (
                f"Sincronização concluída: {len(ledger)} aposta(s) no controle e "
                f"{uploaded} registro(s) local(is) enviado(s) à planilha."
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Não foi possível carregar as apostas: {exc}")
    else:
        st.info("A Planilha Google não está conectada. O controle local continua disponível.")

if register_col.button(
    "REGISTRAR ENTRADAS DA CARTEIRA",
    type="primary",
    use_container_width=True,
    disabled=entries.empty,
):
    records = criar_registros_apostas(entries, bankroll, INTERFACE_VERSION, EXPECTED_CORE_API, MODEL_VERSION)
    ledger, local_added = mesclar_registros(ledger, records)
    remote_added = 0
    try:
        salvar_ledger_local(LOCAL_LEDGER_PATH, ledger)
    except Exception as exc:
        st.warning(f"O arquivo local não pôde ser atualizado: {exc}")
    if google_configurado(st.secrets):
        try:
            remote_ids = identificadores_apostas(st.secrets)
            remote_records = [record for record in records if str(record["ID Aposta"]) not in remote_ids]
            remote_added = salvar_apostas(st.secrets, remote_records)
        except Exception as exc:
            st.error(f"As apostas foram mantidas localmente, mas a planilha não pôde ser atualizada: {exc}")
    st.session_state.tex_ledger = ledger
    invalidate_analysis()
    st.session_state.tex_finance_flash = True
    st.session_state.tex_finance_flash_message = (
        f"Registro concluído: {local_added} nova(s) aposta(s) no controle local e "
        f"{remote_added} nova(s) na planilha. Identificadores repetidos foram ignorados."
    )
    st.rerun()

ledger = normalizar_ledger(st.session_state.get("tex_ledger"))
summary = resumo_financeiro(ledger, bankroll)
f1, f2, f3, f4, f5 = st.columns(5)
f1.metric("Apostas registradas", int(summary["registradas"]))
f2.metric("Pendentes", int(summary["pendentes"]))
f3.metric("Liquidadas", int(summary["liquidadas"]))
f4.metric("Lucro ou prejuízo", money(float(summary["lucro"])))
f5.metric("Banca informada", money(float(summary["banca_informada"])))

f6, f7, f8 = st.columns(3)
f6.metric("Taxa de acerto", pct(float(summary["taxa_acerto"])))
f7.metric("Retorno sobre entradas", pct(float(summary["retorno_sobre_entradas"])))
f8.metric("Maior recuo financeiro", money(float(summary["maior_recuo"])))

if ledger.empty:
    st.info("Ainda não há apostas registradas no controle financeiro.")
else:
    visible_ledger_columns = [
        "ID Aposta", "Data do jogo", "Hora do jogo", "Jogo", "Mercado", "Seleção",
        "Casa de apostas", "Cotação", "Entrada (R$)", "Situação da liquidação",
        "Resultado da aposta", "Lucro ou prejuízo (R$)", "Liquidado em",
    ]
    st.dataframe(
        ledger[[column for column in visible_ledger_columns if column in ledger.columns]],
        hide_index=True,
        use_container_width=True,
    )

    pending = ledger[ledger["Situação da liquidação"].astype(str).eq("PENDENTE")].copy()
    if not pending.empty:
        labels = {
            str(row["ID Aposta"]): (
                f"{row['Data do jogo']} — {row['Jogo']} — {row['Seleção']} — cotação {row['Cotação']}"
            )
            for _, row in pending.iterrows()
        }
        with st.form("liquidacao_aposta"):
            selected_id = st.selectbox(
                "Aposta pendente",
                list(labels),
                format_func=lambda value: labels.get(value, value),
            )
            score_columns = st.columns(2)
            home_goals = score_columns[0].number_input(
                "Gols do mandante", min_value=0, max_value=30, value=0, step=1
            )
            away_goals = score_columns[1].number_input(
                "Gols do visitante", min_value=0, max_value=30, value=0, step=1
            )
            settlement_notes = st.text_input("Observações da liquidação", value="")
            settle = st.form_submit_button("LIQUIDAR APOSTA", type="primary", use_container_width=True)
        if settle:
            try:
                source_record = pending[
                    pending["ID Aposta"].astype(str).eq(selected_id)
                ].iloc[0].to_dict()
                updated = liquidar_registro(
                    source_record,
                    int(home_goals),
                    int(away_goals),
                    settlement_notes,
                )
                if google_configurado(st.secrets):
                    try:
                        updated = liquidar_aposta(
                            st.secrets,
                            selected_id,
                            int(home_goals),
                            int(away_goals),
                            settlement_notes,
                        )
                        st.session_state.pop("tex_ledger_sync_warning", None)
                    except Exception as remote_exc:
                        st.session_state.tex_ledger_sync_warning = (
                            "A liquidação foi preservada localmente, mas não pôde ser enviada "
                            f"à planilha: {remote_exc}"
                        )
                ledger = atualizar_registro(ledger, updated)
                st.session_state.tex_ledger = ledger
                try:
                    salvar_ledger_local(LOCAL_LEDGER_PATH, ledger)
                except Exception:
                    pass
                st.success(
                    f"Aposta liquidada como {updated['Resultado da aposta']}. "
                    f"Lucro ou prejuízo: {money(float(updated['Lucro ou prejuízo (R$)']))}."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Não foi possível liquidar a aposta: {exc}")
    else:
        st.success("Não há apostas pendentes de liquidação.")

    st.download_button(
        "BAIXAR CONTROLE FINANCEIRO CSV",
        ledger.to_csv(index=False).encode("utf-8-sig"),
        "controle_financeiro_tex_statistics.csv",
        "text/csv",
        use_container_width=True,
    )
