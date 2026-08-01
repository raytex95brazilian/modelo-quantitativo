from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import html
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
_filtro2018 = _load_required_module("tex_filtro_2018")
_operacao_filtrada = _load_required_module("tex_operacao_filtrada")
_importador = _load_required_module("tex_importador_programacao")

EXPECTED_CORE_API = "28.1.2"
EXPECTED_STORAGE_API = "28.3.6"
EXPECTED_FINANCE_API = "28.1.5.12"
EXPECTED_FILTER_API = "28.3.3"
EXPECTED_OPERATION_API = "28.2.0"
EXPECTED_IMPORTER_API = "28.3.8"
INTERFACE_VERSION = "V28.3.8"
APP_NAME = "Tex Statistics V28.3.8 — Reconhecimento atualizado de ligas"
CORE_NAME = getattr(_v28, "APP_NAME", "Tex Statistics V28.1.2 — Estado Isolado")
CORE_DISPLAY_NAME = "V28.1.2 — Estado Isolado"
MODEL_VERSION = getattr(_v28, "MODEL_VERSION", "V28.0")
ENGINE_VERSION = getattr(_v28, "ENGINE_VERSION", "V28.1.2-estado-isolado")

_REQUIRED_V25 = ("LEAGUES", "normalize_zip")
_REQUIRED_STORAGE = (
    "COLUNAS_ANALISES", "COLUNAS_COTACOES", "carregar_apostas",
    "criar_registros_cotacoes_digitadas",
    "carregar_lote_pendente", "registrar_evento_lote", "registrar_eventos_lote", "diagnostico_google",
    "google_configurado", "identificadores_analises", "identificadores_apostas",
    "identificadores_cotacoes", "liquidar_aposta", "salvar_analises",
    "salvar_apostas", "salvar_cotacoes", "salvar_lote_pendente",
    "url_planilha_configurada",
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
_REQUIRED_FILTER_2018 = ("evaluate_lot_2018", "build_lot_form_contexts")
_REQUIRED_OPERATION_FILTERED = ("attach_filter_results", "build_operational_outputs")
_REQUIRED_IMPORTER = (
    "parse_pasted_schedule", "resolve_imported_matches",
    "resolve_team_in_league",
)

_IMPORT_PROBLEMS = list(_MODULE_IMPORT_ERRORS)
for module_name, module, required in (
    ("tex_v25_core", _v25, _REQUIRED_V25),
    ("tex_v25_storage", _storage, _REQUIRED_STORAGE),
    ("tex_v28_finance", _finance, _REQUIRED_FINANCE),
    ("tex_v28_core_2812", _v28, _REQUIRED_V28),
    ("tex_operacional_core", _operacional, _REQUIRED_OPERACIONAL),
    ("tex_filtro_2018", _filtro2018, _REQUIRED_FILTER_2018),
    ("tex_operacao_filtrada", _operacao_filtrada, _REQUIRED_OPERATION_FILTERED),
    ("tex_importador_programacao", _importador, _REQUIRED_IMPORTER),
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
if _filtro2018 is not None and getattr(_filtro2018, "FILTER_API_VERSION", None) != EXPECTED_FILTER_API:
    _IMPORT_PROBLEMS.append(
        f"FILTER_API_VERSION esperado {EXPECTED_FILTER_API}; encontrado "
        f"{getattr(_filtro2018, 'FILTER_API_VERSION', 'ausente')}"
    )
if _operacao_filtrada is not None and getattr(_operacao_filtrada, "OPERATION_API_VERSION", None) != EXPECTED_OPERATION_API:
    _IMPORT_PROBLEMS.append(
        f"OPERATION_API_VERSION esperado {EXPECTED_OPERATION_API}; encontrado "
        f"{getattr(_operacao_filtrada, 'OPERATION_API_VERSION', 'ausente')}"
    )
if _importador is not None and getattr(_importador, "IMPORTER_API_VERSION", None) != EXPECTED_IMPORTER_API:
    _IMPORT_PROBLEMS.append(
        f"IMPORTER_API_VERSION esperado {EXPECTED_IMPORTER_API}; encontrado "
        f"{getattr(_importador, 'IMPORTER_API_VERSION', 'ausente')}"
    )

LEAGUES = getattr(_v25, "LEAGUES", {})
normalize_zip = getattr(_v25, "normalize_zip", None)
COLUNAS_ANALISES = getattr(_storage, "COLUNAS_ANALISES", [])
COLUNAS_COTACOES = getattr(_storage, "COLUNAS_COTACOES", [])
carregar_apostas = getattr(_storage, "carregar_apostas", None)
criar_registros_cotacoes_digitadas = getattr(_storage, "criar_registros_cotacoes_digitadas", None)
carregar_lote_pendente = getattr(_storage, "carregar_lote_pendente", None)
google_configurado = getattr(_storage, "google_configurado", None)
identificadores_analises = getattr(_storage, "identificadores_analises", None)
identificadores_apostas = getattr(_storage, "identificadores_apostas", None)
identificadores_cotacoes = getattr(_storage, "identificadores_cotacoes", None)
liquidar_aposta = getattr(_storage, "liquidar_aposta", None)
salvar_analises = getattr(_storage, "salvar_analises", None)
salvar_apostas = getattr(_storage, "salvar_apostas", None)
salvar_cotacoes = getattr(_storage, "salvar_cotacoes", None)
salvar_lote_pendente = getattr(_storage, "salvar_lote_pendente", None)
registrar_evento_lote = getattr(_storage, "registrar_evento_lote", None)
registrar_eventos_lote = getattr(_storage, "registrar_eventos_lote", None)
diagnostico_google = getattr(_storage, "diagnostico_google", None)
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
_core_build_ai_summary = getattr(_v28, "build_ai_summary", None)
display_frame = getattr(_v28, "display_frame", None)
load_v28_model = getattr(_v28, "load_v28_model", None)
lot_fingerprint = getattr(_v28, "lot_fingerprint", None)
validate_market_odds = getattr(_v28, "validate_market_odds", None)
INPUT_COLUMNS = getattr(_operacional, "INPUT_COLUMNS", [])
enrich_with_standings = getattr(_operacional, "enrich_with_standings", None)
latest_team_catalog = getattr(_operacional, "latest_team_catalog", None)
parse_odd = getattr(_operacional, "parse_odd", None)
standings_context = getattr(_operacional, "standings_context", None)
evaluate_lot_2018 = getattr(_filtro2018, "evaluate_lot_2018", None)
build_lot_form_contexts = getattr(_filtro2018, "build_lot_form_contexts", None)
attach_filter_results = getattr(_operacao_filtrada, "attach_filter_results", None)
build_operational_outputs = getattr(_operacao_filtrada, "build_operational_outputs", None)
parse_pasted_schedule = getattr(_importador, "parse_pasted_schedule", None)
resolve_imported_matches = getattr(_importador, "resolve_imported_matches", None)
resolve_team_in_league = getattr(_importador, "resolve_team_in_league", None)


def build_ai_summary(
    games: pd.DataFrame,
    readings: pd.DataFrame,
    evaluations: pd.DataFrame,
    diagnostics: pd.DataFrame,
    matches,
) -> str:
    """Gera o resumo com identificação inequívoca da interface e do motor."""
    if not callable(_core_build_ai_summary):
        raise RuntimeError("O núcleo V28.1.2 não disponibilizou build_ai_summary.")
    original = _core_build_ai_summary(games, readings, evaluations, diagnostics, matches)
    original_lines = str(original).splitlines()
    body = original_lines[1:] if original_lines else []
    approved = 0
    rejected = 0
    if not evaluations.empty and "Filter2018Approved" in evaluations:
        by_game = evaluations[["InputID", "Filter2018Approved"]].drop_duplicates("InputID")
        approved = int(by_game["Filter2018Approved"].fillna(False).astype(bool).sum())
        rejected = int(len(by_game) - approved)
    return "\n".join([
        "ANÁLISE PARA IA — Tex Statistics",
        f"Interface: {APP_NAME}",
        f"Motor preditivo: {CORE_DISPLAY_NAME}",
        f"Filtro eliminatório de 2018: {approved} aprovado(s) e {rejected} reprovado(s).",
        "Jogos reprovados permanecem calculados e salvos, mas são proibidos em apostas simples e múltiplas.",
        *body,
    ])


ROOT = Path(__file__).resolve().parent
DATA_ZIP = ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip"
MODEL_DIR = ROOT / "model"
LOCAL_LEDGER_PATH = ROOT / "data" / "tex_v28_apostas.csv"
LOCAL_PENDING_LOT_PATH = ROOT / "data" / "tex_v28_lote_pendente.json"
CONSERVATIVE_BACKTEST_PATH = ROOT / "backtest" / "V28_1_5_7_META_5_RESUMO.json"
FUSO = ZoneInfo("America/Fortaleza")

st.set_page_config(page_title=APP_NAME, page_icon="⚽", layout="wide", initial_sidebar_state="auto")

if _IMPORT_PROBLEMS:
    st.error("Arquivos da V28 desencontrados no deploy.")
    st.code("\n".join(_IMPORT_PROBLEMS), language="text")
    st.info(
        "O deploy misturou arquivos de versões diferentes. Substitua TODO o conteúdo da raiz "
        "pelo mesmo pacote V28.3.8, confirme os módulos do filtro de 2018 e de armazenamento no GitHub, "
        "faça commit e execute Reboot app no Streamlit Cloud."
    )
    st.stop()


# Streamlit 1.37+ oferece st.fragment, que limita a reexecução ao bloco interativo.
# O fallback experimental mantém compatibilidade com instalações 1.35/1.36.
_FRAGMENT_DECORATOR = getattr(st, "fragment", getattr(st, "experimental_fragment", None))
if _FRAGMENT_DECORATOR is None:
    def _fragment(function):
        return function
else:
    _fragment = _FRAGMENT_DECORATOR


def now_br() -> datetime:
    return datetime.now(FUSO)


def apply_style() -> None:
    st.markdown(
        """
        <style>
        :root{--tex-navy:#0f172a;--tex-cyan:#0891b2;--tex-teal:#0f766e;--tex-soft:#f0fdfa;--tex-border:rgba(15,118,110,.22)}
        .block-container{max-width:1480px;padding-top:1rem;padding-bottom:5rem}
        .tex-head{padding:1.25rem 1.35rem;border-radius:22px;background:linear-gradient(135deg,#0f172a 0%,#164e63 55%,#0f766e 100%);color:#fff;margin-bottom:1rem;box-shadow:0 18px 45px rgba(15,23,42,.18)}
        .tex-head h1{margin:0;font-size:2rem;letter-spacing:-.03em}.tex-head p{margin:.55rem 0 0;color:#dbeafe;line-height:1.55}
        .rule-box,.tex-info-card{padding:1rem 1.05rem;border-radius:16px;border:1px solid var(--tex-border);background:linear-gradient(135deg,rgba(240,253,250,.92),rgba(236,254,255,.92));margin:.55rem 0 1rem}
        .filter-approved{padding:1rem;border-radius:16px;border:1px solid rgba(22,163,74,.32);background:rgba(220,252,231,.72);margin:.5rem 0}
        .filter-rejected{padding:1rem;border-radius:16px;border:1px solid rgba(220,38,38,.28);background:rgba(254,226,226,.72);margin:.5rem 0}
        .multiple-card{padding:1.05rem 1.15rem;border-radius:18px;background:linear-gradient(135deg,#172554,#164e63);color:#fff;box-shadow:0 14px 34px rgba(15,23,42,.18);margin:.75rem 0 1.1rem}
        .multiple-card strong{color:#a5f3fc}
        [data-testid="stMetric"],[data-testid="stDataFrame"]{border:1px solid rgba(120,120,120,.20);border-radius:15px;padding:.5rem;background:rgba(255,255,255,.02)}
        [data-testid="stForm"],[data-testid="stVerticalBlockBorderWrapper"]{border-radius:18px!important}
        .stButton>button,.stDownloadButton>button,.stLinkButton>a{min-height:46px;border-radius:14px!important;font-weight:750!important;letter-spacing:.01em;transition:transform .16s ease,box-shadow .16s ease!important}
        .stButton>button:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover{transform:translateY(-1px);box-shadow:0 8px 20px rgba(8,145,178,.18)}
        button[kind="primary"]{background:linear-gradient(135deg,#0891b2,#0f766e)!important;border:0!important;color:white!important}
        [data-baseweb="input"]>div,[data-baseweb="select"]>div{border-radius:12px!important}
        [data-baseweb="tab-list"]{gap:.45rem;background:rgba(8,145,178,.06);padding:.35rem;border-radius:16px}
        [data-baseweb="tab"]{min-height:46px;border-radius:12px;padding:.55rem 1rem;font-weight:750}
        [aria-selected="true"][data-baseweb="tab"]{background:linear-gradient(135deg,rgba(8,145,178,.16),rgba(15,118,110,.14))}
        [data-testid="stTextArea"] textarea{border-radius:14px!important;line-height:1.45}
        .game-card{padding:.95rem 1rem;border:1px solid rgba(120,120,120,.20);border-radius:15px;margin:.4rem 0}
        .team-context{padding:.9rem 1rem;border:1px solid rgba(8,145,178,.20);border-radius:16px;background:linear-gradient(135deg,rgba(236,254,255,.78),rgba(240,253,250,.72));margin:.45rem 0}
        .team-context-title{font-weight:800;font-size:1.02rem;margin-bottom:.2rem}.team-context-meta{font-size:.91rem;opacity:.84;margin-bottom:.55rem}
        .form-strip{display:flex;gap:.38rem;flex-wrap:wrap;align-items:center;margin:.25rem 0 .55rem}.form-label{font-size:.82rem;font-weight:750;opacity:.75;margin-right:.1rem}
        .form-badge{display:inline-flex;align-items:center;justify-content:center;min-width:29px;height:29px;border-radius:9px;color:#fff;font-weight:850;font-size:.82rem;box-shadow:0 3px 8px rgba(15,23,42,.12)}
        .form-v{background:#15803d}.form-e{background:#a16207}.form-d{background:#b91c1c}.form-na{background:#64748b}
        @media(max-width:768px){
          .block-container{padding:.65rem .75rem 4.5rem}.tex-head{padding:1rem;border-radius:17px}.tex-head h1{font-size:1.45rem}.tex-head p{font-size:.9rem}
          [data-testid="stMetric"]{padding:.35rem}.stButton>button,.stDownloadButton>button,.stLinkButton>a{min-height:50px;font-size:.96rem}
          .rule-box,.tex-info-card,.multiple-card{border-radius:14px;padding:.85rem}
          [data-testid="stDataFrame"]{overflow-x:auto}
          [data-baseweb="tab-list"]{display:grid;grid-template-columns:1fr 1fr;width:100%}
          [data-baseweb="tab"]{font-size:.86rem;padding:.45rem .35rem;text-align:center}
          [data-testid="stTextArea"] textarea{min-height:260px!important;font-size:.92rem}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="tex-head"><h1>Tex Statistics</h1>'
        f'<p><b>Interface:</b> {APP_NAME}<br>'
        f'<b>Motor preditivo:</b> {CORE_DISPLAY_NAME}<br>'
        '<b>Fluxo:</b> cadastro e armazenamento integral → filtro eliminatório de 2018 → análise estatística e financeira dos aprovados → simples e sugestão de múltipla.</p></div>',
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
    "tex_filter_results", "tex_form_contexts", "tex_multiple_summary",
    "tex_ai_summary", "tex_analysis_fingerprint",
)


def _snapshot_time(snapshot: dict) -> datetime:
    raw = str(snapshot.get("Salvo em", "") or snapshot.get("saved_at", "") or "").strip()
    if not raw:
        return datetime.min.replace(tzinfo=FUSO)
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=FUSO)
    except Exception:
        return datetime.min.replace(tzinfo=FUSO)


def _load_local_pending_lot() -> dict:
    if not LOCAL_PENDING_LOT_PATH.is_file():
        return {"Salvo em": "", "Jogos": []}
    try:
        payload = json.loads(LOCAL_PENDING_LOT_PATH.read_text(encoding="utf-8"))
        jogos = payload.get("Jogos", []) if isinstance(payload, dict) else []
        return {
            "Salvo em": str(payload.get("Salvo em", "") if isinstance(payload, dict) else ""),
            "Jogos": [dict(item) for item in jogos if isinstance(item, dict)],
        }
    except Exception as exc:
        st.session_state.tex_autosave_warning = f"Backup local do lote não pôde ser lido: {exc}"
        return {"Salvo em": "", "Jogos": []}


def _save_local_pending_lot(jogos: list[dict]) -> dict:
    LOCAL_PENDING_LOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "Salvo em": now_br().replace(microsecond=0).isoformat(),
        "Versão da interface": INTERFACE_VERSION,
        "Jogos": [dict(item) for item in jogos],
    }
    temporary = LOCAL_PENDING_LOT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(LOCAL_PENDING_LOT_PATH)
    return snapshot


def _restore_pending_lot() -> list[dict]:
    """Restaura da planilha como fonte principal; local é apenas contingência."""
    local = _load_local_pending_lot()
    if google_configurado(st.secrets):
        try:
            remote = carregar_lote_pendente(st.secrets)
            remote_authoritative = bool(
                remote.get("Salvo em")
                or int(remote.get("Eventos encontrados", 0) or 0) > 0
                or remote.get("Jogos")
            )
            if remote_authoritative:
                restored = [dict(item) for item in remote.get("Jogos", []) if isinstance(item, dict)]
                _save_local_pending_lot(restored)
                st.session_state.tex_autosave_notice = (
                    f"Lote restaurado da planilha: {len(restored)} partida(s). "
                    "Fonte durável: aba entrada_jogos."
                )
                return restored
        except Exception as exc:
            st.session_state.tex_autosave_warning = (
                "Não foi possível restaurar o lote da planilha. O backup local foi usado apenas como contingência: "
                f"{exc}"
            )

    restored = [dict(item) for item in local.get("Jogos", []) if isinstance(item, dict)]
    if restored:
        st.session_state.tex_autosave_notice = (
            f"Lote restaurado do backup local: {len(restored)} partida(s). "
            "Sincronize com a planilha antes de continuar."
        )
    return restored


def games() -> list[dict]:
    if "tex_games" not in st.session_state:
        st.session_state.tex_games = _restore_pending_lot()
    return st.session_state.tex_games


def _persist_snapshot_best_effort(reason: str) -> None:
    """Mantém cópias redundantes; o log entrada_jogos é a fonte durável principal."""
    current = [dict(item) for item in games()]
    local = _save_local_pending_lot(current)
    if google_configurado(st.secrets):
        try:
            remote = salvar_lote_pendente(
                st.secrets, current, interface_version=INTERFACE_VERSION
            )
            st.session_state.tex_autosave_status = (
                f"Persistência confirmada: {len(current)} partida(s) na aba entrada_jogos; "
                f"snapshot atualizado — {reason} — {remote.get('Salvo em', local.get('Salvo em', ''))}."
            )
            st.session_state.pop("tex_autosave_warning", None)
        except Exception as exc:
            # O evento append-only já foi confirmado; falha do snapshot não perde a partida.
            st.session_state.tex_autosave_status = (
                f"Persistência confirmada na aba entrada_jogos: {len(current)} partida(s) — {reason}."
            )
            st.session_state.tex_autosave_warning = (
                "A partida foi salva no histórico durável, mas a cópia-resumo lote_pendente não foi atualizada: "
                f"{exc}"
            )
    else:
        st.session_state.tex_autosave_status = (
            f"Backup local atualizado: {len(current)} partida(s) — {reason}."
        )
        st.session_state.tex_autosave_warning = (
            "Google Sheets não está configurado. Sem a aba entrada_jogos não existe garantia de restauração "
            "após reinício do servidor."
        )


def _registrar_evento_obrigatorio(tipo_evento: str, jogo: dict | None = None) -> dict:
    """Grava, relê e devolve o endereço exato da linha confirmada."""
    if not google_configurado(st.secrets):
        detalhe = diagnostico_google(st.secrets) if callable(diagnostico_google) else {}
        raise RuntimeError(
            "A partida NÃO foi aceita porque não existe uma planilha de destino explicitamente configurada. "
            + str(detalhe.get("erro") or "Informe spreadsheet_id ou spreadsheet_url nos Secrets.")
        )
    try:
        confirmacao = registrar_evento_lote(
            st.secrets,
            tipo_evento=tipo_evento,
            jogo=jogo,
            interface_version=INTERFACE_VERSION,
        )
        if str(confirmacao.get("Verificação", "")) != "GRAVADO E RELIDO":
            raise RuntimeError("A leitura pós-gravação não foi confirmada.")
        return dict(confirmacao)
    except Exception as exc:
        raise RuntimeError(
            "A partida NÃO foi aceita porque a planilha não confirmou e não devolveu as cotações gravadas. "
            "Os campos permanecem preenchidos; não digite a próxima partida. "
            f"Detalhe: {exc}"
        ) from exc


def _normalizar_lote_para_comparacao(items: list[dict]) -> str:
    return json.dumps([dict(item) for item in items], ensure_ascii=False, sort_keys=True, default=str)


def _confirmar_lote_remoto_antes_da_analise() -> None:
    if not google_configurado(st.secrets):
        return
    remote = carregar_lote_pendente(st.secrets)
    jogos_remotos = [dict(item) for item in remote.get("Jogos", []) if isinstance(item, dict)]
    if _normalizar_lote_para_comparacao(jogos_remotos) != _normalizar_lote_para_comparacao(games()):
        raise RuntimeError(
            "O lote exibido não coincide com o lote durável da planilha. "
            "A análise foi bloqueada para evitar perda ou mistura de partidas. Recarregue a página."
        )


def invalidate_analysis() -> None:
    for key in RESULT_STATE_KEYS:
        st.session_state.pop(key, None)


def _stable_game_id(game_date: str, league_code: str, home: str, away: str) -> str:
    payload = "|".join([str(game_date), str(league_code), str(home), str(away)]).strip().lower()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def upsert_game(game: dict, bankroll_value: float) -> str:
    key = (game["Data"], game["Código da liga"], game["Mandante"], game["Visitante"])
    existing_index: int | None = None
    candidate = dict(game)
    for index, current in enumerate(games()):
        current_key = (current["Data"], current["Código da liga"], current["Mandante"], current["Visitante"])
        if key == current_key:
            existing_index = index
            candidate["ID"] = current["ID"]
            break

    # 1) Registra o jogo bruto no log durável.
    confirmacao = _registrar_evento_obrigatorio("UPSERT", candidate)

    # 2) Grava imediatamente cada cotação na aba catalogo_odds, antes de qualquer análise.
    #    Ao analisar, as mesmas linhas são atualizadas por ID com probabilidades e contexto.
    try:
        registros_digitados = criar_registros_cotacoes_digitadas(
            candidate,
            bankroll=float(bankroll_value),
            interface_version=INTERFACE_VERSION,
            core_api_version=EXPECTED_CORE_API,
            model_version=MODEL_VERSION,
            core_name=CORE_NAME,
            app_name=APP_NAME,
        )
        cotacoes_confirmadas = salvar_cotacoes(st.secrets, registros_digitados)
        if cotacoes_confirmadas != len(registros_digitados):
            raise RuntimeError(
                f"esperadas {len(registros_digitados)} cotação(ões), confirmadas {cotacoes_confirmadas}."
            )
    except Exception as exc:
        raise RuntimeError(
            "O jogo foi preservado na aba entrada_jogos, mas as cotações ainda não foram "
            "confirmadas em catalogo_odds. Os campos permanecem preenchidos; clique novamente "
            f"após corrigir a conexão. Detalhe: {exc}"
        ) from exc

    # Só depois das duas confirmações altera a sessão e limpa o formulário.
    if existing_index is None:
        games().append(candidate)
        action = "adicionada"
    else:
        games()[existing_index] = candidate
        action = "atualizada"
    invalidate_analysis()
    _persist_snapshot_best_effort(f"partida {action}")
    confirmacao["Cotações no catálogo"] = int(cotacoes_confirmadas)
    st.session_state.tex_last_sheet_confirmation = confirmacao
    return action



def _merge_imported_game(existing: dict | None, incoming: dict) -> dict:
    """Preserva cotações complementares já digitadas quando a importação traz só 1X2."""
    merged = dict(existing or {})
    merged.update({key: value for key, value in dict(incoming).items() if value is not None})
    for column in INPUT_COLUMNS:
        merged.setdefault(column, None if str(column).startswith("Odd ") else "")
    return merged


def upsert_games_batch(
    imported_games: list[dict],
    bankroll_value: float,
    *,
    replace_current_lot: bool = False,
) -> dict:
    """Persiste uma importação inteira e controla se ela substitui o lote ativo."""
    if not imported_games:
        return {"adicionadas": 0, "atualizadas": 0, "cotacoes": 0}
    if not google_configurado(st.secrets):
        detalhe = diagnostico_google(st.secrets) if callable(diagnostico_google) else {}
        raise RuntimeError(
            "O lote NÃO foi aceito porque não existe uma planilha de destino configurada. "
            + str(detalhe.get("erro") or "Informe spreadsheet_id ou spreadsheet_url nos Secrets.")
        )

    previous = [dict(item) for item in games()]
    current = [] if replace_current_lot else [dict(item) for item in previous]
    previous_by_key = {
        (item.get("Data"), item.get("Código da liga"), item.get("Mandante"), item.get("Visitante")): item
        for item in previous
    }
    index_by_key = {
        (item.get("Data"), item.get("Código da liga"), item.get("Mandante"), item.get("Visitante")): index
        for index, item in enumerate(current)
    }
    prepared: list[dict] = []
    added = 0
    updated = 0
    for raw in imported_games:
        incoming = dict(raw)
        key = (
            incoming.get("Data"), incoming.get("Código da liga"),
            incoming.get("Mandante"), incoming.get("Visitante"),
        )
        existing_index = index_by_key.get(key)
        existing = current[existing_index] if existing_index is not None else previous_by_key.get(key)
        candidate = _merge_imported_game(existing, incoming)
        if existing is not None:
            candidate["ID"] = existing.get("ID") or incoming.get("ID")
            updated += 1
        else:
            added += 1
        prepared.append(candidate)

    event_confirmation = registrar_eventos_lote(
        st.secrets,
        prepared,
        interface_version=INTERFACE_VERSION,
        substituir_lote=bool(replace_current_lot),
    )
    if str(event_confirmation.get("Verificação", "")) != "GRAVADO E RELIDO EM LOTE":
        raise RuntimeError("A leitura pós-gravação do lote não foi confirmada.")

    catalog_records: list[dict] = []
    for candidate in prepared:
        catalog_records.extend(
            criar_registros_cotacoes_digitadas(
                candidate,
                bankroll=float(bankroll_value),
                interface_version=INTERFACE_VERSION,
                core_api_version=EXPECTED_CORE_API,
                model_version=MODEL_VERSION,
                core_name=CORE_NAME,
                app_name=APP_NAME,
            )
        )
    confirmed_odds = salvar_cotacoes(st.secrets, catalog_records)
    if confirmed_odds != len(catalog_records):
        raise RuntimeError(
            f"Foram esperadas {len(catalog_records)} cotações e confirmadas {confirmed_odds}."
        )

    # Atualiza a sessão apenas depois de as duas abas terem sido gravadas e relidas.
    # Em novo lote, a lista começa vazia; o histórico anterior permanece nas planilhas.
    result = current
    index_by_key = {
        (item.get("Data"), item.get("Código da liga"), item.get("Mandante"), item.get("Visitante")): index
        for index, item in enumerate(result)
    }
    for candidate in prepared:
        key = (
            candidate.get("Data"), candidate.get("Código da liga"),
            candidate.get("Mandante"), candidate.get("Visitante"),
        )
        existing_index = index_by_key.get(key)
        if existing_index is None:
            index_by_key[key] = len(result)
            result.append(candidate)
        else:
            result[existing_index] = candidate
    st.session_state.tex_games = result
    invalidate_analysis()
    mode_label = "novo lote" if replace_current_lot else "acréscimo ao lote atual"
    _persist_snapshot_best_effort(
        f"{mode_label}: {added} nova(s), {updated} atualizada(s)"
    )
    st.session_state.tex_last_batch_confirmation = {
        **event_confirmation,
        "Partidas adicionadas": added,
        "Partidas atualizadas": updated,
        "Cotações no catálogo": confirmed_odds,
    }
    return {
        "adicionadas": added,
        "atualizadas": updated,
        "cotacoes": confirmed_odds,
        "substituiu_lote": bool(replace_current_lot),
        "partidas_ativas": len(result),
    }

def remove_game(index: int) -> dict:
    target = dict(games()[index])
    _registrar_evento_obrigatorio("DELETE", target)
    games().pop(index)
    invalidate_analysis()
    _persist_snapshot_best_effort("partida removida")
    return target


def clear_games() -> None:
    _registrar_evento_obrigatorio("CLEAR", None)
    st.session_state.tex_games = []
    invalidate_analysis()
    _persist_snapshot_best_effort("lote apagado pelo usuário")


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
                "Filtro 2018 — status": getattr(row, "Filter2018Status", ""),
                "Filtro 2018 — elegível operacional": "Sim" if bool(getattr(row, "Filter2018Approved", False)) else "Não",
                "Regra 1 — resultado": "Aprovada" if bool(getattr(row, "Filter2018Rule1Pass", False)) else "Reprovada",
                "Regra 1 — fundamento": getattr(row, "Filter2018Rule1Basis", ""),
                "Regra 1 — detalhe": getattr(row, "Filter2018Rule1Detail", ""),
                "Regra 2 — resultado": "Aprovada" if bool(getattr(row, "Filter2018Rule2Pass", False)) else "Reprovada",
                "Regra 2 — detalhe": getattr(row, "Filter2018Rule2Detail", ""),
                "Regra 3 — resultado": "Aprovada" if bool(getattr(row, "Filter2018Rule3Pass", False)) else "Reprovada",
                "Regra 3 — gols do mandante nas últimas 5": getattr(row, "Filter2018Rule3Count", ""),
                "Regra 3 — detalhe": getattr(row, "Filter2018Rule3Detail", ""),
                "Regra 4 — resultado": "Aprovada" if bool(getattr(row, "Filter2018Rule4Pass", False)) else "Reprovada",
                "Regra 4 — gols do visitante nas últimas 5": getattr(row, "Filter2018Rule4Count", ""),
                "Regra 4 — detalhe": getattr(row, "Filter2018Rule4Detail", ""),
                "Último confronto direto — data": getattr(row, "Filter2018LastH2HDate", ""),
                "Último confronto direto — placar": getattr(row, "Filter2018LastH2HScore", ""),
                "Último confronto direto — ambas marcaram": getattr(row, "Filter2018LastH2HBothScored", ""),
                "Resumo do filtro 2018": getattr(row, "Filter2018Summary", ""),
                "Decisão operacional": getattr(row, "OperationalDecision", getattr(row, "Status", "")),
                "Mercado escolhido para simples": "Sim" if str(getattr(row, "Status", "")) == "OPERAR" else "Não",
                "Incluído na sugestão de múltipla": "Sim" if bool(getattr(row, "IncludedInMultiple", False)) else "Não",
                "Fator total da múltipla": getattr(row, "MultipleFactorTotal", ""),
                "Versão do filtro 2018": EXPECTED_FILTER_API,
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
            "filtro_2018_obrigatorio": True,
            "piso_ev_financeiro": 0.0,
            "politica_operacional": "somente jogos aprovados no filtro de 2018; sem meta mínima; uma seleção simples por partida",
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
                "Entrada %": unit_fraction * float(getattr(row, "StakeMultiplier", 1.0)) * 100.0 if row.Status == "OPERAR" else 0.0,
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
                    f"Confiança estatística da amostra: {row.SampleConfidence}. Estabilidade: {float(row.Reliability):.1%}. "
                    f"Cotação informada: {float(row.Odd):.2f}; cotação após desconto: {float(row.EffectiveOdd):.2f}. "
                    f"Desacordo: {getattr(row, 'DisagreementLevel', 'NORMAL')} "
                    f"({float(getattr(row, 'MaximumComponentDisagreement', 0.0)):.1%}). "
                    f"Faixa da carteira: {getattr(row, 'PortfolioTier', '')}; "
                    f"multiplicador da unidade: {float(getattr(row, 'StakeMultiplier', 0.0)):.2f}."
                ),
                "Versão da interface": INTERFACE_VERSION,
                "Versão da API do núcleo": EXPECTED_CORE_API,
                "Probabilidade conservadora %": float(row.ConservativeProbability) * 100.0,
                "Valor esperado do modelo %": float(row.ModelExpectedValue) * 100.0,
                "Valor esperado conservador %": float(row.ConservativeExpectedValue) * 100.0,
                "Limite conservador da faixa histórica %": float(row.SimilarCasesLowerProbability) * 100.0,
                "Código do mercado": row.Market,
                "Código da seleção": row.Side,
                "Filtro 2018 — status": getattr(row, "Filter2018Status", ""),
                "Filtro 2018 — elegível operacional": "Sim" if bool(getattr(row, "Filter2018Approved", False)) else "Não",
                "Regra 1 — resultado": "Aprovada" if bool(getattr(row, "Filter2018Rule1Pass", False)) else "Reprovada",
                "Regra 1 — fundamento": getattr(row, "Filter2018Rule1Basis", ""),
                "Regra 1 — detalhe": getattr(row, "Filter2018Rule1Detail", ""),
                "Regra 2 — resultado": "Aprovada" if bool(getattr(row, "Filter2018Rule2Pass", False)) else "Reprovada",
                "Regra 2 — detalhe": getattr(row, "Filter2018Rule2Detail", ""),
                "Regra 3 — resultado": "Aprovada" if bool(getattr(row, "Filter2018Rule3Pass", False)) else "Reprovada",
                "Regra 3 — gols do mandante nas últimas 5": getattr(row, "Filter2018Rule3Count", ""),
                "Regra 3 — detalhe": getattr(row, "Filter2018Rule3Detail", ""),
                "Regra 4 — resultado": "Aprovada" if bool(getattr(row, "Filter2018Rule4Pass", False)) else "Reprovada",
                "Regra 4 — gols do visitante nas últimas 5": getattr(row, "Filter2018Rule4Count", ""),
                "Regra 4 — detalhe": getattr(row, "Filter2018Rule4Detail", ""),
                "Último confronto direto — data": getattr(row, "Filter2018LastH2HDate", ""),
                "Último confronto direto — placar": getattr(row, "Filter2018LastH2HScore", ""),
                "Último confronto direto — ambas marcaram": getattr(row, "Filter2018LastH2HBothScored", ""),
                "Resumo do filtro 2018": getattr(row, "Filter2018Summary", ""),
                "Decisão operacional": getattr(row, "OperationalDecision", getattr(row, "Status", "")),
                "Mercado escolhido para simples": "Sim" if str(getattr(row, "Status", "")) == "OPERAR" else "Não",
                "Incluído na sugestão de múltipla": "Sim" if bool(getattr(row, "IncludedInMultiple", False)) else "Não",
                "Fator total da múltipla": getattr(row, "MultipleFactorTotal", ""),
                "Probabilidade conjunta da múltipla %": float(getattr(row, "MultipleJointProbability", 0.0) or 0.0) * 100.0,
                "Valor esperado da múltipla %": float(getattr(row, "MultipleExpectedValue", 0.0) or 0.0) * 100.0,
                "Versão do filtro 2018": EXPECTED_FILTER_API,
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

if "tex_operational_config" not in st.session_state:
    st.session_state.tex_operational_config = {
        "bankroll": 1000.0,
        "unit_percent": 1.0,
        "weekly_target": 5,
    }

if "tex_bankroll_input" not in st.session_state:
    st.session_state.tex_bankroll_input = float(
        st.session_state.tex_operational_config.get("bankroll", 1000.0)
    )
if "tex_unit_percent_input" not in st.session_state:
    st.session_state.tex_unit_percent_input = float(
        st.session_state.tex_operational_config.get("unit_percent", 1.0)
    )


def _apply_operational_config_automatically() -> None:
    current = dict(st.session_state.get("tex_operational_config", {}))
    updated = {
        "bankroll": float(st.session_state.get("tex_bankroll_input", 1000.0)),
        "unit_percent": float(st.session_state.get("tex_unit_percent_input", 1.0)),
        "weekly_target": 5,
    }
    if updated != current:
        st.session_state.tex_operational_config = updated
        invalidate_analysis()


with st.sidebar:
    st.header("Operação")
    st.number_input(
        "Banca informada para a análise (R$)",
        min_value=0.0,
        step=10.0,
        key="tex_bankroll_input",
        on_change=_apply_operational_config_automatically,
    )
    st.number_input(
        "Unidade fixa (%)",
        min_value=0.1,
        max_value=2.0,
        step=0.1,
        key="tex_unit_percent_input",
        on_change=_apply_operational_config_automatically,
    )
    st.info(
        "Os valores são aplicados automaticamente. O filtro de 2018 é o único portão "
        "de elegibilidade para apostas."
    )
    _apply_operational_config_automatically()
    current_operational_config = dict(st.session_state.tex_operational_config)
    bankroll = float(current_operational_config["bankroll"])
    unit_percent = float(current_operational_config["unit_percent"])
    weekly_target = 5
    max_entries = weekly_target  # compatibilidade com o contrato do núcleo isolado

    st.divider()
    st.caption(f"Fonte: {source}")
    st.caption(f"Partidas históricas: {len(matches):,}".replace(",", "."))
    st.caption(f"Ligas: {len(LEAGUES)}")
    if backtest_summary:
        st.caption(
            "O backtest legado da V28 permanece no pacote apenas para auditoria histórica. "
            "Ele não controla a seleção desta versão, que não possui meta mínima semanal."
        )
    if registered_week_counts:
        st.caption(f"Apostas já registradas por semana: {registered_week_counts}")
    if st.session_state.get("tex_ledger_sync_warning"):
        st.warning(
            "A planilha não pôde ser sincronizada. O histórico de apostas registrado nesta instalação "
            "pode estar incompleto até uma nova sincronização bem-sucedida."
        )
    google_diag = diagnostico_google(st.secrets) if callable(diagnostico_google) else {}
    if google_configurado(st.secrets):
        st.success("Planilha Google conectada")
        st.caption(
            f"Destino obrigatório: ID final …{google_diag.get('spreadsheet_id_final', '')} | "
            f"aba {google_diag.get('aba_eventos', 'entrada_jogos')}"
        )
        st.link_button("Abrir exatamente a planilha de gravação", url_planilha_configurada(st.secrets))
    else:
        st.error(
            "Gravação bloqueada: configure spreadsheet_id ou spreadsheet_url explicitamente nos Secrets. "
            + str(google_diag.get("erro") or "")
        )

st.markdown(
    '<div class="rule-box"><b>Regra operacional obrigatória:</b> todos os jogos são calculados e salvos. '
    'Somente os confrontos <b>aprovados integralmente no filtro de 2018</b> seguem para qualquer decisão de aposta. '
    'Depois da aprovação, o aplicativo realiza exclusivamente a análise estatística das probabilidades e a análise financeira das cotações. '
    'Não existe meta mínima de entradas nem complemento com valor esperado negativo.</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Limitação atual da fonte: o histórico carregado contém 24 ligas de pontos corridos. "
    "As últimas cinco partidas são buscadas sem separar casa e fora e atravessam temporadas; "
    "copas e amistosos só poderão entrar quando uma fonte futura os fornecer."
)

# Restaura o lote antes de desenhar a interface e antes de exibir o estado do autosave.
_ = games()

# Migração automática: lotes criados nas versões anteriores podem existir apenas em
# entrada_jogos. Ao abrir a V28.3.2, todas as odds desse lote são copiadas/atualizadas
# em catalogo_odds imediatamente, sem exigir o clique em ANALISAR TODO O LOTE.
if games() and google_configurado(st.secrets) and not st.session_state.get("tex_catalog_backfill_done"):
    try:
        backfill_records: list[dict] = []
        for pending_game in games():
            backfill_records.extend(
                criar_registros_cotacoes_digitadas(
                    dict(pending_game),
                    bankroll=float(bankroll),
                    interface_version=INTERFACE_VERSION,
                    core_api_version=EXPECTED_CORE_API,
                    model_version=MODEL_VERSION,
                    core_name=CORE_NAME,
                    app_name=APP_NAME,
                )
            )
        backfilled = salvar_cotacoes(st.secrets, backfill_records)
        st.session_state.tex_catalog_backfill_done = True
        st.session_state.tex_catalog_backfill_notice = (
            f"Catálogo pré-análise sincronizado: {backfilled} cotação(ões) do lote atual "
            "confirmada(s) em catalogo_odds."
        )
    except Exception as exc:
        st.session_state.tex_autosave_warning = (
            "O lote foi restaurado, mas as cotações pré-análise ainda não foram confirmadas "
            f"em catalogo_odds: {exc}"
        )

st.subheader("1. Adicionar partidas")
league_names = list(LEAGUES.values())
name_to_code = {name: code for code, name in LEAGUES.items()}

if st.session_state.pop("tex_flash", None):
    st.success(st.session_state.pop("tex_flash_message", "Partida salva."))
if st.session_state.get("tex_catalog_backfill_notice"):
    st.success(str(st.session_state.pop("tex_catalog_backfill_notice")))
if st.session_state.get("tex_autosave_notice"):
    st.info(str(st.session_state.pop("tex_autosave_notice")))
if st.session_state.get("tex_autosave_status"):
    st.caption("💾 " + str(st.session_state.get("tex_autosave_status")))
if st.session_state.get("tex_autosave_warning"):
    st.warning(str(st.session_state.get("tex_autosave_warning")))
last_confirmation = st.session_state.get("tex_last_sheet_confirmation")
if isinstance(last_confirmation, dict) and last_confirmation:
    st.success(
        "Última gravação comprovada: "
        f"aba {last_confirmation.get('Aba', '')}, linha {last_confirmation.get('Linha', '')}, "
        f"ID {last_confirmation.get('ID Evento', '')}."
    )
    if last_confirmation.get("Planilha URL"):
        st.link_button("Abrir a linha na planilha e conferir", str(last_confirmation.get("Planilha URL")))
    st.json({
        "Jogo": f"{last_confirmation.get('Mandante', '')} x {last_confirmation.get('Visitante', '')}",
        "Casa": last_confirmation.get("Casa de apostas", ""),
        "Cotações lidas de volta": last_confirmation.get("Cotações verificadas", {}),
    }, expanded=False)
last_batch = st.session_state.get("tex_last_batch_confirmation")
if isinstance(last_batch, dict) and last_batch:
    st.success(
        "Última gravação em lote comprovada: "
        f"{last_batch.get('Eventos confirmados', 0)} partida(s), linhas "
        f"{last_batch.get('Primeira linha', '?')}–{last_batch.get('Última linha', '?')} da aba "
        f"{last_batch.get('Aba', 'entrada_jogos')}; "
        f"{last_batch.get('Cotações no catálogo', 0)} cotação(ões) no catálogo."
    )
    if last_batch.get("Planilha URL"):
        st.link_button("Abrir o lote confirmado na planilha", str(last_batch.get("Planilha URL")))
if google_configurado(st.secrets):
    st.success("Persistência obrigatória ativa: cada partida e cada cotação são gravadas imediatamente em entrada_jogos e catalogo_odds, antes da análise.")
else:
    st.error("Persistência durável indisponível: configure o Google Sheets antes de inserir um lote importante.")


@_fragment
def render_match_selectors(form_version: int) -> None:
    """Atualiza somente liga e equipes, sem tocar nos campos de cotações."""
    selection_key = f"tex_selected_match_{form_version}"
    selector_row = st.columns([1.8, 1.4, 1.4])

    league_name = selector_row[0].selectbox(
        "Liga",
        league_names,
        index=None,
        placeholder="Selecione a liga",
        key=f"entry_league_{form_version}",
    )

    if league_name is None:
        st.session_state.pop(selection_key, None)
        selector_row[1].selectbox(
            "Mandante",
            [],
            index=None,
            placeholder="Selecione primeiro a liga",
            disabled=True,
            key=f"entry_home_{form_version}_empty",
        )
        selector_row[2].selectbox(
            "Visitante",
            [],
            index=None,
            placeholder="Selecione primeiro a liga",
            disabled=True,
            key=f"entry_away_{form_version}_empty",
        )
        st.caption("Selecione a liga para carregar o catálogo correto de equipes.")
        return

    code = name_to_code[league_name]
    available_teams = list(teams_by_code.get(code, []))
    if not available_teams:
        st.session_state.pop(selection_key, None)
        st.error(
            f"Não há equipes disponíveis para {league_name} na base carregada. "
            "Atualize a base ou verifique o relatório de carregamento."
        )
        return

    home = selector_row[1].selectbox(
        "Mandante",
        available_teams,
        index=None,
        placeholder="Selecione o mandante",
        key=f"entry_home_{form_version}_{code}",
    )
    away_options = [team for team in available_teams if team != home] if home else []
    away = selector_row[2].selectbox(
        "Visitante",
        away_options,
        index=None,
        placeholder="Selecione o visitante" if home else "Selecione primeiro o mandante",
        disabled=not bool(home),
        key=f"entry_away_{form_version}_{code}_{home or 'empty'}",
    )

    season_label = season_by_code.get(code, "")
    st.caption(
        f"Catálogo ativo: {league_name} — {len(available_teams)} equipes"
        + (f" — temporada {season_label}" if season_label != "" else "")
    )

    if home and away and home != away:
        st.session_state[selection_key] = {
            "Código da liga": code,
            "Liga": league_name,
            "Mandante": home,
            "Visitante": away,
        }
    else:
        st.session_state.pop(selection_key, None)


def render_game_entry() -> None:
    """Entrada em etapa única; seletores reativos e demais campos enviados em lote."""
    form_version = int(st.session_state.get("tex_form_version", 0))
    selection_key = f"tex_selected_match_{form_version}"

    with st.container(border=True):
        st.markdown("**Partida e cotações — etapa única**")
        st.caption(
            "Selecione liga e equipes e preencha os demais campos abaixo. "
            "A troca de liga atualiza somente os seletores; data, horário, casa e cotações permanecem estáveis."
        )

        render_match_selectors(form_version)

        with st.form(f"game_form_{form_version}", clear_on_submit=False):
            row_top = st.columns([1.0, 0.8, 1.8])
            game_date = row_top[0].date_input(
                "Data",
                value=None,
                format="DD/MM/YYYY",
                key=f"game_date_{form_version}",
            )
            game_time = row_top[1].time_input(
                "Horário",
                value=None,
                key=f"game_time_{form_version}",
            )
            bookmaker = row_top[2].text_input(
                "Casa de apostas",
                value="PIXBET",
                placeholder="Edite somente se usar outra casa",
                key=f"bookmaker_{form_version}",
            )

            st.markdown("**Mercados e cotações**")
            st.caption(
                "As cotações começam vazias. A casa padrão é PIXBET e pode ser editada."
            )

            use_1x2 = st.checkbox(
                "Resultado final 1X2",
                value=True,
                key=f"use_1x2_{form_version}",
            )
            a, b, c = st.columns(3)
            odd_h = a.number_input(
                "Cotação mandante",
                min_value=1.01,
                max_value=100.0,
                value=None,
                step=0.01,
                format="%.2f",
                placeholder="Digite a cotação",
                key=f"odd_h_{form_version}",
            )
            odd_d = b.number_input(
                "Cotação empate",
                min_value=1.01,
                max_value=100.0,
                value=None,
                step=0.01,
                format="%.2f",
                placeholder="Digite a cotação",
                key=f"odd_d_{form_version}",
            )
            odd_a = c.number_input(
                "Cotação visitante",
                min_value=1.01,
                max_value=100.0,
                value=None,
                step=0.01,
                format="%.2f",
                placeholder="Digite a cotação",
                key=f"odd_a_{form_version}",
            )

            use_ou = st.checkbox(
                "Mais/menos de 2,5 gols",
                value=True,
                key=f"use_ou_{form_version}",
            )
            a, b = st.columns(2)
            odd_o = a.number_input(
                "Cotação mais de 2,5",
                min_value=1.01,
                max_value=100.0,
                value=None,
                step=0.01,
                format="%.2f",
                placeholder="Digite a cotação",
                key=f"odd_o_{form_version}",
            )
            odd_u = b.number_input(
                "Cotação menos de 2,5",
                min_value=1.01,
                max_value=100.0,
                value=None,
                step=0.01,
                format="%.2f",
                placeholder="Digite a cotação",
                key=f"odd_u_{form_version}",
            )

            use_btts = st.checkbox(
                "Ambas marcam — análise complementar",
                value=False,
                key=f"use_btts_{form_version}",
            )
            a, b = st.columns(2)
            odd_by = a.number_input(
                "Cotação ambas — Sim",
                min_value=1.01,
                max_value=100.0,
                value=None,
                step=0.01,
                format="%.2f",
                placeholder="Digite a cotação",
                key=f"odd_by_{form_version}",
            )
            odd_bn = b.number_input(
                "Cotação ambas — Não",
                min_value=1.01,
                max_value=100.0,
                value=None,
                step=0.01,
                format="%.2f",
                placeholder="Digite a cotação",
                key=f"odd_bn_{form_version}",
            )

            submitted = st.form_submit_button(
                "ADICIONAR OU ATUALIZAR PARTIDA",
                type="primary",
                use_container_width=True,
            )

        if not submitted:
            return

        selected_match = st.session_state.get(selection_key)
        if not selected_match:
            st.error("Selecione liga, mandante e visitante antes de adicionar a partida.")
            return
        if game_date is None or game_time is None:
            st.error("Preencha a data e o horário da partida.")
            return
        if not any((use_1x2, use_ou, use_btts)):
            st.error("Ative ao menos um mercado.")
            return

        missing_odds: list[str] = []
        if use_1x2:
            missing_odds.extend(
                label for label, value in (
                    ("mandante", odd_h), ("empate", odd_d), ("visitante", odd_a)
                ) if value is None
            )
        if use_ou:
            missing_odds.extend(
                label for label, value in (
                    ("mais de 2,5", odd_o), ("menos de 2,5", odd_u)
                ) if value is None
            )
        if use_btts:
            missing_odds.extend(
                label for label, value in (
                    ("ambas marcam — Sim", odd_by), ("ambas marcam — Não", odd_bn)
                ) if value is None
            )
        if missing_odds:
            st.error("Preencha as cotações: " + ", ".join(missing_odds) + ".")
            return

        game_start = datetime.combine(game_date, game_time, tzinfo=FUSO)
        if game_start <= now_br():
            st.error(
                "A partida precisa estar programada para um horário futuro. "
                "O aplicativo é exclusivamente pré-jogo."
            )
            return

        try:
            if use_1x2:
                validate_market_odds("1X2", [float(odd_h), float(odd_d), float(odd_a)])
            if use_ou:
                validate_market_odds("OU25", [float(odd_o), float(odd_u)])
            if use_btts:
                validate_market_odds("BTTS", [float(odd_by), float(odd_bn)])
        except ValueError as exc:
            st.error(str(exc))
            return

        code = str(selected_match["Código da liga"])
        league_name = str(selected_match["Liga"])
        home = str(selected_match["Mandante"])
        away = str(selected_match["Visitante"])
        game = {
            "ID": _stable_game_id(game_date.isoformat(), code, home, away),
            "Data": game_date.isoformat(),
            "Hora": game_time.strftime("%H:%M"),
            "Código da liga": code,
            "Liga": league_name,
            "Mandante": home,
            "Visitante": away,
            "Casa de apostas": bookmaker.strip() or "PIXBET",
            "Odd mandante": float(odd_h) if use_1x2 else None,
            "Odd empate": float(odd_d) if use_1x2 else None,
            "Odd visitante": float(odd_a) if use_1x2 else None,
            "Odd mais de 2,5": float(odd_o) if use_ou else None,
            "Odd menos de 2,5": float(odd_u) if use_ou else None,
            "Odd ambas marcam — Sim": float(odd_by) if use_btts else None,
            "Odd ambas marcam — Não": float(odd_bn) if use_btts else None,
        }
        try:
            action = upsert_game(game, bankroll)
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.session_state.tex_form_version = form_version + 1
        st.session_state.pop(selection_key, None)
        st.session_state.tex_flash = True
        confirmacao = dict(st.session_state.get("tex_last_sheet_confirmation", {}))
        odds_salvas = confirmacao.get("Cotações verificadas", {})
        odds_texto = ", ".join(
            f"{nome}={valor}" for nome, valor in odds_salvas.items() if str(valor).strip()
        ) or "sem cotação"
        st.session_state.tex_flash_message = (
            f"Partida {action}: {home} x {away}. GRAVADA E RELIDA na aba "
            f"{confirmacao.get('Aba', 'entrada_jogos')}, linha {confirmacao.get('Linha', '?')}; "
            f"{confirmacao.get('Cotações no catálogo', 0)} cotação(ões) gravada(s) imediatamente "
            f"em catalogo_odds. Cotações conferidas: {odds_texto}."
        )
        st.rerun()



def _format_import_date(value: object) -> str:
    try:
        return pd.Timestamp(str(value)).strftime("%d/%m/%Y")
    except Exception:
        return str(value or "")


def render_bulk_import() -> None:
    """Importa a listagem visual: data, hora, equipes e Resultado Final 1X2."""
    with st.container(border=True):
        st.markdown("**Importar programação e cotações 1X2**")
        st.caption(
            "Cole a listagem principal da casa de apostas. O leitor extrai somente os dados "
            "seguros: data, horário, mandante, visitante e as três cotações de Resultado Final. "
            "Mais/Menos de 2,5 e Ambas Marcam serão complementados manualmente depois."
        )
        controls = st.columns([0.8, 1.5])
        import_year = controls[0].number_input(
            "Ano das partidas",
            min_value=2020,
            max_value=2100,
            value=int(date.today().year),
            step=1,
            key="tex_import_year",
        )
        bookmaker = controls[1].text_input(
            "Casa de apostas",
            value="PIXBET",
            key="tex_import_bookmaker",
        )
        import_mode = st.selectbox(
            "Destino desta importação",
            [
                "Criar novo lote — substituir apenas o lote exibido",
                "Adicionar ao lote atual",
            ],
            index=0,
            key="tex_import_mode",
            help=(
                "Criar novo lote remove as partidas anteriores somente da área ativa do aplicativo. "
                "Nada é apagado do catálogo de cotações, do histórico de análises ou da planilha."
            ),
        )
        replace_current_lot = import_mode.startswith("Criar novo lote")
        if games():
            active_leagues = sorted({str(item.get("Liga", "")) for item in games() if str(item.get("Liga", "")).strip()})
            st.caption(
                f"Lote ativo: {len(games())} partida(s)"
                + (f" — {', '.join(active_leagues[:3])}" if active_leagues else "")
                + (". A nova importação substituirá esta lista ativa." if replace_current_lot else ". Os novos jogos serão somados a ela.")
            )
        raw_text = st.text_area(
            "Programação copiada",
            height=300,
            placeholder=(
                "08/08\n16:00\nGrêmio\nSão Paulo SP\n\n"
                "Grêmio\n2.32\n\nEmpate\n3.09\n\nSão Paulo SP\n2.92"
            ),
            key="tex_import_text",
        )
        if st.button(
            "INTERPRETAR E PREENCHER AUTOMATICAMENTE",
            type="primary",
            use_container_width=True,
            key="tex_parse_import",
        ):
            parsed = parse_pasted_schedule(raw_text, default_year=int(import_year))
            if not parsed:
                st.session_state.pop("tex_import_preview", None)
                st.error(
                    "Nenhuma partida foi reconhecida. O texto precisa conter, nessa ordem: "
                    "data, horário, mandante, visitante e o primeiro bloco de Resultado Final."
                )
            else:
                resolved = resolve_imported_matches(
                    parsed,
                    teams_by_code=teams_by_code,
                    leagues=LEAGUES,
                )
                for item in resolved:
                    try:
                        kickoff = datetime.fromisoformat(
                            f"{item['Data']}T{item['Hora']}:00"
                        ).replace(tzinfo=FUSO)
                    except Exception:
                        kickoff = None
                    if kickoff is None or kickoff <= now_br():
                        item["Usar"] = False
                        item["Status"] = "REVISAR"
                        item["Diagnóstico"] = (
                            str(item.get("Diagnóstico", ""))
                            + " Data ou horário inválido/passado para uma análise pré-jogo."
                        ).strip()
                st.session_state.tex_import_preview = resolved
                st.success(
                    f"{len(resolved)} partida(s) identificada(s). Confira a prévia antes de gravar."
                )

        preview = st.session_state.get("tex_import_preview")
        if not preview:
            return

        preview_frame = pd.DataFrame(preview)
        recognized = int(preview_frame["Status"].eq("RECONHECIDO").sum())
        review = int(len(preview_frame) - recognized)
        c1, c2, c3 = st.columns(3)
        c1.metric("Partidas encontradas", len(preview_frame))
        c2.metric("Reconhecidas automaticamente", recognized)
        c3.metric("Precisam de revisão", review)
        st.caption(
            "A liga é inferida pelas duas equipes em conjunto. Ex.: Flamengo + São Paulo → "
            "Brasileirão Série A; NY City + Inter Miami → EUA - MLS. Você pode corrigir "
            "liga, nomes, data, horário ou cotações diretamente na tabela."
        )

        editable_columns = [
            "Usar", "Status", "Confiança", "Liga", "Data", "Hora",
            "Mandante", "Visitante", "Odd mandante", "Odd empate", "Odd visitante",
            "Diagnóstico",
        ]
        edited = st.data_editor(
            preview_frame[editable_columns],
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            disabled=["Status", "Confiança", "Diagnóstico"],
            column_config={
                "Usar": st.column_config.CheckboxColumn("Importar", default=True),
                "Liga": st.column_config.SelectboxColumn(
                    "Liga detectada",
                    options=league_names,
                    required=True,
                ),
                "Data": st.column_config.TextColumn("Data", help="AAAA-MM-DD"),
                "Hora": st.column_config.TextColumn("Hora", help="HH:MM"),
                "Odd mandante": st.column_config.NumberColumn("Casa", min_value=1.01, max_value=100.0, format="%.2f"),
                "Odd empate": st.column_config.NumberColumn("Empate", min_value=1.01, max_value=100.0, format="%.2f"),
                "Odd visitante": st.column_config.NumberColumn("Fora", min_value=1.01, max_value=100.0, format="%.2f"),
                "Diagnóstico": st.column_config.TextColumn("Diagnóstico", width="large"),
            },
            key="tex_import_editor",
        )

        selected = edited[edited["Usar"].fillna(False).astype(bool)].copy()
        destination_text = (
            "formarão um novo lote ativo" if replace_current_lot
            else "serão acrescentadas ao lote ativo"
        )
        st.info(
            f"{len(selected)} partida(s) marcada(s) {destination_text}. "
            "Os mercados adicionais permanecerão vazios até o preenchimento manual."
        )
        if not st.button(
            "GRAVAR PARTIDAS E COTAÇÕES 1X2",
            type="primary",
            use_container_width=True,
            disabled=selected.empty,
            key="tex_commit_import",
        ):
            return

        prepared: list[dict] = []
        errors: list[str] = []
        for position, row in selected.reset_index(drop=True).iterrows():
            label = f"Linha {position + 1}"
            league_name = str(row.get("Liga", "") or "").strip()
            code = name_to_code.get(league_name)
            if not code:
                errors.append(f"{label}: selecione uma liga válida.")
                continue
            home, home_score = resolve_team_in_league(str(row.get("Mandante", "")), code, teams_by_code)
            away, away_score = resolve_team_in_league(str(row.get("Visitante", "")), code, teams_by_code)
            if not home or home_score < 0.72:
                errors.append(f"{label}: mandante não reconhecido em {league_name}: {row.get('Mandante', '')!r}.")
                continue
            if not away or away_score < 0.72:
                errors.append(f"{label}: visitante não reconhecido em {league_name}: {row.get('Visitante', '')!r}.")
                continue
            if home == away:
                errors.append(f"{label}: mandante e visitante foram resolvidos como a mesma equipe.")
                continue
            try:
                game_date = pd.Timestamp(str(row.get("Data", ""))).date()
                game_time = datetime.strptime(str(row.get("Hora", "")), "%H:%M").time()
                kickoff = datetime.combine(game_date, game_time, tzinfo=FUSO)
            except Exception:
                errors.append(f"{label}: data ou horário inválido.")
                continue
            if kickoff <= now_br():
                errors.append(f"{label}: {home} x {away} não está em horário futuro.")
                continue
            odds = [parse_odd(row.get(column)) for column in ("Odd mandante", "Odd empate", "Odd visitante")]
            if any(value is None for value in odds):
                errors.append(f"{label}: complete as três cotações de Resultado Final.")
                continue
            try:
                validate_market_odds("1X2", [float(value) for value in odds])
            except ValueError as exc:
                errors.append(f"{label}: {exc}")
                continue
            prepared.append({
                "ID": _stable_game_id(game_date.isoformat(), code, home, away),
                "Data": game_date.isoformat(),
                "Hora": game_time.strftime("%H:%M"),
                "Código da liga": code,
                "Liga": league_name,
                "Mandante": home,
                "Visitante": away,
                "Casa de apostas": bookmaker.strip() or "PIXBET",
                "Odd mandante": float(odds[0]),
                "Odd empate": float(odds[1]),
                "Odd visitante": float(odds[2]),
                "Odd mais de 2,5": None,
                "Odd menos de 2,5": None,
                "Odd ambas marcam — Sim": None,
                "Odd ambas marcam — Não": None,
            })
        if errors:
            st.error("A importação foi bloqueada para evitar registros incorretos.")
            for error in errors[:20]:
                st.write("• " + error)
            return
        try:
            with st.status("Gravando partidas no Google Sheets...", expanded=True) as status:
                st.write(f"Enviando {len(prepared)} partida(s) e as respectivas cotações 1X2 em lote.")
                result = upsert_games_batch(
                    prepared, bankroll, replace_current_lot=replace_current_lot
                )
                status.update(label="Partidas gravadas e confirmadas.", state="complete", expanded=False)
        except Exception as exc:
            detalhe = str(exc)
            detalhe_minusculo = detalhe.lower()
            if any(chave in detalhe_minusculo for chave in (
                "[503]", "service unavailable", "temporarily unavailable",
                "backend error", "gateway timeout", "timed out", "timeout",
            )):
                st.error(
                    "O Google Sheets ficou temporariamente indisponível durante a gravação. "
                    "As partidas continuam preenchidas na tela. Esta versão verifica os IDs "
                    "antes de repetir a operação, evitando duplicações."
                )
            elif any(chave in detalhe_minusculo for chave in (
                "[429]", "quota", "too many requests", "resource_exhausted",
            )):
                st.error(
                    "O Google Sheets recusou temporariamente a gravação por limite de requisições. "
                    "As partidas continuam preenchidas; aguarde um instante e tente novamente."
                )
            else:
                st.error("A gravação não foi concluída. As partidas continuam preenchidas na tela.")
            with st.expander("Detalhes técnicos do erro"):
                st.code(detalhe)
            return
        st.session_state.pop("tex_import_preview", None)
        st.session_state.tex_flash = True
        mode_message = (
            "Novo lote ativo criado" if result.get("substituiu_lote")
            else "Jogos adicionados ao lote ativo"
        )
        st.session_state.tex_flash_message = (
            f"{mode_message}: {result['partidas_ativas']} partida(s) ativas; "
            f"{result['adicionadas']} nova(s), {result['atualizadas']} atualizada(s) e "
            f"{result['cotacoes']} cotação(ões) 1X2 confirmada(s). "
            "Os lotes anteriores permanecem preservados nas planilhas históricas."
        )
        st.rerun()


def render_bulk_odds_completion() -> None:
    """Complementação manual, móvel e em lote dos mercados não presentes na tela principal."""
    if not games():
        return
    with st.container(border=True):
        st.markdown("**Completar Mais/Menos de 2,5 e Ambas Marcam em lote**")
        st.caption(
            "Os valores importados de Resultado Final são preservados. Abra apenas os jogos "
            "que deseja completar. O salvamento de todas as alterações é feito em lote para "
            "não exceder a quota do Google Sheets."
        )
        with st.form("tex_bulk_completion_form", clear_on_submit=False):
            captured: list[tuple[int, object, object, object, object]] = []
            for index, item in enumerate(games()):
                title = (
                    f"{_format_import_date(item.get('Data'))} {item.get('Hora', '')} — "
                    f"{item.get('Mandante', '')} x {item.get('Visitante', '')}"
                )
                with st.expander(title, expanded=False):
                    st.caption(
                        f"1X2 já salvo: {item.get('Odd mandante') or '—'} | "
                        f"{item.get('Odd empate') or '—'} | {item.get('Odd visitante') or '—'}"
                    )
                    row_ou = st.columns(2)
                    odd_o = row_ou[0].number_input(
                        "Mais de 2,5",
                        min_value=1.01,
                        max_value=100.0,
                        value=item.get("Odd mais de 2,5"),
                        step=0.01,
                        format="%.2f",
                        key=f"bulk_o25_{item.get('ID', index)}",
                    )
                    odd_u = row_ou[1].number_input(
                        "Menos de 2,5",
                        min_value=1.01,
                        max_value=100.0,
                        value=item.get("Odd menos de 2,5"),
                        step=0.01,
                        format="%.2f",
                        key=f"bulk_u25_{item.get('ID', index)}",
                    )
                    row_btts = st.columns(2)
                    odd_y = row_btts[0].number_input(
                        "Ambas marcam — Sim",
                        min_value=1.01,
                        max_value=100.0,
                        value=item.get("Odd ambas marcam — Sim"),
                        step=0.01,
                        format="%.2f",
                        key=f"bulk_btts_y_{item.get('ID', index)}",
                    )
                    odd_n = row_btts[1].number_input(
                        "Ambas marcam — Não",
                        min_value=1.01,
                        max_value=100.0,
                        value=item.get("Odd ambas marcam — Não"),
                        step=0.01,
                        format="%.2f",
                        key=f"bulk_btts_n_{item.get('ID', index)}",
                    )
                    captured.append((index, odd_o, odd_u, odd_y, odd_n))
            submitted = st.form_submit_button(
                "SALVAR TODAS AS COTAÇÕES COMPLEMENTARES",
                type="primary",
                use_container_width=True,
            )
        if not submitted:
            return
        changed: list[dict] = []
        errors: list[str] = []
        for index, odd_o, odd_u, odd_y, odd_n in captured:
            original = dict(games()[index])
            title = f"{original.get('Mandante')} x {original.get('Visitante')}"
            if (odd_o is None) != (odd_u is None):
                errors.append(f"{title}: preencha as duas cotações de Mais/Menos de 2,5 ou deixe ambas vazias.")
                continue
            if (odd_y is None) != (odd_n is None):
                errors.append(f"{title}: preencha Sim e Não de Ambas Marcam ou deixe ambos vazios.")
                continue
            try:
                if odd_o is not None:
                    validate_market_odds("OU25", [float(odd_o), float(odd_u)])
                if odd_y is not None:
                    validate_market_odds("BTTS", [float(odd_y), float(odd_n)])
            except ValueError as exc:
                errors.append(f"{title}: {exc}")
                continue
            candidate = dict(original)
            candidate.update({
                "Odd mais de 2,5": float(odd_o) if odd_o is not None else None,
                "Odd menos de 2,5": float(odd_u) if odd_u is not None else None,
                "Odd ambas marcam — Sim": float(odd_y) if odd_y is not None else None,
                "Odd ambas marcam — Não": float(odd_n) if odd_n is not None else None,
            })
            changed_keys = (
                "Odd mais de 2,5", "Odd menos de 2,5",
                "Odd ambas marcam — Sim", "Odd ambas marcam — Não",
            )
            if any(candidate.get(key) != original.get(key) for key in changed_keys):
                changed.append(candidate)
        if errors:
            st.error("As alterações não foram salvas.")
            for error in errors[:20]:
                st.write("• " + error)
            return
        if not changed:
            st.info("Nenhuma cotação complementar foi alterada.")
            return
        try:
            result = upsert_games_batch(changed, bankroll)
        except Exception as exc:
            st.error(str(exc))
            return
        st.session_state.tex_flash = True
        st.session_state.tex_flash_message = (
            f"Cotações complementares salvas em lote para {len(changed)} partida(s); "
            f"{result['cotacoes']} registro(s) confirmado(s) no catálogo."
        )
        st.rerun()


manual_tab, import_tab = st.tabs(["Cadastro manual", "Colar jogos e cotações 1X2"])
with manual_tab:
    render_game_entry()
with import_tab:
    render_bulk_import()

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
    render_bulk_odds_completion()
    remove_col, backup_col = st.columns([3, 1])
    labels = [f"{index + 1}. {item['Mandante']} x {item['Visitante']} — {item['Liga']}" for index, item in enumerate(games())]
    remove_label = remove_col.selectbox("Remover partida", ["Nenhuma"] + labels)
    if remove_col.button("REMOVER SELECIONADA", use_container_width=True) and remove_label != "Nenhuma":
        index = labels.index(remove_label)
        try:
            remove_game(index)
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            st.rerun()
    backup_col.download_button(
        "BAIXAR BACKUP DO LOTE",
        games_frame().to_csv(index=False).encode("utf-8-sig"),
        "lote_pendente_tex_statistics.csv",
        "text/csv",
        use_container_width=True,
    )
    with st.expander("Apagar todo o lote", expanded=False):
        confirm_clear = st.checkbox(
            "Confirmo que desejo apagar todas as partidas do lote e atualizar o autosave.",
            value=False,
            key="tex_confirm_clear_lot",
        )
        if st.button(
            "APAGAR TODO O LOTE",
            disabled=not confirm_clear,
            use_container_width=True,
        ):
            try:
                clear_games()
            except RuntimeError as exc:
                st.error(str(exc))
            else:
                st.session_state.tex_form_version = int(st.session_state.get("tex_form_version", 0)) + 1
                st.session_state.tex_flash = True
                st.session_state.tex_flash_message = "Lote apagado após confirmação explícita."
                st.rerun()

    if st.button("ANALISAR TODO O LOTE", type="primary", use_container_width=True):
        try:
            _confirmar_lote_remoto_antes_da_analise()
        except Exception as exc:
            st.error(f"Análise bloqueada: {exc}")
            st.stop()
        current_games = games_frame()
        _legacy_entries, _legacy_readings, base_evaluations, diagnostics = analyze_games(
            current_games,
            matches,
            v28_model,
            bankroll=bankroll,
            unit_fraction=unit_percent / 100.0,
            max_entries=int(max_entries),
            existing_week_counts=registered_week_counts,
            existing_match_ids=registered_match_ids,
        )
        # O núcleo calcula probabilidades para TODOS os jogos, inclusive os reprovados.
        # Isso preserva integralmente a base histórica. O filtro atua apenas como portão operacional.
        base_evaluations = enrich_with_standings(base_evaluations, current_games, matches)
        filter_results = evaluate_lot_2018(current_games, matches)
        form_contexts = build_lot_form_contexts(current_games, matches)
        filtered_evaluations = attach_filter_results(base_evaluations, filter_results)
        entries, readings, evaluations, multiple_summary = build_operational_outputs(
            filtered_evaluations,
            bankroll=float(bankroll),
            unit_fraction=float(unit_percent) / 100.0,
        )
        for frame in (entries, readings, evaluations):
            if not frame.empty:
                frame["MultipleFactorTotal"] = float(multiple_summary.factor)
                frame["MultipleJointProbability"] = float(multiple_summary.joint_probability)
                frame["MultipleExpectedValue"] = float(multiple_summary.expected_value)
        st.session_state.tex_entries = entries
        st.session_state.tex_readings = readings
        st.session_state.tex_evaluations = evaluations
        st.session_state.tex_filter_results = filter_results
        st.session_state.tex_form_contexts = form_contexts
        st.session_state.tex_multiple_summary = multiple_summary
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
        if google_configurado(st.secrets):
            try:
                catalog_records = make_catalog_records(evaluations, bankroll)
                analysis_records = make_analysis_records(evaluations, unit_percent / 100.0)
                # Grava diretamente, sem reler abas inteiras. A releitura anterior podia
                # estourar a quota do Google e impedir qualquer salvamento. A deduplicação
                # da sessão usa os IDs determinísticos no cache do módulo de armazenamento.
                saved_odds = salvar_cotacoes(st.secrets, catalog_records)
                saved_analysis = salvar_analises(st.secrets, analysis_records)
                st.session_state.tex_analysis_autosave = (
                    f"Análise salva automaticamente na planilha: {saved_odds} cotação(ões) e "
                    f"{saved_analysis} probabilidade(s) novas."
                )
                st.session_state.pop("tex_analysis_autosave_error", None)
                st.session_state.pop("tex_analysis_autosave_error_details", None)
            except Exception as exc:
                detalhe = str(exc)
                detalhe_minusculo = detalhe.lower()
                if any(chave in detalhe_minusculo for chave in ("429", "quota", "too many requests", "resource_exhausted")):
                    resumo = (
                        "A análise permaneceu na tela, mas a quota temporária do Google Sheets "
                        "impediu a confirmação do salvamento. Aguarde cerca de um minuto e repita."
                    )
                elif "conferência" in detalhe_minusculo or "conferencia" in detalhe_minusculo:
                    resumo = (
                        "A análise permaneceu na tela. A gravação foi enviada, mas a conferência "
                        "dos valores não pôde ser validada. Repita o salvamento nesta versão."
                    )
                else:
                    resumo = (
                        "A análise permaneceu na tela, mas o salvamento automático não foi concluído. "
                        "Use o botão de repetir salvamento."
                    )
                st.session_state.tex_analysis_autosave_error = resumo
                st.session_state.tex_analysis_autosave_error_details = detalhe

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
filter_results = st.session_state.get("tex_filter_results", pd.DataFrame())
diagnostics = st.session_state.get("tex_diagnostics", pd.DataFrame())
form_contexts = st.session_state.get("tex_form_contexts", {})
if not isinstance(form_contexts, dict):
    form_contexts = {}
if not form_contexts and (not readings.empty or not diagnostics.empty) and games():
    try:
        form_contexts = build_lot_form_contexts(games_frame(), matches)
        st.session_state.tex_form_contexts = form_contexts
    except Exception:
        form_contexts = {}
multiple_summary = st.session_state.get("tex_multiple_summary")
ai_summary = st.session_state.get("tex_ai_summary", "")
if st.session_state.get("tex_analysis_autosave"):
    st.success(str(st.session_state.pop("tex_analysis_autosave")))
if st.session_state.get("tex_analysis_autosave_error"):
    st.error(str(st.session_state.get("tex_analysis_autosave_error")))
    detalhes_salvamento = str(st.session_state.get("tex_analysis_autosave_error_details") or "").strip()
    if detalhes_salvamento:
        with st.expander("Detalhes técnicos do salvamento"):
            st.code(detalhes_salvamento, language=None, wrap_lines=True)


def pct(value: float) -> str:
    return f"{float(value):.1%}"


def money(value: float) -> str:
    return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fair_odd_from_probability(value: float) -> float:
    probability = float(value or 0.0)
    return 1.0 / probability if probability > 0.0 else float("nan")


def _safe_float(value) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number


def render_expected_goals(row: pd.Series, home: str, away: str) -> None:
    """Exibe a projeção de gols já calculada pelo motor estatístico."""
    home_expected = _safe_float(row.get("LambdaHome"))
    away_expected = _safe_float(row.get("LambdaAway"))
    if pd.isna(home_expected) or pd.isna(away_expected):
        st.info("A projeção de gols não ficou disponível para esta partida.")
        return

    total_expected = home_expected + away_expected
    st.markdown("##### Projeção de gols do modelo")
    goal_home, goal_away, goal_total = st.columns(3)
    goal_home.metric(f"Gols esperados — {home}", f"{home_expected:.2f}")
    goal_away.metric(f"Gols esperados — {away}", f"{away_expected:.2f}")
    goal_total.metric("Gols esperados — total", f"{total_expected:.2f}")
    st.caption(
        "Os gols esperados representam médias probabilísticas usadas pelo modelo de Poisson; "
        "não correspondem a uma previsão de placar exato."
    )


def evaluation_table(frame: pd.DataFrame, *, technical: bool = False) -> pd.DataFrame:
    """Tabela enxuta por padrão; cálculos auxiliares ficam no modo técnico."""
    if frame.empty:
        return frame.copy()

    source = frame.copy()

    # A oportunidade precisa ser identificável sem o usuário procurar a partida
    # em outra seção da tela. Mantemos a identificação antes dos dados financeiros.
    home = (
        source["Home"].fillna("").astype(str).str.strip()
        if "Home" in source.columns
        else pd.Series("", index=source.index, dtype="object")
    )
    away = (
        source["Away"].fillna("").astype(str).str.strip()
        if "Away" in source.columns
        else pd.Series("", index=source.index, dtype="object")
    )
    source["MatchDisplay"] = home.copy()
    both_teams = home.ne("") & away.ne("")
    source.loc[both_teams, "MatchDisplay"] = home[both_teams] + " x " + away[both_teams]
    source.loc[home.eq("") & away.ne(""), "MatchDisplay"] = away[home.eq("") & away.ne("")]
    source["LeagueDisplay"] = (
        source["League"].fillna("").astype(str).str.strip()
        if "League" in source.columns
        else ""
    )
    if "DateParsed" in source.columns:
        parsed_dates = pd.to_datetime(source["DateParsed"], errors="coerce")
        source["GameDateDisplay"] = parsed_dates.dt.strftime("%d/%m/%Y").fillna("")
    else:
        source["GameDateDisplay"] = ""
    source["GameTimeDisplay"] = (
        source["Time"].fillna("").astype(str).str.strip().str.slice(0, 5)
        if "Time" in source.columns
        else ""
    )

    source["FairOdd"] = pd.to_numeric(
        source.get("ConservativeProbability"), errors="coerce"
    ).map(lambda value: _fair_odd_from_probability(value) if pd.notna(value) else float("nan"))

    if technical:
        columns = [
            "Status", "MatchDisplay", "LeagueDisplay", "GameDateDisplay", "GameTimeDisplay",
            "MarketName", "Selection", "Odd", "EffectiveOdd", "FairOdd",
            "RequiredOddForOperation", "MarketProbability", "RawSportsProbability",
            "DecisionProbability", "ConservativeProbability", "EmpiricalHitRate",
            "ProfileSample", "SampleConfidence", "Reliability", "ModelMarketDifference",
            "ModelSportsDifference", "MaximumComponentDisagreement", "DisagreementLevel",
            "Filter2018Status", "OperationalDecision", "IncludedInMultiple",
            "PortfolioTier", "StakeMultiplier", "ModelExpectedValue",
            "ConservativeExpectedValue", "Reason",
        ]
        percentage_columns = (
            "MarketProbability", "RawSportsProbability", "DecisionProbability",
            "ConservativeProbability", "EmpiricalHitRate", "Reliability",
            "ModelExpectedValue", "ConservativeExpectedValue", "ModelMarketDifference",
            "ModelSportsDifference", "MaximumComponentDisagreement",
        )
        rename = {
            "Status": "Situação", "MatchDisplay": "Partida", "LeagueDisplay": "Liga",
            "GameDateDisplay": "Data", "GameTimeDisplay": "Hora",
            "MarketName": "Mercado", "Selection": "Seleção",
            "Odd": "Cotação atual", "EffectiveOdd": "Cotação após desconto de 2%",
            "FairOdd": "Cotação justa", "RequiredOddForOperation": "Cotação mínima para operar",
            "MarketProbability": "Mercado sem margem",
            "RawSportsProbability": "Probabilidade esportiva",
            "DecisionProbability": "Probabilidade do modelo",
            "ConservativeProbability": "Probabilidade final",
            "EmpiricalHitRate": "Acerto histórico da faixa",
            "ProfileSample": "Amostra histórica da faixa",
            "SampleConfidence": "Confiança estatística da amostra",
            "Reliability": "Estabilidade da calibração",
            "ModelMarketDifference": "Diferença modelo–mercado",
            "ModelSportsDifference": "Diferença modelo–esportivo",
            "MaximumComponentDisagreement": "Maior desacordo entre componentes",
            "DisagreementLevel": "Nível de desacordo",
            "Filter2018Status": "Filtro de 2018",
            "OperationalDecision": "Decisão operacional",
            "IncludedInMultiple": "Incluído na múltipla",
            "PortfolioTier": "Faixa da carteira",
            "StakeMultiplier": "Multiplicador da unidade",
            "ModelExpectedValue": "Valor esperado do modelo",
            "ConservativeExpectedValue": "Valor esperado final",
            "Reason": "Motivo",
        }
    else:
        columns = [
            "Status", "MatchDisplay", "LeagueDisplay", "GameDateDisplay", "GameTimeDisplay",
            "MarketName", "Selection", "Odd", "FairOdd",
            "RequiredOddForOperation", "ConservativeProbability",
            "ConservativeExpectedValue", "OperationalDecision", "Reason",
        ]
        percentage_columns = ("ConservativeProbability", "ConservativeExpectedValue")
        rename = {
            "Status": "Situação", "MatchDisplay": "Partida", "LeagueDisplay": "Liga",
            "GameDateDisplay": "Data", "GameTimeDisplay": "Hora",
            "MarketName": "Mercado", "Selection": "Seleção",
            "Odd": "Cotação atual", "FairOdd": "Cotação justa",
            "RequiredOddForOperation": "Cotação mínima para operar",
            "ConservativeProbability": "Probabilidade final",
            "ConservativeExpectedValue": "Valor esperado final",
            "OperationalDecision": "Decisão financeira", "Reason": "Motivo",
        }

    out = source[[column for column in columns if column in source.columns]].copy()
    for column in percentage_columns:
        if column in out:
            out[column] = pd.to_numeric(out[column], errors="coerce") * 100.0
    return out.rename(columns=rename)



def approved_games_summary_table(
    game_records: list[dict],
    filter_results: pd.DataFrame,
    readings: pd.DataFrame,
) -> pd.DataFrame:
    """Monta um resumo compacto de todos os jogos aprovados no filtro de 2018.

    A tabela preserva a ordem original do lote e inclui o número da partida na
    seção detalhada, permitindo localizar rapidamente o cartão correspondente.
    Jogos aprovados sem leitura estatística continuam aparecendo no resumo.
    """
    columns = [
        "Nº", "Partida", "Liga", "Data e hora", "Resultado da análise",
        "Melhor mercado", "Probabilidade final", "Cotação atual",
        "Cotação justa", "Valor esperado",
    ]
    if not isinstance(filter_results, pd.DataFrame) or filter_results.empty:
        return pd.DataFrame(columns=columns)

    approved_by_id: dict[str, dict] = {}
    for _, row in filter_results.iterrows():
        input_id = str(row.get("InputID", ""))
        approved_value = row.get("Filter2018Approved", False)
        if input_id and pd.notna(approved_value) and bool(approved_value):
            approved_by_id[input_id] = row.to_dict()

    reading_by_id: dict[str, dict] = {}
    if isinstance(readings, pd.DataFrame) and not readings.empty and "InputID" in readings.columns:
        for _, row in readings.drop_duplicates("InputID", keep="first").iterrows():
            reading_by_id[str(row.get("InputID", ""))] = row.to_dict()

    records: list[dict] = []
    for game_number, game in enumerate(game_records, start=1):
        input_id = str(game.get("ID", ""))
        if input_id not in approved_by_id:
            continue

        reading = reading_by_id.get(input_id, {})
        probability = pd.to_numeric(
            pd.Series([reading.get("ConservativeProbability")]), errors="coerce"
        ).iloc[0]
        odd = pd.to_numeric(pd.Series([reading.get("Odd")]), errors="coerce").iloc[0]
        expected_value = pd.to_numeric(
            pd.Series([reading.get("ConservativeExpectedValue")]), errors="coerce"
        ).iloc[0]
        fair_odd = (
            _fair_odd_from_probability(float(probability))
            if pd.notna(probability) and float(probability) > 0
            else float("nan")
        )

        game_date = pd.to_datetime(game.get("Data"), errors="coerce")
        date_display = game_date.strftime("%d/%m/%Y") if pd.notna(game_date) else str(game.get("Data", ""))
        hour_display = str(game.get("Hora", "")).strip()[:5]
        date_time_display = " · ".join(part for part in (date_display, hour_display) if part)

        market = str(reading.get("MarketName", "")).strip()
        selection = str(reading.get("Selection", "")).strip()
        if market and selection and selection.casefold().startswith(market.casefold()):
            market_display = selection
        else:
            market_display = " — ".join(part for part in (market, selection) if part)
        status = str(reading.get("Status", "ANÁLISE NÃO DISPONÍVEL")).strip() or "ANÁLISE NÃO DISPONÍVEL"

        records.append({
            "Nº": game_number,
            "Partida": f"{game.get('Mandante', '')} x {game.get('Visitante', '')}",
            "Liga": str(game.get("Liga", "")),
            "Data e hora": date_time_display,
            "Resultado da análise": status,
            "Melhor mercado": market_display or "Não disponível",
            "Probabilidade final": float(probability) * 100.0 if pd.notna(probability) else float("nan"),
            "Cotação atual": float(odd) if pd.notna(odd) else float("nan"),
            "Cotação justa": float(fair_odd) if pd.notna(fair_odd) else float("nan"),
            "Valor esperado": float(expected_value) * 100.0 if pd.notna(expected_value) else float("nan"),
        })

    return pd.DataFrame(records, columns=columns)


def _form_badges(records: list[dict]) -> str:
    if not records:
        return '<span class="form-badge form-na">—</span>'
    badges: list[str] = []
    for item in records:
        result = str(item.get("Result", "")).upper()
        css = {"V": "form-v", "E": "form-e", "D": "form-d"}.get(result, "form-na")
        title = html.escape(
            f"{item.get('Date', '')} · {item.get('Venue', '')} · "
            f"{item.get('Opponent', '')} · {item.get('Score', '')}"
        )
        badges.append(
            f'<span class="form-badge {css}" title="{title}">{html.escape(result or "—")}</span>'
        )
    return "".join(badges)


def _form_table(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["Data", "Local", "Adversário", "Placar", "R"])
    return pd.DataFrame([
        {
            "Data": item.get("Date", ""),
            "Local": item.get("VenueShort", ""),
            "Adversário": item.get("Opponent", ""),
            "Placar": item.get("Score", ""),
            "R": item.get("Result", ""),
        }
        for item in records
    ])


def _standing_text(standing: dict) -> str:
    if not standing or not standing.get("Available"):
        return "Classificação indisponível na base para a data do evento."
    return (
        f"<b>{int(standing.get('Position', 0))}º lugar</b> · "
        f"{int(standing.get('Points', 0))} pontos · {int(standing.get('Games', 0))} jogos · "
        f"{int(standing.get('Wins', 0))}V/{int(standing.get('Draws', 0))}E/{int(standing.get('Losses', 0))}D · "
        f"gols {int(standing.get('GoalsFor', 0))}:{int(standing.get('GoalsAgainst', 0))}"
    )


def _render_team_context(
    *,
    team: str,
    role: str,
    standing: dict,
    overall: list[dict],
    venue_specific: list[dict],
    venue_title: str,
) -> None:
    st.markdown(
        '<div class="team-context">'
        f'<div class="team-context-title">{html.escape(role)} — {html.escape(team)}</div>'
        f'<div class="team-context-meta">{_standing_text(standing)}</div>'
        '<div class="form-strip"><span class="form-label">Forma geral:</span>'
        f'{_form_badges(overall)}</div>'
        f'<div class="form-strip"><span class="form-label">{html.escape(venue_title)}:</span>'
        f'{_form_badges(venue_specific)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_game_form_context(context: dict) -> None:
    if not context:
        st.info("Classificação e forma recente não puderam ser montadas para esta partida.")
        return
    season = int(context.get("StandingsSeason", 0) or 0)
    title_suffix = f" — temporada {season}" if season else ""
    st.markdown(f"##### Classificação e forma antes da partida{title_suffix}")
    st.caption("V = vitória · E = empate · D = derrota. Todos os registros são anteriores à data do confronto analisado.")
    home_col, away_col = st.columns(2)
    with home_col:
        _render_team_context(
            team=str(context.get("HomeTeam", "Mandante")),
            role="Mandante",
            standing=dict(context.get("HomeStanding") or {}),
            overall=list(context.get("HomeOverall") or []),
            venue_specific=list(context.get("HomeAtHome") or []),
            venue_title="Últimos 5 em casa",
        )
    with away_col:
        _render_team_context(
            team=str(context.get("AwayTeam", "Visitante")),
            role="Visitante",
            standing=dict(context.get("AwayStanding") or {}),
            overall=list(context.get("AwayOverall") or []),
            venue_specific=list(context.get("AwayAway") or []),
            venue_title="Últimos 5 fora",
        )

    with st.expander("Ver os placares dos jogos recentes", expanded=False):
        home_details, away_details = st.columns(2)
        with home_details:
            st.markdown(f"**{context.get('HomeTeam', 'Mandante')} — últimos 5, qualquer mando**")
            st.dataframe(
                _form_table(list(context.get("HomeOverall") or [])),
                hide_index=True,
                use_container_width=True,
            )
            st.markdown(f"**{context.get('HomeTeam', 'Mandante')} — últimos 5 em casa**")
            st.dataframe(
                _form_table(list(context.get("HomeAtHome") or [])),
                hide_index=True,
                use_container_width=True,
            )
        with away_details:
            st.markdown(f"**{context.get('AwayTeam', 'Visitante')} — últimos 5, qualquer mando**")
            st.dataframe(
                _form_table(list(context.get("AwayOverall") or [])),
                hide_index=True,
                use_container_width=True,
            )
            st.markdown(f"**{context.get('AwayTeam', 'Visitante')} — últimos 5 fora**")
            st.dataframe(
                _form_table(list(context.get("AwayAway") or [])),
                hide_index=True,
                use_container_width=True,
            )
        st.caption(str(context.get("SourceNote", "")))


if not readings.empty or not diagnostics.empty:
    st.subheader("3. Resultado completo")

    approved_count = (
        int(filter_results["Filter2018Approved"].fillna(False).astype(bool).sum())
        if isinstance(filter_results, pd.DataFrame) and not filter_results.empty
        else 0
    )
    rejected_count = (
        int(len(filter_results) - approved_count)
        if isinstance(filter_results, pd.DataFrame) and not filter_results.empty
        else 0
    )
    multiple_selections = (
        multiple_summary.selections
        if multiple_summary is not None and hasattr(multiple_summary, "selections")
        else pd.DataFrame()
    )
    analyzed_games = int((diagnostics["Situação"] == "ANALISADO").sum()) if not diagnostics.empty else 0
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Partidas calculadas", analyzed_games)
    m2.metric("Aprovadas no filtro", approved_count)
    m3.metric("Eliminadas no filtro", rejected_count)
    m4.metric("Apostas simples", len(entries))
    m5.metric("Itens na múltipla", len(multiple_selections))

    st.markdown("### Resumo dos jogos aprovados")
    approved_summary = approved_games_summary_table(games(), filter_results, readings)
    if approved_summary.empty:
        st.info("Nenhuma partida foi aprovada no filtro de 2018 neste lote.")
    else:
        st.success(
            f"{len(approved_summary)} partida(s) aprovada(s). "
            "Todas aparecem abaixo, inclusive as que não apresentaram cotação favorável."
        )
        st.dataframe(
            approved_summary,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Nº": st.column_config.NumberColumn(format="%d"),
                "Probabilidade final": st.column_config.ProgressColumn(
                    format="%.1f%%", min_value=0, max_value=100
                ),
                "Cotação atual": st.column_config.NumberColumn(format="%.2f"),
                "Cotação justa": st.column_config.NumberColumn(format="%.2f"),
                "Valor esperado": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
        st.caption(
            "O número da primeira coluna corresponde à posição do jogo na seção 'Análise de cada partida'. "
            "Assim, você identifica imediatamente quais eventos passaram no filtro sem percorrer os reprovados."
        )

    st.markdown("### Lista de verificação do filtro de 2018")
    st.caption(
        "Este é o único portão de elegibilidade esportiva. O resultado não apaga cálculos: "
        "probabilidades e cotações de todos os jogos continuam armazenadas na planilha."
    )
    if isinstance(filter_results, pd.DataFrame) and not filter_results.empty:
        filter_view = filter_results[[
            "InputID", "Filter2018Status", "Filter2018Rule1Basis",
            "Filter2018Rule3Count", "Filter2018Rule4Count",
            "Filter2018LastH2HScore", "Filter2018Summary",
        ]].copy()
        game_names = {str(item["ID"]): f"{item['Mandante']} x {item['Visitante']}" for item in games()}
        filter_view.insert(1, "Partida", filter_view["InputID"].astype(str).map(game_names))
        filter_view = filter_view.drop(columns=["InputID"]).rename(columns={
            "Filter2018Status": "Resultado",
            "Filter2018Rule1Basis": "Regra 1 — fundamento",
            "Filter2018Rule3Count": "Mandante marcou em",
            "Filter2018Rule4Count": "Visitante marcou em",
            "Filter2018LastH2HScore": "Último confronto direto",
            "Filter2018Summary": "Resumo",
        })
        st.dataframe(filter_view, hide_index=True, use_container_width=True)

    st.markdown("### Sugestão de múltipla")
    if multiple_summary is not None and len(multiple_selections) >= 2:
        reference_stake = float(bankroll) * float(unit_percent) / 100.0
        potential_return = reference_stake * float(multiple_summary.factor)
        potential_profit = potential_return - reference_stake
        st.markdown(
            '<div class="multiple-card"><b>SUGESTÃO DE MÚLTIPLA</b><br>'
            'Somente jogos aprovados no filtro de 2018. Para cada confronto, foi escolhido um único mercado: '
            'o de maior probabilidade final entre as opções com cotação financeiramente favorável.</div>',
            unsafe_allow_html=True,
        )
        multi_view = multiple_selections[[
            "League", "Home", "Away", "MarketName", "Selection",
            "ConservativeProbability", "Odd", "ConservativeExpectedValue",
        ]].copy()
        multi_view["FairOdd"] = pd.to_numeric(
            multi_view["ConservativeProbability"], errors="coerce"
        ).map(lambda value: _fair_odd_from_probability(value) if pd.notna(value) else float("nan"))
        multi_view.insert(1, "Partida", multi_view["Home"].astype(str) + " x " + multi_view["Away"].astype(str))
        multi_view = multi_view.drop(columns=["Home", "Away"]).rename(columns={
            "League": "Liga", "MarketName": "Mercado", "Selection": "Seleção",
            "ConservativeProbability": "Probabilidade final",
            "Odd": "Cotação", "FairOdd": "Cotação justa",
            "ConservativeExpectedValue": "Valor esperado final",
        })
        st.dataframe(
            multi_view, hide_index=True, use_container_width=True,
            column_config={
                "Probabilidade final": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=1),
                "Cotação": st.column_config.NumberColumn(format="%.2f"),
                "Cotação justa": st.column_config.NumberColumn(format="%.2f"),
                "Valor esperado final": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
        a, b, c, d = st.columns(4)
        a.metric("Fator total", f"{float(multiple_summary.factor):.2f}")
        b.metric("Probabilidade conjunta estimada", pct(float(multiple_summary.joint_probability)))
        c.metric("Valor esperado conjunto", pct(float(multiple_summary.expected_value)))
        d.metric("Retorno com uma unidade", money(potential_return), f"Lucro potencial {money(potential_profit)}")
        st.caption(
            "A probabilidade conjunta é uma aproximação obtida pelo produto das probabilidades individuais. "
            "O fator total é o produto das cotações informadas. A entrada de referência é uma unidade da banca atual."
        )
    elif multiple_summary is not None and len(multiple_selections) == 1:
        st.info(
            "Há apenas uma seleção que atende simultaneamente ao filtro, à análise estatística e ao preço atual. "
            "Ela permanece como oportunidade individual; uma múltipla exige pelo menos dois confrontos."
        )
    else:
        st.info(
            "Nenhuma sugestão de múltipla foi formada. Isso ocorre quando menos de duas partidas aprovadas "
            "possuem um mercado com cotação financeiramente favorável."
        )

    st.markdown("### Apostas individuais")
    if entries.empty:
        st.info(
            "Nenhuma partida aprovada apresentou cotação favorável no cenário conservador. "
            "Os eventos continuam aptos e analisados, mas não há entrada ao preço atual."
        )
    else:
        st.success(
            f"{len(entries)} oportunidade(s) individual(is) identificada(s). "
            "Não existe meta mínima nem inclusão de complemento com valor esperado negativo."
        )
        st.caption(
            "Cada oportunidade mostra agora a partida, a liga, a data e o horário antes do mercado recomendado."
        )
        st.dataframe(
            evaluation_table(entries),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Probabilidade final": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Cotação atual": st.column_config.NumberColumn(format="%.2f"),
                "Cotação justa": st.column_config.NumberColumn(format="%.2f"),
                "Cotação mínima para operar": st.column_config.NumberColumn(format="%.2f"),
                "Valor esperado final": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    st.markdown("### Análise de cada partida")
    filter_by_id = (
        filter_results.set_index(filter_results["InputID"].astype(str)).to_dict("index")
        if isinstance(filter_results, pd.DataFrame) and not filter_results.empty
        else {}
    )
    for game_index, game in enumerate(games(), start=1):
        input_id = str(game["ID"])
        game_filter = filter_by_id.get(input_id, {})
        game_reading = readings[readings["InputID"].astype(str).eq(input_id)] if not readings.empty else pd.DataFrame()
        game_evaluations = evaluations[evaluations["InputID"].astype(str).eq(input_id)] if not evaluations.empty else pd.DataFrame()
        approved = bool(game_filter.get("Filter2018Approved", False))

        with st.container(border=True):
            st.markdown(f"#### {game_index}. {game['Mandante']} x {game['Visitante']} — {game['Liga']}")
            st.caption(
                f"{pd.to_datetime(game['Data']).strftime('%d/%m/%Y')} às {game['Hora']} | "
                f"Casa de apostas: {game['Casa de apostas']}"
            )
            render_game_form_context(dict(form_contexts.get(input_id, {}) or {}))
            css_class = "filter-approved" if approved else "filter-rejected"
            filter_title = "APROVADO NO FILTRO DE 2018" if approved else "REPROVADO NO FILTRO DE 2018 — FORA DO UNIVERSO OPERACIONAL"
            st.markdown(
                f'<div class="{css_class}"><b>{filter_title}</b><br>{game_filter.get("Filter2018Summary", "Resultado indisponível.")}</div>',
                unsafe_allow_html=True,
            )
            checklist = pd.DataFrame([
                {"Regra": "1 — posição e pontos do visitante", "Resultado": "Aprovada" if game_filter.get("Filter2018Rule1Pass") else "Reprovada", "Detalhe": game_filter.get("Filter2018Rule1Detail", "")},
                {"Regra": "2 — último confronto direto", "Resultado": "Aprovada" if game_filter.get("Filter2018Rule2Pass") else "Reprovada", "Detalhe": game_filter.get("Filter2018Rule2Detail", "")},
                {"Regra": "3 — mandante marcou em 4 das últimas 5", "Resultado": "Aprovada" if game_filter.get("Filter2018Rule3Pass") else "Reprovada", "Detalhe": game_filter.get("Filter2018Rule3Detail", "")},
                {"Regra": "4 — visitante marcou em 4 das últimas 5", "Resultado": "Aprovada" if game_filter.get("Filter2018Rule4Pass") else "Reprovada", "Detalhe": game_filter.get("Filter2018Rule4Detail", "")},
            ])
            st.dataframe(checklist, hide_index=True, use_container_width=True)

            if not approved:
                st.warning(
                    "O jogo morre operacionalmente neste ponto: não pode aparecer nas apostas simples nem na sugestão de múltipla. "
                    "Os cálculos abaixo continuam salvos exclusivamente para formar a base de dados."
                )
                with st.expander("Ver probabilidades armazenadas para auditoria", expanded=False):
                    st.dataframe(
                        evaluation_table(game_evaluations.sort_values(
                            ["ConservativeProbability", "ConservativeExpectedValue"], ascending=[False, False]
                        )),
                        hide_index=True, use_container_width=True,
                    )
                continue

            st.success("Evento apto. A análise posterior é exclusivamente estatística e financeira.")
            if game_reading.empty:
                st.error("A partida foi aprovada, mas não produziu leitura estatística. Consulte o diagnóstico.")
                continue
            row = game_reading.iloc[0]
            render_expected_goals(
                row,
                home=str(game["Mandante"]),
                away=str(game["Visitante"]),
            )
            status = str(row["Status"])
            headline = (
                f"{status}: {row['Selection']} | cotação {float(row['Odd']):.2f} | "
                f"probabilidade final {pct(row['ConservativeProbability'])}"
            )
            if status == "OPERAR":
                st.success(headline)
            else:
                st.info(headline)

            fair_odd = _fair_odd_from_probability(row["ConservativeProbability"])
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Probabilidade final", pct(row["ConservativeProbability"]))
            p2.metric("Cotação justa", f"{fair_odd:.2f}")
            p3.metric("Cotação atual", f"{float(row['Odd']):.2f}")
            p4.metric("Valor esperado", pct(row["ConservativeExpectedValue"]))
            o1, o2 = st.columns(2)
            o1.metric("Cotação mínima para operar", f"{float(row['RequiredOddForOperation']):.2f}")
            o2.metric("Decisão financeira", status)
            st.caption("Cotação justa = 1 ÷ probabilidade final. Quanto maior a cotação atual em relação à justa, melhor o preço.")
            st.write(f"**Motivo:** {row['Reason']}")

            ordered_markets = game_evaluations.sort_values(
                ["ConservativeProbability", "ConservativeExpectedValue"], ascending=[False, False]
            )
            with st.expander("Ver todos os mercados avaliados", expanded=False):
                st.dataframe(
                    evaluation_table(ordered_markets),
                    hide_index=True, use_container_width=True,
                    column_config={
                        "Probabilidade final": st.column_config.NumberColumn(format="%.1f%%"),
                        "Valor esperado final": st.column_config.NumberColumn(format="%.1f%%"),
                        "Cotação atual": st.column_config.NumberColumn(format="%.2f"),
                        "Cotação justa": st.column_config.NumberColumn(format="%.2f"),
                        "Cotação mínima para operar": st.column_config.NumberColumn(format="%.2f"),
                    },
                )
            with st.expander("Ver cálculos técnicos detalhados", expanded=False):
                st.dataframe(
                    evaluation_table(ordered_markets, technical=True),
                    hide_index=True, use_container_width=True,
                )

    st.markdown("### Auditoria completa")
    tab_summary, tab_technical, tab_errors = st.tabs([
        "Resumo dos mercados", "Cálculos técnicos", "Diagnóstico técnico"
    ])
    ordered_audit = evaluations.sort_values(
        ["InputID", "Filter2018Approved", "ConservativeProbability"],
        ascending=[True, False, False],
    )
    with tab_summary:
        st.dataframe(
            evaluation_table(ordered_audit),
            hide_index=True, use_container_width=True,
        )
    with tab_technical:
        st.dataframe(
            evaluation_table(ordered_audit, technical=True),
            hide_index=True, use_container_width=True,
        )
    with tab_errors:
        st.dataframe(diagnostics, hide_index=True, use_container_width=True)

    st.markdown("### Análise para IA")
    if not ai_summary:
        ai_summary = build_ai_summary(games_frame(), readings, evaluations, diagnostics, matches)
    st.caption(
        "O texto está disponível diretamente na tela. Use o ícone de copiar no canto do bloco; "
        "não é necessário baixar arquivo."
    )
    st.code(ai_summary, language=None, wrap_lines=True)
    st.download_button(
        "BAIXAR ANÁLISE PARA IA — OPCIONAL",
        ai_summary.encode("utf-8"),
        "analise_tex_statistics_para_ia.txt",
        "text/plain",
        use_container_width=True,
    )

    st.subheader("4. Salvar cotações e probabilidades")
    st.caption("A análise já tenta salvar automaticamente. Use este botão apenas para repetir ou confirmar a gravação.")
    if st.button("REPETIR SALVAMENTO NA PLANILHA", type="primary", use_container_width=True):
        if google_configurado(st.secrets):
            try:
                catalog_records = make_catalog_records(evaluations, bankroll)
                analysis_records = make_analysis_records(evaluations, unit_percent / 100.0)
                # Grava diretamente, sem reler abas inteiras. A releitura anterior podia
                # estourar a quota do Google e impedir qualquer salvamento. A deduplicação
                # da sessão usa os IDs determinísticos no cache do módulo de armazenamento.
                saved_odds = salvar_cotacoes(st.secrets, catalog_records)
                saved_analysis = salvar_analises(st.secrets, analysis_records)
                st.session_state.pop("tex_analysis_autosave_error", None)
                st.session_state.pop("tex_analysis_autosave_error_details", None)
                st.success(
                    f"Gravação concluída: {saved_odds} novo(s) registro(s) de cotações e "
                    f"{saved_analysis} novo(s) registro(s) de probabilidades. Duplicidades foram ignoradas."
                )
            except Exception as exc:
                st.error(f"Não foi possível gravar na planilha: {exc}")
        else:
            st.error("A Planilha Google não está conectada nos Secrets deste aplicativo.")

    export1, export2 = st.columns(2)
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
