from __future__ import annotations

from datetime import date, datetime
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
from tex_v25_core import CFG, LEAGUES, build_current_state, normalize_zip
from tex_v25_storage import (
    COLUNAS_ANALISES,
    COLUNAS_COTACOES,
    google_configurado,
    salvar_analises,
    salvar_cotacoes,
    url_planilha_configurada,
)
from tex_v26_operacional import (
    OP_CFG,
    VERSION,
    analyze_batch,
    empty_batch,
    operational_columns,
)

ROOT = Path(__file__).resolve().parent
DATA_ZIP = ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip"
ZONE_METRICS = ROOT / "output" / "v25_zone_season_metrics.csv"
FUSO = ZoneInfo("America/Sao_Paulo")

st.set_page_config(page_title=VERSION, page_icon="📊", layout="wide", initial_sidebar_state="expanded")


def now_br() -> datetime:
    return datetime.now(FUSO)


def style() -> None:
    st.markdown(
        """
        <style>
        .block-container{max-width:1500px;padding-top:1rem;padding-bottom:4rem}
        [data-testid="stMetric"]{border:1px solid rgba(120,120,120,.22);border-radius:14px;padding:.7rem}
        [data-testid="stDataFrame"]{border:1px solid rgba(120,120,120,.22);border-radius:12px;overflow:hidden}
        .tex-head{padding:1rem 1.2rem;border-radius:18px;background:linear-gradient(120deg,#111827,#263b5e);color:white;margin-bottom:1rem}
        .tex-head h1{margin:0;font-size:2rem}.tex-head p{margin:.35rem 0 0;color:#dbeafe}
        .operar{padding:.9rem 1rem;border-radius:12px;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.35)}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="tex-head"><h1>{VERSION}</h1><p>Carteira semanal • uma seleção por jogo • unidade fixa • regra temporal congelada</p></div>',
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner="Carregando as 24 ligas do Football-Data...")
def load_matches():
    errors: list[str] = []

    if _atualizacao is not None:
        direct_loader = getattr(_atualizacao, "carregar_base_football_data", None)
        if callable(direct_loader):
            try:
                matches, report = direct_loader(date.today())
                return matches, report, 0, "Football-Data.co.uk — consulta direta, sem ZIP"
            except Exception as exc:
                errors.append(f"consulta direta: {exc}")

        legacy_loader = getattr(_atualizacao, "carregar_base_com_atualizacao", None)
        if callable(legacy_loader):
            try:
                matches, report, new_count = legacy_loader(DATA_ZIP, date.today())
                return matches, report, new_count, "Football-Data.co.uk + histórico local"
            except Exception as exc:
                errors.append(f"atualizador compatível: {exc}")
    else:
        errors.append("módulo tex_v25_atualizacao indisponível")

    try:
        matches = normalize_zip(DATA_ZIP, include_incomplete_annual_2026=True)
        detail = " | ".join(errors) if errors else "sem detalhes"
        return matches, [], 0, f"Histórico local de contingência ({detail})"
    except Exception as local_exc:
        detail = " | ".join(errors) if errors else "sem detalhes"
        raise RuntimeError(
            "Não foi possível carregar nem o Football-Data direto nem a base local. "
            f"Atualização: {detail}. Base local: {local_exc}"
        ) from local_exc


@st.cache_data(show_spinner=False)
def load_zone_metrics() -> pd.DataFrame:
    return pd.read_csv(ZONE_METRICS)


def clean_batch(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    keys = ["Data", "Liga", "Mandante", "Visitante"]
    for key in keys:
        if key not in frame.columns:
            frame[key] = ""
    keep = frame[keys].fillna("").astype(str).apply(lambda column: column.str.strip()).ne("").any(axis=1)
    return frame.loc[keep].reset_index(drop=True)


def format_portfolio(frame: pd.DataFrame) -> pd.DataFrame:
    output = operational_columns(frame)
    if output.empty:
        return output
    output["DataParsed"] = pd.to_datetime(output["DateParsed"]).dt.strftime("%d/%m/%Y")
    return output.rename(columns={
        "Decision": "Decisão", "WeekID": "Semana", "DateParsed": "Data", "League": "Liga",
        "Home": "Mandante", "Away": "Visitante", "MarketName": "Mercado", "Selection": "Seleção",
        "ExecutableOdd": "Cotação", "MarketProbability": "Prob. mercado", "SportsProbability": "Prob. modelo",
        "HistoricalHitRate": "Acerto histórico", "HistoricalROI": "ROI histórico",
        "HistoricalBets": "Amostra histórica", "Stake": "Entrada", "WeeklyRank": "Posição semanal",
        "Reason": "Motivo",
    })


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
            odd = pd.to_numeric(str(row.get(odd_column, "")).replace(",", "."), errors="coerce")
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
                "Mercado": market,
                "Seleção": selection_fn(row),
                "Cotação": float(odd),
                "Grupo do mercado": group,
                "Probabilidade implícita bruta %": 100.0 / float(odd),
                "Banca no momento": bankroll,
                "Perfil": VERSION,
                "Origem": "Painel semanal",
                "Observação": "Lote operacional salvo por acréscimo.",
            })
            records.append(record)
    return records


def analysis_records(batch_id: str, portfolio: pd.DataFrame, unit_fraction: float) -> list[dict]:
    now = now_br().strftime("%d/%m/%Y %H:%M:%S")
    records: list[dict] = []
    for index, row in portfolio.iterrows():
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
            "Origem": "Painel semanal",
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
            "Configuração JSON": json.dumps({"unit_fraction": unit_fraction, "weekly_top_n": OP_CFG.weekly_top_n}, ensure_ascii=False),
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
matches, update_report, new_count, data_source = load_matches()
zone_metrics = load_zone_metrics()

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
    st.caption(f"Fonte: {data_source}")
    st.caption(f"Partidas históricas carregadas: {len(matches):,}".replace(",", "."))
    if google_configurado(st.secrets):
        st.success("Planilha Google conectada")
        st.link_button("Abrir planilha", url_planilha_configurada(st.secrets), use_container_width=True)
    else:
        st.info("A planilha Google será habilitada quando os segredos existentes forem reconhecidos.")

panel_tab, audit_tab = st.tabs(["PAINEL SEMANAL", "AUDITORIA E EXPORTAÇÃO"])

with panel_tab:
    st.subheader("Jogos e cotações da semana")
    st.write("Insira todas as partidas disponíveis. A carteira é formada no conjunto, não jogo por jogo.")

    template = empty_batch(1)
    template.at[0, "Data"] = now_br().strftime("%d/%m/%Y")
    template.at[0, "Liga"] = "Brasileirão Série A"
    template.at[0, "Mandante"] = "Mandante"
    template.at[0, "Visitante"] = "Visitante"
    template.at[0, "Casa de apostas"] = "Pixbet"
    template.at[0, "Cotação mandante"] = 2.10
    template.at[0, "Cotação empate"] = 3.40
    template.at[0, "Cotação visitante"] = 3.50
    template.at[0, "Cotação mais de 2,5"] = 1.90
    template.at[0, "Cotação menos de 2,5"] = 1.90
    st.download_button(
        "BAIXAR MODELO CSV",
        template.to_csv(index=False).encode("utf-8-sig"),
        "modelo_painel_semanal_v26.csv",
        "text/csv",
    )

    uploaded = st.file_uploader("Importar CSV preenchido", type=["csv"], key="batch_csv")
    if "batch_editor_v26" not in st.session_state:
        st.session_state.batch_editor_v26 = empty_batch(12)
    if uploaded is not None:
        try:
            imported = pd.read_csv(uploaded, sep=None, engine="python")
            st.session_state.batch_editor_v26 = imported
        except Exception as exc:
            st.error(f"Não foi possível ler o CSV: {exc}")

    edited = st.data_editor(
        st.session_state.batch_editor_v26,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="editor_v26",
        column_config={
            "Liga": st.column_config.SelectboxColumn("Liga", options=list(LEAGUES.values())),
            "Cotação mandante": st.column_config.NumberColumn(format="%.2f", min_value=1.01),
            "Cotação empate": st.column_config.NumberColumn(format="%.2f", min_value=1.01),
            "Cotação visitante": st.column_config.NumberColumn(format="%.2f", min_value=1.01),
            "Cotação mais de 2,5": st.column_config.NumberColumn(format="%.2f", min_value=1.01),
            "Cotação menos de 2,5": st.column_config.NumberColumn(format="%.2f", min_value=1.01),
        },
    )

    analyze = st.button("ANALISAR E MONTAR CARTEIRA", type="primary", use_container_width=True)
    if analyze:
        batch = clean_batch(edited)
        if batch.empty:
            st.error("Inclua pelo menos uma partida completa.")
        else:
            with st.spinner("Calculando as probabilidades pré-jogo e montando a carteira semanal..."):
                portfolio, diagnostics = analyze_batch(
                    batch, matches, zone_metrics, bankroll=float(bankroll),
                    unit_fraction=unit_fraction, weekly_top_n=int(weekly_limit), cfg=CFG,
                )
            st.session_state.result_v26 = portfolio
            st.session_state.diag_v26 = diagnostics
            st.session_state.input_v26 = batch
            st.session_state.batch_id_v26 = uuid4().hex[:12]

    portfolio = st.session_state.get("result_v26", pd.DataFrame())
    diagnostics = st.session_state.get("diag_v26", pd.DataFrame())
    if not diagnostics.empty:
        errors = diagnostics[diagnostics["Situação"].eq("ERRO")]
        if not errors.empty:
            st.error(f"{len(errors)} linha(s) não puderam ser analisadas.")
            st.dataframe(errors, use_container_width=True, hide_index=True)

    if not portfolio.empty:
        operating = portfolio[portfolio["Decision"].eq("OPERAR")].copy()
        reserves = portfolio[portfolio["Decision"].eq("RESERVA")].copy()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entradas operacionais", len(operating))
        c2.metric("Reservas aprovadas", len(reserves))
        c3.metric("Exposição", f"R$ {operating['Stake'].sum():.2f}")
        c4.metric("Ligas com entrada", operating["League"].nunique() if not operating.empty else 0)

        if operating.empty:
            st.warning("O lote não produziu entrada operacional pela regra congelada. Amplie a cobertura para as 24 ligas; não force mercados descartados.")
        else:
            st.markdown('<div class="operar"><strong>CARTEIRA OPERACIONAL</strong><br>Somente estas linhas recebem entrada.</div>', unsafe_allow_html=True)
            display = format_portfolio(operating)
            st.dataframe(
                display.style.format({
                    "Cotação": "{:.2f}", "Prob. mercado": "{:.2%}", "Prob. modelo": "{:.2%}",
                    "Acerto histórico": "{:.2%}", "ROI histórico": "{:.2%}", "Entrada": "R$ {:.2f}",
                }, na_rep="—"),
                use_container_width=True,
                hide_index=True,
            )
        if not reserves.empty:
            with st.expander(f"Reservas aprovadas fora do limite semanal ({len(reserves)})"):
                st.dataframe(format_portfolio(reserves), use_container_width=True, hide_index=True)
    elif analyze:
        st.warning("Nenhuma faixa aprovada foi encontrada no lote.")

with audit_tab:
    portfolio = st.session_state.get("result_v26", pd.DataFrame())
    batch = st.session_state.get("input_v26", pd.DataFrame())
    diagnostics = st.session_state.get("diag_v26", pd.DataFrame())
    if portfolio.empty and diagnostics.empty:
        st.info("Execute uma análise no Painel Semanal para liberar a auditoria e as exportações.")
    else:
        st.subheader("Arquivos auditáveis")
        if not portfolio.empty:
            export = format_portfolio(portfolio)
            st.download_button(
                "BAIXAR CARTEIRA E RESERVAS",
                export.to_csv(index=False).encode("utf-8-sig"),
                "carteira_operacional_v26.csv",
                "text/csv",
                use_container_width=True,
            )
        if not diagnostics.empty:
            st.download_button(
                "BAIXAR DIAGNÓSTICO DO LOTE",
                diagnostics.to_csv(index=False).encode("utf-8-sig"),
                "diagnostico_lote_v26.csv",
                "text/csv",
                use_container_width=True,
            )
        st.subheader("Gravar na planilha histórica")
        st.caption("A gravação é por acréscimo e não apaga as linhas existentes.")
        if google_configurado(st.secrets) and not batch.empty:
            if st.button("SALVAR LOTE E DECISÕES NO GOOGLE", use_container_width=True):
                batch_id = st.session_state.get("batch_id_v26", uuid4().hex[:12])
                try:
                    n_quotes = salvar_cotacoes(st.secrets, catalog_records(batch_id, batch, float(bankroll)))
                    n_analysis = salvar_analises(st.secrets, analysis_records(batch_id, portfolio, unit_fraction)) if not portfolio.empty else 0
                    st.success(f"Salvo: {n_quotes} cotações e {n_analysis} decisões, sem substituir o histórico.")
                except Exception as exc:
                    st.error(f"Falha ao salvar: {exc}")
        else:
            st.info("A conexão Google não está disponível nesta execução.")

st.caption("A ferramenta calcula e organiza decisões estatísticas; não garante lucro nem transforma banca em renda fixa.")
