from __future__ import annotations

from collections import defaultdict
import json
from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from tex_v25_atualizacao import carregar_base_football_data
from tex_v25_core import (
    ANNUAL_CODES,
    CFG,
    LEAGUES,
    VERSION,
    build_current_state,
    evaluate_live_market,
    no_vig_probabilities,
    sports_probabilities_for_match,
)
from tex_v25_storage import (
    ABA_ANALISES,
    ABA_COTACOES,
    PLANILHA_ANTIGA_URL,
    agora_brasilia,
    carregar_analises,
    carregar_cotacoes,
    confirmar_resultado,
    configuracao_google,
    google_configurado,
    salvar_analises,
    salvar_cotacoes,
    url_planilha_configurada,
)

ROOT = Path(__file__).resolve().parent
ZONE_METRICS = ROOT / "output" / "v25_zone_season_metrics.csv"
REGISTRY = ROOT / "output" / "v25_registry.json"

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")

st.set_page_config(
    page_title="Tex Statistics v.25",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def agora_em_brasilia() -> datetime:
    return datetime.now(FUSO_BRASILIA)


def aplicar_identidade_visual() -> None:
    st.markdown(
        """
        <style>
        :root {
            --tex-fundo: #f5f7fb;
            --tex-cartao: rgba(255,255,255,.92);
            --tex-borda: rgba(15,23,42,.10);
            --tex-texto: #172033;
            --tex-suave: #64748b;
            --tex-destaque: #ef4444;
            --tex-destaque-2: #f97316;
            --tex-sombra: 0 14px 36px rgba(15,23,42,.08);
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --tex-fundo: #090f1b;
                --tex-cartao: rgba(17,24,39,.92);
                --tex-borda: rgba(148,163,184,.18);
                --tex-texto: #f1f5f9;
                --tex-suave: #94a3b8;
                --tex-destaque: #fb7185;
                --tex-destaque-2: #fb923c;
                --tex-sombra: 0 16px 44px rgba(0,0,0,.35);
            }
        }
        html { color-scheme: light dark; }
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 10% 0%, rgba(239,68,68,.08), transparent 28rem),
                radial-gradient(circle at 95% 10%, rgba(249,115,22,.07), transparent 25rem),
                var(--tex-fundo);
        }
        [data-testid="stHeader"] { background: transparent; }
        .block-container {
            max-width: 1440px;
            padding-top: 1.25rem;
            padding-bottom: 5rem;
        }
        .tex-cabecalho {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 1.15rem 1.3rem;
            margin-bottom: 1rem;
            border: 1px solid var(--tex-borda);
            border-radius: 22px;
            background: linear-gradient(135deg, var(--tex-cartao), rgba(239,68,68,.05));
            box-shadow: var(--tex-sombra);
        }
        .tex-marca { display:flex; align-items:center; gap:.9rem; }
        .tex-icone {
            display:grid; place-items:center; width:3rem; height:3rem;
            border-radius:15px; color:white; font-size:1.35rem; font-weight:800;
            background: linear-gradient(135deg, var(--tex-destaque), var(--tex-destaque-2));
            box-shadow:0 10px 24px rgba(239,68,68,.22);
        }
        .tex-titulo { color:var(--tex-texto); font-size:clamp(1.55rem,3.3vw,2.45rem); font-weight:850; line-height:1.05; }
        .tex-hora { color:var(--tex-suave); text-align:right; font-size:.86rem; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--tex-borda) !important;
            border-radius: 18px !important;
            background: var(--tex-cartao);
            box-shadow: 0 8px 24px rgba(15,23,42,.045);
        }
        [data-testid="stMetric"] {
            border:1px solid var(--tex-borda);
            border-radius:16px;
            background:var(--tex-cartao);
            padding:.75rem .85rem;
        }
        [data-baseweb="tab-list"] { gap:.35rem; overflow-x:auto; scrollbar-width:none; }
        [data-baseweb="tab"] { white-space:nowrap; border-radius:999px; padding:.55rem .85rem; }
        [data-baseweb="tab"][aria-selected="true"] { background:rgba(239,68,68,.10); }
        .stButton > button, .stDownloadButton > button {
            border-radius:12px; min-height:2.8rem; font-weight:700;
        }
        div[data-baseweb="input"] { border-radius:12px; }
        [data-testid="stDataFrame"] { border:1px solid var(--tex-borda); border-radius:14px; overflow:hidden; }
        @media (max-width: 768px) {
            .block-container { padding:.65rem .65rem 4.5rem; }
            .tex-cabecalho { padding:.9rem; border-radius:17px; align-items:flex-start; }
            .tex-icone { width:2.55rem; height:2.55rem; border-radius:13px; }
            .tex-hora { display:none; }
            [data-testid="stHorizontalBlock"] { flex-wrap:wrap; gap:.55rem; }
            [data-testid="column"] { min-width:100% !important; flex:1 1 100% !important; }
            .stButton > button, .stDownloadButton > button { width:100%; min-height:3rem; }
            [data-baseweb="tab"] { font-size:.82rem; }
            h1, h2, h3 { line-height:1.18 !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    momento = agora_em_brasilia()
    st.markdown(
        f"""
        <div class="tex-cabecalho">
          <div class="tex-marca">
            <div class="tex-icone">T25</div>
            <div class="tex-titulo">Tex Statistics v.25</div>
          </div>
          <div class="tex-hora">Horário de Brasília<br><strong>{momento.strftime('%d/%m/%Y %H:%M')}</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ativar_digitacao_rapida_das_odds() -> None:
    components.html(
        """
        <script>
        const documento = window.parent.document;
        documento.documentElement.lang = 'pt-BR';
        const rotulos = [
          'Vitória do mandante','Empate','Vitória do visitante',
          'Mais de 2,5 gols','Menos de 2,5 gols',
          'Ambas as equipes marcam — Sim','Ambas as equipes marcam — Não'
        ];
        function preparar() {
          documento.querySelectorAll('input').forEach((campo) => {
            const nome = campo.getAttribute('aria-label') || '';
            if (!rotulos.some(r => nome.includes(r))) return;
            campo.setAttribute('inputmode', 'decimal');
            if (campo.dataset.texPreparado === 'sim') return;
            campo.dataset.texPreparado = 'sim';
            const selecionar = () => setTimeout(() => campo.select(), 0);
            campo.addEventListener('focus', selecionar);
            campo.addEventListener('pointerup', (evento) => { evento.preventDefault(); selecionar(); });
          });
        }
        preparar();
        const observador = new MutationObserver(preparar);
        observador.observe(documento.body, {childList:true, subtree:true});
        setTimeout(() => observador.disconnect(), 120000);
        </script>
        """,
        height=0,
    )


aplicar_identidade_visual()


@st.cache_data(ttl=43_200, show_spinner="Baixando os dados das 24 ligas diretamente do Football-Data...")
def carregar_base_atualizada():
    # Não existe mais leitura, mesclagem ou fallback para ZIP.
    return carregar_base_football_data(date.today())


@st.cache_resource(ttl=43_200, show_spinner="Construindo o estado estatístico...")
def carregar_motor():
    partidas_carregadas, relatorio_atualizacao = carregar_base_atualizada()
    # As zonas são o artefato de calibração da V25. Os jogos usados na análise
    # operacional são baixados diretamente do Football-Data em cada ciclo de cache.
    metricas = pd.read_csv(ZONE_METRICS)
    equipes: dict[str, list[str]] = {}
    for codigo_liga in LEAGUES:
        equipes[codigo_liga] = sorted(
            {item["Home"] for item in partidas_carregadas if item["Code"] == codigo_liga}
            | {item["Away"] for item in partidas_carregadas if item["Code"] == codigo_liga}
        )
    return partidas_carregadas, metricas, equipes, relatorio_atualizacao


try:
    partidas, metricas_zonas, equipes_por_codigo, relatorio_atualizacao = carregar_motor()
except Exception as erro:
    st.error(f"Não foi possível carregar os dados diretamente do Football-Data: {erro}")
    st.stop()
liga_para_codigo = {nome: codigo for codigo, nome in LEAGUES.items()}

if "ultima_analise_v25" not in st.session_state:
    st.session_state.ultima_analise_v25 = None
if "historico_sessao_cotacoes" not in st.session_state:
    st.session_state.historico_sessao_cotacoes = []
if "historico_sessao_analises" not in st.session_state:
    st.session_state.historico_sessao_analises = []
if "historico_google_cotacoes" not in st.session_state:
    st.session_state.historico_google_cotacoes = []
if "historico_google_analises" not in st.session_state:
    st.session_state.historico_google_analises = []


@st.cache_resource(show_spinner=False)
def estado_antes_da_data(data_iso: str):
    limite = date.fromisoformat(data_iso)
    anteriores = [item for item in partidas if item["DateParsed"] < limite]
    return build_current_state(anteriores, CFG)


def temporada_padrao(codigo: str, referencia: date | None = None) -> int:
    referencia = referencia or date.today()
    if codigo in ANNUAL_CODES:
        return referencia.year
    return referencia.year if referencia.month >= 7 else referencia.year - 1


def nome_selecao(codigo: str, mandante: str, visitante: str) -> str:
    return {
        "H": f"Vitória do {mandante}",
        "D": "Empate",
        "A": f"Vitória do {visitante}",
        "O25": "Mais de 2,5 gols",
        "U25": "Menos de 2,5 gols",
    }.get(codigo, codigo)


def nome_mercado(codigo: str) -> str:
    return {
        "1X2": "Resultado da partida",
        "OU": "Total de gols — 2,5",
    }.get(codigo, codigo)


def entrada_odd(rotulo: str, chave: str, valor: float | None = None) -> float:
    inicial = "" if valor in (None, 0, 0.0) else f"{float(valor):.2f}".replace(".", ",")
    texto = st.text_input(
        rotulo,
        value=inicial,
        placeholder="Toque e digite a cotação",
        key=chave,
        help="Ao tocar no campo, o valor anterior é selecionado. Basta digitar o novo número; não é necessário apagar.",
    )
    limpo = str(texto or "").strip().replace("R$", "").replace(" ", "").replace(",", ".")
    if not limpo:
        return 0.0
    try:
        numero = float(limpo)
        return numero if 0.0 <= numero <= 100.0 else 0.0
    except ValueError:
        return 0.0


def margem_bruta(odds: list[float]) -> float | None:
    if not odds or any(not odd or float(odd) <= 1.0 for odd in odds):
        return None
    return sum(1.0 / float(odd) for odd in odds) - 1.0


def ultima_data_da_liga(codigo: str) -> date | None:
    datas = [item["DateParsed"] for item in partidas if item["Code"] == codigo]
    return max(datas) if datas else None


def quantidade_partidas_da_liga(codigo: str) -> int:
    return sum(1 for item in partidas if item["Code"] == codigo)


def classificacao_antes_do_jogo(codigo: str, temporada: int, data_analise: date) -> pd.DataFrame:
    tabela: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "Jogos": 0,
            "Vitórias": 0,
            "Empates": 0,
            "Derrotas": 0,
            "Gols marcados": 0,
            "Gols sofridos": 0,
            "Pontos": 0,
        }
    )
    anteriores = [
        item
        for item in partidas
        if item["Code"] == codigo
        and int(item["Season"]) == int(temporada)
        and item["DateParsed"] < data_analise
    ]
    for item in anteriores:
        mandante, visitante = item["Home"], item["Away"]
        gols_mandante, gols_visitante = int(item["HG"]), int(item["AG"])
        casa, fora = tabela[mandante], tabela[visitante]
        casa["Jogos"] += 1
        fora["Jogos"] += 1
        casa["Gols marcados"] += gols_mandante
        casa["Gols sofridos"] += gols_visitante
        fora["Gols marcados"] += gols_visitante
        fora["Gols sofridos"] += gols_mandante
        if gols_mandante > gols_visitante:
            casa["Vitórias"] += 1
            fora["Derrotas"] += 1
            casa["Pontos"] += 3
        elif gols_visitante > gols_mandante:
            fora["Vitórias"] += 1
            casa["Derrotas"] += 1
            fora["Pontos"] += 3
        else:
            casa["Empates"] += 1
            fora["Empates"] += 1
            casa["Pontos"] += 1
            fora["Pontos"] += 1

    linhas = []
    for equipe, valores in tabela.items():
        jogos = int(valores["Jogos"])
        if jogos <= 0:
            continue
        linhas.append(
            {
                "Equipe": equipe,
                **valores,
                "Saldo": valores["Gols marcados"] - valores["Gols sofridos"],
                "Pontos por jogo": valores["Pontos"] / jogos,
                "Gols por jogo": valores["Gols marcados"] / jogos,
                "Gols sofridos por jogo": valores["Gols sofridos"] / jogos,
            }
        )
    if not linhas:
        return pd.DataFrame()
    quadro = pd.DataFrame(linhas).sort_values(
        ["Pontos", "Vitórias", "Saldo", "Gols marcados"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    quadro.insert(0, "Posição", np.arange(1, len(quadro) + 1))
    return quadro


def contexto_da_classificacao(
    codigo: str,
    temporada: int,
    data_analise: date,
    mandante: str,
    visitante: str,
) -> dict:
    quadro = classificacao_antes_do_jogo(codigo, temporada, data_analise)
    vazio = {
        "Disponível": False,
        "Quadro": quadro,
        "Posição do mandante": "",
        "Posição do visitante": "",
        "Pontos do mandante": "",
        "Pontos do visitante": "",
        "Pontos por jogo do mandante": "",
        "Pontos por jogo do visitante": "",
        "Gols por jogo do mandante": "",
        "Gols por jogo do visitante": "",
        "Gols sofridos por jogo do mandante": "",
        "Gols sofridos por jogo do visitante": "",
    }
    if quadro.empty:
        return vazio
    casa = quadro[quadro["Equipe"] == mandante]
    fora = quadro[quadro["Equipe"] == visitante]
    if casa.empty or fora.empty:
        return vazio
    casa, fora = casa.iloc[0], fora.iloc[0]
    return {
        "Disponível": True,
        "Quadro": quadro,
        "Posição do mandante": int(casa["Posição"]),
        "Posição do visitante": int(fora["Posição"]),
        "Pontos do mandante": int(casa["Pontos"]),
        "Pontos do visitante": int(fora["Pontos"]),
        "Pontos por jogo do mandante": float(casa["Pontos por jogo"]),
        "Pontos por jogo do visitante": float(fora["Pontos por jogo"]),
        "Gols por jogo do mandante": float(casa["Gols por jogo"]),
        "Gols por jogo do visitante": float(fora["Gols por jogo"]),
        "Gols sofridos por jogo do mandante": float(casa["Gols sofridos por jogo"]),
        "Gols sofridos por jogo do visitante": float(fora["Gols sofridos por jogo"]),
    }


def mostrar_classificacao(contexto: dict, mandante: str, visitante: str) -> None:
    st.markdown("### Classificação antes da partida")
    if not contexto["Disponível"]:
        st.info("Ainda não há jogos suficientes nesta temporada para reconstruir a classificação.")
        return
    coluna1, coluna2 = st.columns(2)
    coluna1.metric(
        mandante,
        f"{contexto['Posição do mandante']}º lugar",
        f"{contexto['Pontos do mandante']} pontos | {contexto['Pontos por jogo do mandante']:.2f} por jogo",
    )
    coluna2.metric(
        visitante,
        f"{contexto['Posição do visitante']}º lugar",
        f"{contexto['Pontos do visitante']} pontos | {contexto['Pontos por jogo do visitante']:.2f} por jogo",
    )
    diferenca_posicao = abs(contexto["Posição do mandante"] - contexto["Posição do visitante"])
    diferenca_pontos = abs(
        contexto["Pontos por jogo do mandante"] - contexto["Pontos por jogo do visitante"]
    )
    if diferenca_posicao >= 5 or diferenca_pontos >= 0.45:
        superior = (
            mandante
            if contexto["Pontos por jogo do mandante"] > contexto["Pontos por jogo do visitante"]
            else visitante
        )
        st.warning(
            f"Diferença relevante: {diferenca_posicao} posições e {diferenca_pontos:.2f} ponto por jogo. "
            f"Equipe superior nesse recorte: {superior}."
        )
    with st.expander("Ver tabela completa"):
        st.dataframe(
            contexto["Quadro"].style.format(
                {
                    "Pontos por jogo": "{:.2f}",
                    "Gols por jogo": "{:.2f}",
                    "Gols sofridos por jogo": "{:.2f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )



def _formatar_percentual_historico(valor) -> str:
    try:
        if pd.isna(valor):
            return "indisponível"
        return f"{float(valor):.2%}"
    except Exception:
        return "indisponível"


def _motivo_falhas_validacao(linha: pd.Series) -> str:
    codigos = {item for item in str(linha.get("ValidationFailures") or "").split(",") if item}
    partes: list[str] = []
    amostra = int(linha.get("HistoricalEligibleBets") or 0)
    temporadas = int(linha.get("HistoricalEligibleSeasons") or 0)
    positivas = int(linha.get("HistoricalPositiveSeasons") or 0)
    acerto = linha.get("HistoricalHitRate")
    retorno = linha.get("HistoricalROI")
    retorno_recente = linha.get("HistoricalRecentROI")

    if "AMOSTRA_TOTAL_INSUFICIENTE" in codigos:
        partes.append(f"amostra elegível {amostra}/{CFG.min_zone_total_bets}")
    if "TEMPORADAS_OBSERVADAS_INSUFICIENTES" in codigos:
        partes.append(f"temporadas elegíveis {temporadas}/{CFG.min_positive_seasons}")
    if "TEMPORADAS_POSITIVAS_INSUFICIENTES" in codigos:
        partes.append(f"temporadas positivas {positivas}/{CFG.min_positive_seasons}")
    if "RETORNO_HISTORICO_INSUFICIENTE" in codigos:
        partes.append(f"retorno histórico {_formatar_percentual_historico(retorno)} (mínimo {CFG.min_zone_roi:.2%})")
    if "SEM_TEMPORADA_RECENTE_ELEGIVEL" in codigos:
        partes.append("sem amostra elegível na temporada anterior")
    if "RETORNO_RECENTE_INSUFICIENTE" in codigos:
        partes.append(f"retorno da temporada anterior {_formatar_percentual_historico(retorno_recente)} (mínimo {CFG.min_recent_season_roi:.2%})")
    if "ACERTO_HISTORICO_INSUFICIENTE" in codigos:
        partes.append(f"acerto histórico {_formatar_percentual_historico(acerto)} (mínimo {CFG.min_zone_hit_rate:.2%})")
    return "; ".join(partes)


def detalhar_situacao(linha: pd.Series) -> tuple[str, str]:
    valor = float(linha.get("ValorEsperadoEsportivo") or 0.0)
    odd = float(linha.get("ExecutableOdd") or 0.0)
    diferenca = float(linha.get("ProbabilityDifference") or 0.0)

    if str(linha.get("Status")) == "APROVADA":
        amostra = int(linha.get("HistoricalEligibleBets") or linha.get("HistoricalBets") or 0)
        return (
            "AUTORIZADA",
            f"A faixa cumpriu todos os critérios históricos da V25, com {amostra} observações elegíveis nas quatro temporadas anteriores.",
        )

    if valor >= 0.02 and odd > CFG.max_executable_odd:
        return (
            "SINAL COM VALOR — COTAÇÃO FORA DA FAIXA",
            f"Existe valor esportivo, mas a cotação {odd:.2f} supera o limite {CFG.max_executable_odd:.2f} testado pela V25.",
        )

    if valor >= 0.02 and not bool(linha.get("HistoricalMarketAvailable", False)):
        return (
            "SINAL COM VALOR — SEM DADOS HISTÓRICOS",
            "O cálculo esportivo encontrou valor, mas o mercado e o lado analisados não possuem observações históricas na janela de quatro temporadas usada pela validação da V25.",
        )

    if valor >= 0.02 and not bool(linha.get("HistoricalExactZoneObserved", False)):
        return (
            "SINAL COM VALOR — FAIXA SEM AMOSTRA",
            f"O mercado possui histórico, porém a faixa exata de probabilidade e diferença deste sinal não apareceu nas quatro temporadas anteriores (faixas {float(linha.get('MarketBand') or 0):.3f} e {float(linha.get('DifferenceBand') or 0):.3f}).",
        )

    if valor >= 0.02 and int(linha.get("HistoricalEligibleBets") or 0) <= 0:
        bruta = int(linha.get("HistoricalRawBets") or 0)
        temporadas = int(linha.get("HistoricalSeasonsObserved") or 0)
        return (
            "SINAL COM VALOR — AMOSTRA INSUFICIENTE",
            f"A faixa apareceu em {bruta} jogo(s), distribuído(s) por {temporadas} temporada(s), mas nenhuma temporada atingiu o mínimo de {CFG.min_zone_bets_per_season} observações exigido pela V25.",
        )

    if valor >= 0.02:
        falhas = _motivo_falhas_validacao(linha)
        detalhe = falhas or "a faixa não cumpriu todos os critérios históricos da V25"
        return (
            "SINAL COM VALOR — NÃO VALIDADO",
            f"O cálculo esportivo encontrou valor, porém a faixa não foi aprovada: {detalhe}.",
        )

    if abs(diferenca) >= 0.10:
        return (
            "DESCARTADA — DIVERGÊNCIA ALTA SEM VALOR",
            "A projeção esportiva diverge fortemente do mercado, mas a cotação informada ainda produz valor esperado negativo pelo próprio cálculo.",
        )
    return "DESCARTADA — SEM VALOR", "A probabilidade esportiva não supera a probabilidade mínima exigida pela cotação informada."

def preparar_resultado(resultado: pd.DataFrame) -> pd.DataFrame:
    preparado = resultado.copy()
    preparado["ProbabilidadeMinima"] = preparado["ExecutableOdd"].apply(
        lambda valor: 1.0 / float(valor) if valor and float(valor) > 1.0 else np.nan
    )
    preparado["ValorEsperadoEsportivo"] = preparado["SportsProbability"] * preparado["ExecutableOdd"] - 1.0
    detalhes = preparado.apply(detalhar_situacao, axis=1)
    preparado["SituacaoDetalhada"] = [item[0] for item in detalhes]
    preparado["Motivo"] = [item[1] for item in detalhes]
    return preparado


def mostrar_resultado(
    resultado: pd.DataFrame,
    mandante: str,
    visitante: str,
    valor_unidade: float = 0.0,
) -> None:
    autorizadas = resultado[resultado["SituacaoDetalhada"] == "AUTORIZADA"].copy()
    sinais = resultado[resultado["SituacaoDetalhada"].str.startswith("SINAL")].copy()

    if not autorizadas.empty:
        principal = autorizadas.sort_values(
            ["MarketProbability", "HistoricalHitRate"], ascending=False
        ).iloc[0]
        odd_principal = float(principal["ExecutableOdd"])
        st.success(
            f"🟢 ENTRADA AUTORIZADA: {nome_selecao(str(principal['Side']), mandante, visitante)} | "
            f"cotação informada {odd_principal:.2f}"
        )
        if valor_unidade > 0:
            financeiro1, financeiro2, financeiro3 = st.columns(3)
            financeiro1.metric("Valor da entrada", f"R$ {valor_unidade:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            financeiro2.metric("Retorno total possível", f"R$ {valor_unidade * odd_principal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            financeiro3.metric("Lucro possível", f"R$ {valor_unidade * (odd_principal - 1):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    elif not sinais.empty:
        descricoes = ", ".join(
            f"{nome_selecao(str(linha['Side']), mandante, visitante)} ({linha['SituacaoDetalhada']})"
            for _, linha in sinais.iterrows()
        )
        st.warning("🟡 NENHUMA ENTRADA AUTORIZADA. O motivo de cada sinal está identificado separadamente: " + descricoes)
    else:
        st.error("🔴 NENHUMA SELEÇÃO APRESENTOU VALOR SUFICIENTE NESTA PARTIDA")

    for _, linha in resultado.iterrows():
        situacao = str(linha["SituacaoDetalhada"])
        icone = "🟢" if situacao == "AUTORIZADA" else ("🟡" if situacao.startswith("SINAL") else "🔴")
        selecao = nome_selecao(str(linha["Side"]), mandante, visitante)
        abrir = situacao == "AUTORIZADA" or situacao.startswith("SINAL")
        with st.expander(f"{icone} {selecao} — {situacao}", expanded=abrir):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Probabilidade do mercado", f"{linha['MarketProbability']:.2%}")
            c2.metric("Probabilidade esportiva", f"{linha['SportsProbability']:.2%}")
            c3.metric("Probabilidade mínima exigida", f"{linha['ProbabilidadeMinima']:.2%}")
            c4.metric("Valor esperado esportivo", f"{linha['ValorEsperadoEsportivo']:.2%}")
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Cotação informada", f"{linha['ExecutableOdd']:.2f}")
            d2.metric("Diferença modelo–mercado", f"{linha['ProbabilityDifference']:.2%}")
            d3.metric("Amostra histórica elegível", int(linha.get("HistoricalEligibleBets") or linha.get("HistoricalBets") or 0))
            d4.metric(
                "Retorno histórico",
                "—" if pd.isna(linha.get("HistoricalROI")) else f"{linha['HistoricalROI']:.2%}",
            )
            st.caption(
                f"Faixa observada: {int(linha.get('HistoricalRawBets') or 0)} jogo(s) em "
                f"{int(linha.get('HistoricalSeasonsObserved') or 0)} temporada(s); "
                f"elegível: {int(linha.get('HistoricalEligibleBets') or 0)} jogo(s) em "
                f"{int(linha.get('HistoricalEligibleSeasons') or 0)} temporada(s)."
            )
            st.write(f"**Motivo:** {linha['Motivo']}")

    tabela = resultado.copy()
    tabela["Seleção"] = tabela["Side"].map(lambda item: nome_selecao(str(item), mandante, visitante))
    exibir = tabela[
        [
            "SituacaoDetalhada", "Seleção", "MarketProbability", "SportsProbability",
            "ProbabilidadeMinima", "ValorEsperadoEsportivo", "ExecutableOdd",
            "ProbabilityDifference", "HistoricalBets", "HistoricalHitRate",
            "HistoricalROI", "HistoricalEVAtCurrentPrice", "Motivo",
        ]
    ].rename(
        columns={
            "SituacaoDetalhada": "Situação",
            "MarketProbability": "Probabilidade do mercado",
            "SportsProbability": "Probabilidade esportiva",
            "ProbabilidadeMinima": "Probabilidade mínima exigida",
            "ValorEsperadoEsportivo": "Valor esperado esportivo",
            "ExecutableOdd": "Cotação informada",
            "ProbabilityDifference": "Diferença modelo–mercado",
            "HistoricalBets": "Amostra histórica",
            "HistoricalHitRate": "Acerto histórico",
            "HistoricalROI": "Retorno histórico",
            "HistoricalEVAtCurrentPrice": "Valor histórico no preço atual",
            "Motivo": "Motivo da decisão",
        }
    )
    exibir = exibir.replace({None: np.nan})
    st.dataframe(
        exibir.style.format(
            {
                "Probabilidade do mercado": "{:.2%}",
                "Probabilidade esportiva": "{:.2%}",
                "Probabilidade mínima exigida": "{:.2%}",
                "Valor esperado esportivo": "{:.2%}",
                "Cotação informada": "{:.2f}",
                "Diferença modelo–mercado": "{:.2%}",
                "Acerto histórico": "{:.2%}",
                "Retorno histórico": "{:.2%}",
                "Valor histórico no preço atual": "{:.2%}",
            },
            na_rep="—",
        ),
        use_container_width=True,
        hide_index=True,
    )


def _mercado_legado(codigo: str) -> str:
    return {
        "H": "Vitória Casa",
        "D": "Empate",
        "A": "Vitória Fora",
        "O25": "Mais de 2.5 gols",
        "U25": "Menos de 2.5 gols",
        "AMBAS_SIM": "Ambos marcam - Sim",
        "AMBAS_NAO": "Ambos marcam - Não",
    }.get(codigo, codigo)


def _grupo_mercado(codigo: str) -> str:
    if codigo in {"H", "D", "A"}:
        return "Resultado final 1X2"
    if codigo in {"O25", "U25"}:
        return "Total de gols 2.5"
    if codigo in {"AMBAS_SIM", "AMBAS_NAO"}:
        return "Ambas marcam"
    return "Outro"


def criar_linhas_cotacoes(
    identificador_coleta: str,
    nome_liga: str,
    temporada: int,
    data_partida: date,
    horario_partida: time | None,
    mandante: str,
    visitante: str,
    fonte: str,
    odds: dict[str, float],
    banca: float,
    contexto: dict,
) -> list[dict]:
    validas = {codigo: float(odd) for codigo, odd in odds.items() if odd and float(odd) > 1.0}
    grupos: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for codigo, odd in validas.items():
        grupos[_grupo_mercado(codigo)].append((codigo, odd))
    esperados = {"Resultado final 1X2": 3, "Total de gols 2.5": 2, "Ambas marcam": 2}
    metricas: dict[str, dict] = {}
    for grupo, itens in grupos.items():
        completo = len(itens) == esperados.get(grupo, 0)
        soma = sum(1.0 / odd for _, odd in itens)
        for codigo, odd in itens:
            metricas[codigo] = {
                "completo": completo,
                "bruta": 100.0 / odd,
                "margem": (soma - 1.0) * 100.0 if completo else "",
                "ajustada": ((1.0 / odd) / soma) * 100.0 if completo and soma > 0 else "",
            }
    momento = agora_brasilia()
    jogo = f"{mandante} x {visitante}"
    hora = horario_partida.strftime("%H:%M") if horario_partida else ""
    selecoes = {
        "H": mandante,
        "D": "Empate",
        "A": visitante,
        "O25": "Mais de 2.5 gols",
        "U25": "Menos de 2.5 gols",
        "AMBAS_SIM": "Sim",
        "AMBAS_NAO": "Não",
    }
    linhas = []
    for codigo, odd in validas.items():
        metrica = metricas[codigo]
        linhas.append({
            "ID Coleta": identificador_coleta,
            "Registrado em": momento,
            "Casa de apostas": fonte or "Não informada",
            "Liga": nome_liga,
            "Jogo": jogo,
            "Mandante": mandante,
            "Visitante": visitante,
            "Data do jogo": data_partida.strftime("%Y-%m-%d"),
            "Hora do jogo": hora,
            "Mercado": _mercado_legado(codigo),
            "Seleção": selecoes.get(codigo, codigo),
            "Cotação": odd,
            "Grupo do mercado": _grupo_mercado(codigo),
            "Mercado completo": "Sim" if metrica["completo"] else "Não",
            "Probabilidade implícita bruta %": metrica["bruta"],
            "Margem do mercado %": metrica["margem"],
            "Probabilidade ajustada sem margem %": metrica["ajustada"],
            "Banca no momento": banca,
            "Perfil": "Tex Statistics v.25",
            "Origem": "Digitação manual",
            "Observação": "Coleta salva por clique explícito; histórico somente de acréscimo.",
            "Temporada": temporada,
            "Posição do mandante": contexto.get("Posição do mandante", ""),
            "Posição do visitante": contexto.get("Posição do visitante", ""),
            "Pontos do mandante": contexto.get("Pontos do mandante", ""),
            "Pontos do visitante": contexto.get("Pontos do visitante", ""),
            "Pontos por jogo do mandante": contexto.get("Pontos por jogo do mandante", ""),
            "Pontos por jogo do visitante": contexto.get("Pontos por jogo do visitante", ""),
        })
    return linhas


def criar_registros(payload: dict) -> tuple[list[dict], list[dict]]:
    contexto = payload["contexto"]
    linhas_cotacoes = criar_linhas_cotacoes(
        payload["id_coleta"], payload["liga"], payload["temporada"], payload["data"], payload.get("horario"),
        payload["mandante"], payload["visitante"], payload["fonte"], payload["odds"], payload.get("banca", 0.0), contexto,
    )
    momento = agora_brasilia()
    config_json = json.dumps({
        "percentual_unidade": payload.get("percentual_unidade", 0.0),
        "valor_unidade": payload.get("valor_unidade", 0.0),
        "contexto_classificacao": {k: v for k, v in contexto.items() if k != "Quadro"},
    }, ensure_ascii=False, default=str)
    registros = []
    for _, linha in payload["resultado"].iterrows():
        codigo = str(linha["Side"])
        prob_esportiva = float(linha["SportsProbability"])
        prob_empirica = linha.get("HistoricalHitRate")
        registros.append({
            "ID Análise": payload["identificador"],
            "ID Coleta": payload["id_coleta"],
            "Registrado em": momento,
            "Liga": payload["liga"],
            "Jogo": f"{payload['mandante']} x {payload['visitante']}",
            "Mandante": payload["mandante"],
            "Visitante": payload["visitante"],
            "Data do jogo": payload["data"].strftime("%Y-%m-%d"),
            "Hora do jogo": payload.get("horario").strftime("%H:%M") if payload.get("horario") else "",
            "Casa de apostas": payload["fonte"] or "Não informada",
            "Origem": "Digitação manual",
            "Mercado": _mercado_legado(codigo),
            "Cotação": float(linha["ExecutableOdd"]),
            "Probabilidade operacional %": prob_esportiva * 100.0,
            "Probabilidade Poisson %": prob_esportiva * 100.0,
            "Probabilidade empírica %": "" if pd.isna(prob_empirica) else float(prob_empirica) * 100.0,
            "Probabilidade de mercado ajustada %": float(linha["MarketProbability"]) * 100.0,
            "Cotação justa": (1.0 / prob_esportiva) if prob_esportiva > 0 else "",
            "Valor esperado %": float(linha["ValorEsperadoEsportivo"]) * 100.0,
            "Gols projetados casa": payload["esportivo"]["LambdaHome"],
            "Gols projetados fora": payload["esportivo"]["LambdaAway"],
            "Gols projetados total": payload["esportivo"]["LambdaHome"] + payload["esportivo"]["LambdaAway"],
            "Chance mandante marcar %": (1.0 - np.exp(-payload["esportivo"]["LambdaHome"])) * 100.0,
            "Chance visitante marcar %": (1.0 - np.exp(-payload["esportivo"]["LambdaAway"])) * 100.0,
            "Amostra casa": "",
            "Amostra fora": "",
            "Estabilidade": linha["SituacaoDetalhada"],
            "Situação": linha["SituacaoDetalhada"],
            "Entrada %": payload.get("percentual_unidade", 0.0) if linha["SituacaoDetalhada"] == "AUTORIZADA" else 0.0,
            "Versão do modelo": "Tex Statistics v.25",
            "Configuração JSON": config_json,
            "Probabilidade mínima exigida %": float(linha["ProbabilidadeMinima"]) * 100.0,
            "Diferença modelo–mercado (p.p.)": float(linha["ProbabilityDifference"]) * 100.0,
            "Amostra histórica": int(linha.get("HistoricalBets") or 0),
            "Retorno histórico %": "" if pd.isna(linha.get("HistoricalROI")) else float(linha["HistoricalROI"]) * 100.0,
            "Motivo da decisão": linha["Motivo"],
            "Posição do mandante": contexto.get("Posição do mandante", ""),
            "Posição do visitante": contexto.get("Posição do visitante", ""),
            "Pontos do mandante": contexto.get("Pontos do mandante", ""),
            "Pontos do visitante": contexto.get("Pontos do visitante", ""),
            "Pontos por jogo do mandante": contexto.get("Pontos por jogo do mandante", ""),
            "Pontos por jogo do visitante": contexto.get("Pontos por jogo do visitante", ""),
            "Resultado confirmado": "NÃO",
        })
    return linhas_cotacoes, registros


def gerar_resumo_compartilhavel(payload: dict) -> str:
    contexto = payload["contexto"]
    linhas = [
        "TEX STATISTICS V.25 — RESUMO PARA ANÁLISE TEXTUAL",
        f"Identificador da análise: {payload['identificador']}",
        f"Jogo: {payload['mandante']} x {payload['visitante']}",
        f"Liga: {payload['liga']} | Temporada: {payload['temporada']}",
        f"Data: {payload['data'].strftime('%d/%m/%Y')} | Horário de Brasília: {payload.get('horario').strftime('%H:%M') if payload.get('horario') else 'não informado'}",
        f"Fonte das cotações: {payload['fonte'] or 'não informada'}",
        f"Fonte dos dados esportivos: {payload.get('fonte_dados_esportivos', 'Football-Data.co.uk — consulta direta, sem ZIP')}",
        f"Último jogo disponível na liga: {payload.get('ultima_data_liga').strftime('%d/%m/%Y') if payload.get('ultima_data_liga') else 'não disponível'} | Partidas carregadas na liga: {int(payload.get('partidas_liga_carregadas', 0))}",
        f"Banca: R$ {payload.get('banca', 0.0):.2f} | Unidade: {payload.get('percentual_unidade', 0.0):.2f}% = R$ {payload.get('valor_unidade', 0.0):.2f}",
        "",
        "CLASSIFICAÇÃO PRÉ-JOGO",
    ]
    if contexto.get("Disponível"):
        linhas.extend([
            f"- {payload['mandante']}: {contexto.get('Posição do mandante')}º, {contexto.get('Pontos do mandante')} pontos, {contexto.get('Pontos por jogo do mandante'):.2f} ponto por jogo.",
            f"- {payload['visitante']}: {contexto.get('Posição do visitante')}º, {contexto.get('Pontos do visitante')} pontos, {contexto.get('Pontos por jogo do visitante'):.2f} ponto por jogo.",
        ])
    else:
        linhas.append("- Classificação indisponível para o recorte selecionado.")
    linhas.extend([
        "",
        "PROJEÇÃO DE GOLS",
        f"- Mandante: {payload['esportivo']['LambdaHome']:.2f}",
        f"- Visitante: {payload['esportivo']['LambdaAway']:.2f}",
        f"- Total: {payload['esportivo']['LambdaHome'] + payload['esportivo']['LambdaAway']:.2f}",
        f"- Probabilidade de ambas as equipes marcarem: {payload['esportivo']['BTTS_Y']:.2%}",
        "",
        "COTAÇÕES, PROBABILIDADES E DECISÕES",
    ])
    for _, r in payload["resultado"].iterrows():
        linhas.append(
            f"- {nome_selecao(str(r['Side']), payload['mandante'], payload['visitante'])}: "
            f"cotação {float(r['ExecutableOdd']):.2f}; mercado {float(r['MarketProbability']):.2%}; "
            f"esportiva {float(r['SportsProbability']):.2%}; mínima exigida {float(r['ProbabilidadeMinima']):.2%}; "
            f"valor esperado {float(r['ValorEsperadoEsportivo']):.2%}; situação {r['SituacaoDetalhada']}. "
            f"Motivo: {r['Motivo']}"
        )
    autorizadas = payload["resultado"][payload["resultado"]["SituacaoDetalhada"] == "AUTORIZADA"]
    sinais = payload["resultado"][payload["resultado"]["SituacaoDetalhada"].astype(str).str.startswith("SINAL")]
    linhas.extend(["", "CONCLUSÃO AUTOMÁTICA"])
    if not autorizadas.empty:
        nomes = ", ".join(nome_selecao(str(c), payload['mandante'], payload['visitante']) for c in autorizadas['Side'])
        linhas.append(f"- Entrada(s) autorizada(s): {nomes}.")
    elif not sinais.empty:
        linhas.append("- Nenhuma entrada autorizada. Diagnóstico dos sinais com valor:")
        for _, sinal in sinais.iterrows():
            linhas.append(
                f"  - {nome_selecao(str(sinal['Side']), payload['mandante'], payload['visitante'])}: "
                f"{sinal['SituacaoDetalhada']}. {sinal['Motivo']}"
            )
    else:
        linhas.append("- Nenhuma entrada autorizada; todas as seleções foram descartadas por ausência de valor.")
    return "\n".join(linhas)


def mostrar_resumo_compartilhavel(payload: dict) -> None:
    resumo = gerar_resumo_compartilhavel(payload)
    st.markdown("### Resumo para copiar e enviar")
    st.caption("Este é o texto completo para copiar e enviar em uma nova análise.")
    st.text_area("Resumo textual", value=resumo, height=460, key=f"resumo_{payload['identificador']}")
    texto_js = json.dumps(resumo, ensure_ascii=False)
    components.html(
        f'''<button id="copiar" style="width:100%;padding:12px;border:0;border-radius:10px;font-weight:700;cursor:pointer;background:#ef4444;color:white">COPIAR RESUMO</button>
        <script>
        document.getElementById('copiar').onclick = async () => {{
          try {{ await navigator.clipboard.writeText({texto_js}); document.getElementById('copiar').innerText='RESUMO COPIADO'; }}
          catch(e) {{ document.getElementById('copiar').innerText='SELECIONE O TEXTO ACIMA E COPIE'; }}
        }};
        </script>''',
        height=52,
    )
    st.download_button(
        "BAIXAR RESUMO EM TXT",
        resumo.encode("utf-8"),
        file_name=f"resumo_{payload['identificador']}.txt",
        mime="text/plain",
        key=f"baixar_resumo_{payload['identificador']}",
    )

def historico_local(sincronizar_google: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Usa cache da sessão e só lê a Planilha Google quando o usuário pedir."""
    cotacoes = pd.DataFrame(st.session_state.historico_google_cotacoes)
    analises = pd.DataFrame(st.session_state.historico_google_analises)

    if sincronizar_google and google_configurado(st.secrets):
        try:
            cotacoes_google = carregar_cotacoes(st.secrets)
            analises_google = carregar_analises(st.secrets)
            st.session_state.historico_google_cotacoes = cotacoes_google.to_dict("records")
            st.session_state.historico_google_analises = analises_google.to_dict("records")
            cotacoes = cotacoes_google
            analises = analises_google
            st.success("Histórico sincronizado com a Planilha Google.")
        except Exception as erro:
            st.warning(f"Não foi possível sincronizar agora: {erro}")

    cotacoes_sessao = pd.DataFrame(st.session_state.historico_sessao_cotacoes)
    analises_sessao = pd.DataFrame(st.session_state.historico_sessao_analises)
    if not cotacoes_sessao.empty:
        cotacoes = pd.concat([cotacoes, cotacoes_sessao], ignore_index=True)
    if not analises_sessao.empty:
        analises = pd.concat([analises, analises_sessao], ignore_index=True)

    if not cotacoes.empty and "ID Coleta" in cotacoes:
        cotacoes = cotacoes.drop_duplicates(["ID Coleta", "Mercado"], keep="last")
    if not analises.empty and all(coluna in analises for coluna in ["ID Análise", "Mercado"]):
        analises = analises.drop_duplicates(["ID Análise", "Mercado"], keep="last")
    return cotacoes, analises


with st.sidebar:
    st.markdown("### Regra operacional")
    st.write("Até quatro seleções por semana, escolhidas somente entre faixas históricas aprovadas.")
    st.write("A cotação usada no cálculo é exatamente a cotação digitada.")
    st.write("Dados esportivos: Football-Data.co.uk, consultado diretamente. O aplicativo não usa ZIP local.")
    if google_configurado(st.secrets):
        st.success("Histórico permanente conectado.")
    else:
        st.warning("Planilha Google ainda não conectada.")

with st.container(border=True):
    banco1, banco2, banco3, banco4 = st.columns([1.2, 1.0, 1.0, 1.0])
    with banco1:
        banca_atual = st.number_input(
            "Banca atual (R$)", min_value=0.0, value=1000.0, step=50.0, format="%.2f", key="banca_atual_v25"
        )
    with banco2:
        percentual_unidade = st.number_input(
            "Percentual por entrada", min_value=0.10, max_value=10.0, value=1.0, step=0.10, format="%.2f", key="percentual_unidade_v25"
        )
    valor_unidade = float(banca_atual) * float(percentual_unidade) / 100.0
    with banco3:
        st.metric("Valor da unidade", f"R$ {valor_unidade:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with banco4:
        st.metric("Limite semanal", f"R$ {valor_unidade * CFG.weekly_top_n:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

abas = st.tabs(
    [
        "Jogo individual",
        "Lote semanal",
        "Histórico e auditoria",
        "Atualização dos dados",
        "Planilha Google",
    ]
)
aba_jogo, aba_lote, aba_historico, aba_atualizacao, aba_planilha = abas

with aba_jogo:
    coluna1, coluna2, coluna3, coluna4 = st.columns([1.45, 0.8, 1.0, 0.9])
    with coluna1:
        nome_liga = st.selectbox("Liga", list(liga_para_codigo), key="liga_individual")
        codigo = liga_para_codigo[nome_liga]
    with coluna2:
        temporada = st.number_input(
            "Temporada inicial",
            min_value=2016,
            max_value=2035,
            value=temporada_padrao(codigo, agora_em_brasilia().date()),
            step=1,
        )
    with coluna3:
        data_analise = st.date_input(
            "Data da partida",
            value=agora_em_brasilia().date(),
            format="DD/MM/YYYY",
            key="data_partida_v25",
        )
    with coluna4:
        horario_partida = st.time_input(
            "Horário da partida (Brasília)",
            value=None,
            step=900,
            key="horario_partida_v25",
        )

    data_mais_recente = ultima_data_da_liga(codigo)
    if data_mais_recente:
        st.info(
            f"Último resultado carregado para {nome_liga}: {data_mais_recente.strftime('%d/%m/%Y')}. "
            "A base externa é consultada automaticamente a cada três horas."
        )

    equipes = equipes_por_codigo[codigo]
    if len(equipes) < 2:
        st.error("Não há equipes suficientes carregadas nesta liga.")
        st.stop()
    c1, c2 = st.columns(2)
    with c1:
        mandante = st.selectbox("Mandante", equipes, key="equipe_mandante")
    with c2:
        visitante = st.selectbox(
            "Visitante", [equipe for equipe in equipes if equipe != mandante], key="equipe_visitante"
        )

    contexto = contexto_da_classificacao(codigo, int(temporada), data_analise, mandante, visitante)
    mostrar_classificacao(contexto, mandante, visitante)

    fonte = st.text_input("Fonte das cotações", placeholder="Ex.: casa ou plataforma consultada")
    st.markdown("### Cotações disponíveis")
    st.caption("Toque no campo e digite: o valor anterior fica selecionado e é substituído automaticamente.")
    a1, a2, a3 = st.columns(3)
    with a1:
        odd_casa = entrada_odd("Vitória do mandante", "odd_casa")
    with a2:
        odd_empate = entrada_odd("Empate", "odd_empate")
    with a3:
        odd_fora = entrada_odd("Vitória do visitante", "odd_fora")
    a4, a5 = st.columns(2)
    with a4:
        odd_mais = entrada_odd("Mais de 2,5 gols", "odd_mais")
    with a5:
        odd_menos = entrada_odd("Menos de 2,5 gols", "odd_menos")

    ambas1, ambas2 = st.columns(2)
    with ambas1:
        odd_ambas_sim = entrada_odd("Ambas as equipes marcam — Sim", "odd_ambas_sim")
    with ambas2:
        odd_ambas_nao = entrada_odd("Ambas as equipes marcam — Não", "odd_ambas_nao")

    ativar_digitacao_rapida_das_odds()

    margem_resultado = margem_bruta([odd_casa, odd_empate, odd_fora])
    margem_gols = margem_bruta([odd_mais, odd_menos])
    if margem_resultado is not None:
        if margem_resultado < -0.02 or margem_resultado > 0.20:
            st.error(f"As três cotações de resultado produzem margem de {margem_resultado:.2%}. Revise os valores.")
        else:
            st.caption(f"Margem calculada do mercado de resultado: {margem_resultado:.2%}.")
    if margem_gols is not None:
        if margem_gols < -0.02 or margem_gols > 0.15:
            st.warning(f"As cotações de gols produzem margem de {margem_gols:.2%}. Revise os valores.")
        else:
            st.caption(f"Margem calculada do mercado de gols: {margem_gols:.2%}.")

    assinatura_formulario = (
        nome_liga, int(temporada), data_analise.isoformat(), str(horario_partida), mandante, visitante, fonte,
        round(odd_casa, 4), round(odd_empate, 4), round(odd_fora, 4), round(odd_mais, 4),
        round(odd_menos, 4), round(odd_ambas_sim, 4), round(odd_ambas_nao, 4),
    )
    botao1, botao2 = st.columns(2)
    with botao1:
        salvar_cotacoes_agora = st.button("SALVAR COTAÇÕES", type="secondary", use_container_width=True)
    with botao2:
        analisar_agora = st.button("ANALISAR JOGO", type="primary", use_container_width=True)

    if salvar_cotacoes_agora:
        identificador_coleta = uuid4().hex[:12]
        odds_para_salvar = {
            "H": odd_casa, "D": odd_empate, "A": odd_fora, "O25": odd_mais, "U25": odd_menos,
            "AMBAS_SIM": odd_ambas_sim, "AMBAS_NAO": odd_ambas_nao,
        }
        linhas_cotacoes = criar_linhas_cotacoes(
            identificador_coleta, nome_liga, int(temporada), data_analise, horario_partida, mandante, visitante,
            fonte, odds_para_salvar, float(banca_atual), contexto,
        )
        if not linhas_cotacoes:
            st.error("Informe pelo menos uma cotação válida antes de salvar.")
        elif google_configurado(st.secrets):
            try:
                quantidade = salvar_cotacoes(st.secrets, linhas_cotacoes)
                st.session_state.historico_sessao_cotacoes.extend(linhas_cotacoes)
                st.session_state.ultima_coleta_v25 = {"assinatura": assinatura_formulario, "id": identificador_coleta}
                st.success(f"{quantidade} cotação(ões) acrescentada(s) ao catálogo da planilha antiga. Nenhuma linha anterior foi alterada.")
            except Exception as erro:
                if "429" in str(erro) or "quota" in str(erro).lower():
                    st.error("O Google bloqueou temporariamente novas requisições por excesso de leituras da versão anterior. Aguarde cerca de 60 segundos e clique novamente. Esta correção não relê a planilha antes de salvar.")
                else:
                    st.error(f"Não foi possível salvar na planilha antiga: {erro}")
        else:
            st.error("A conta de serviço do Google não foi reconhecida. A V25 já aponta para a planilha antiga; confira os Segredos do Streamlit.")

    if analisar_agora:
        try:
            estado = estado_antes_da_data(data_analise.isoformat())
            esportivo = sports_probabilities_for_match(codigo, mandante, visitante, estado, CFG)
            odds = {"H": odd_casa, "D": odd_empate, "A": odd_fora}
            if odd_mais > 1 and odd_menos > 1:
                odds.update({"O25": odd_mais, "U25": odd_menos})
            resultado = evaluate_live_market(
                codigo,
                int(temporada),
                mandante,
                visitante,
                odds,
                odds,
                esportivo,
                metricas_zonas,
                CFG,
            )
            if resultado.empty:
                st.error("Preencha pelo menos as três cotações do resultado da partida.")
            else:
                resultado = preparar_resultado(resultado)
                st.session_state.ultima_analise_v25 = {
                    "identificador": uuid4().hex[:12],
                    "id_coleta": (
                        st.session_state.get("ultima_coleta_v25", {}).get("id")
                        if st.session_state.get("ultima_coleta_v25", {}).get("assinatura") == assinatura_formulario
                        else uuid4().hex[:12]
                    ),
                    "data": data_analise,
                    "horario": horario_partida,
                    "banca": float(banca_atual),
                    "percentual_unidade": float(percentual_unidade),
                    "valor_unidade": float(valor_unidade),
                    "liga": nome_liga,
                    "codigo": codigo,
                    "temporada": int(temporada),
                    "mandante": mandante,
                    "visitante": visitante,
                    "fonte": fonte,
                    "fonte_dados_esportivos": "Football-Data.co.uk — consulta direta, sem ZIP",
                    "ultima_data_liga": ultima_data_da_liga(codigo),
                    "partidas_liga_carregadas": quantidade_partidas_da_liga(codigo),
                    "esportivo": esportivo,
                    "contexto": contexto,
                    "resultado": resultado,
                    "odds": {
                        **odds,
                        "AMBAS_SIM": odd_ambas_sim,
                        "AMBAS_NAO": odd_ambas_nao,
                    },
                }
        except Exception as erro:
            st.error(str(erro))

    payload = st.session_state.ultima_analise_v25
    if payload and payload["liga"] == nome_liga and payload["mandante"] == mandante and payload["visitante"] == visitante:
        mostrar_resultado(payload["resultado"], mandante, visitante, float(payload.get("valor_unidade", 0.0)))
        m1, m2, m3 = st.columns(3)
        m1.metric("Gols esperados do mandante", f"{payload['esportivo']['LambdaHome']:.2f}")
        m2.metric("Gols esperados do visitante", f"{payload['esportivo']['LambdaAway']:.2f}")
        m3.metric("Probabilidade de ambas as equipes marcarem", f"{payload['esportivo']['BTTS_Y']:.2%}")

        if odd_ambas_sim > 1 and odd_ambas_nao > 1:
            probabilidades_ambas = no_vig_probabilities([odd_ambas_sim, odd_ambas_nao])
            valor_ambas = payload["esportivo"]["BTTS_Y"] * odd_ambas_sim - 1.0
            st.info(
                f"Ambas as equipes marcam — Sim: probabilidade do mercado {probabilidades_ambas[0]:.2%}; "
                f"probabilidade esportiva {payload['esportivo']['BTTS_Y']:.2%}; "
                f"valor esperado esportivo {valor_ambas:.2%}. "
                "Este mercado é exibido apenas como leitura esportiva porque a regra histórica de autorização da V25 ainda não inclui ambas as equipes marcam."
            )

        linhas_cotacoes, registros = criar_registros(payload)
        mostrar_resumo_compartilhavel(payload)
        s1, s2, s3 = st.columns([1.5, 1.2, 1.2])
        with s1:
            if st.button("SALVAR ANÁLISE COMPLETA", type="secondary", use_container_width=True):
                if google_configurado(st.secrets):
                    try:
                        quantidade_cotacoes = salvar_cotacoes(st.secrets, linhas_cotacoes)
                        quantidade_analises = salvar_analises(st.secrets, registros)
                        st.session_state.historico_sessao_cotacoes.extend(linhas_cotacoes)
                        st.session_state.historico_sessao_analises.extend(registros)
                        st.success(
                            f"Planilha antiga atualizada: {quantidade_cotacoes} cotação(ões) nova(s) e "
                            f"{quantidade_analises} linha(s) de análise. O histórico anterior foi preservado."
                        )
                    except Exception as erro:
                        if "429" in str(erro) or "quota" in str(erro).lower():
                            st.error("O Google bloqueou temporariamente novas requisições por excesso de leituras da versão anterior. Aguarde cerca de 60 segundos e clique novamente. A correção atual grava por acréscimo sem reler toda a planilha.")
                        else:
                            st.error(f"Falha ao salvar na planilha antiga: {erro}")
                else:
                    st.error("A conta de serviço do Google não foi reconhecida nos Segredos do Streamlit.")
        with s2:
            st.download_button(
                "BAIXAR PROBABILIDADES",
                pd.DataFrame(registros).to_csv(index=False).encode("utf-8-sig"),
                f"probabilidades_{payload['identificador']}.csv",
                "text/csv",
                use_container_width=True,
            )
        with s3:
            st.download_button(
                "BAIXAR COTAÇÕES",
                pd.DataFrame(linhas_cotacoes).to_csv(index=False).encode("utf-8-sig"),
                f"cotacoes_{payload['id_coleta']}.csv",
                "text/csv",
                use_container_width=True,
            )

with aba_lote:
    st.write("Envie os jogos da semana com uma única cotação por seleção.")
    modelo = pd.DataFrame(
        [
            {
                "Data": agora_em_brasilia().strftime("%d/%m/%Y"),
                "Horário (Brasília)": "20:00",
                "Liga": "Inglaterra - Premier League",
                "Mandante": "Arsenal",
                "Visitante": "Liverpool",
                "Cotação mandante": 2.10,
                "Cotação empate": 3.40,
                "Cotação visitante": 3.50,
                "Cotação mais de 2,5": 1.90,
                "Cotação menos de 2,5": 1.90,
            }
        ]
    )
    st.download_button(
        "Baixar modelo do lote",
        modelo.to_csv(index=False).encode("utf-8-sig"),
        "modelo_lote_v25.csv",
        "text/csv",
    )
    arquivo_lote = st.file_uploader("Enviar lote em CSV", type=["csv"])
    if arquivo_lote is not None:
        try:
            lote = pd.read_csv(arquivo_lote)
            obrigatorias = [
                "Data", "Liga", "Mandante", "Visitante",
                "Cotação mandante", "Cotação empate", "Cotação visitante",
            ]
            faltantes = [coluna for coluna in obrigatorias if coluna not in lote.columns]
            if faltantes:
                raise ValueError("Colunas ausentes: " + ", ".join(faltantes))
            autorizadas_lote = []
            sinais_lote = []
            for _, item in lote.iterrows():
                liga = str(item["Liga"]).strip()
                if liga not in liga_para_codigo:
                    continue
                cod = liga_para_codigo[liga]
                data_jogo = pd.to_datetime(item["Data"], dayfirst=True).date()
                mand = str(item["Mandante"]).strip()
                visit = str(item["Visitante"]).strip()
                estado_lote = estado_antes_da_data(data_jogo.isoformat())
                esportivo = sports_probabilities_for_match(cod, mand, visit, estado_lote, CFG)
                odds = {
                    "H": float(item["Cotação mandante"]),
                    "D": float(item["Cotação empate"]),
                    "A": float(item["Cotação visitante"]),
                }
                if "Cotação mais de 2,5" in lote.columns and "Cotação menos de 2,5" in lote.columns:
                    mais = pd.to_numeric(item.get("Cotação mais de 2,5"), errors="coerce")
                    menos = pd.to_numeric(item.get("Cotação menos de 2,5"), errors="coerce")
                    if pd.notna(mais) and pd.notna(menos) and mais > 1 and menos > 1:
                        odds.update({"O25": float(mais), "U25": float(menos)})
                temporada_lote = temporada_padrao(cod, data_jogo)
                analise = evaluate_live_market(
                    cod, temporada_lote, mand, visit, odds, odds, esportivo, metricas_zonas, CFG
                )
                if analise.empty:
                    continue
                analise = preparar_resultado(analise)
                analise["Data"] = data_jogo
                analise["Semana"] = f"{data_jogo.isocalendar().year}-{data_jogo.isocalendar().week:02d}"
                analise["Seleção"] = analise["Side"].map(lambda valor: nome_selecao(str(valor), mand, visit))
                autorizadas_lote.append(analise[analise["SituacaoDetalhada"] == "AUTORIZADA"])
                sinais_lote.append(analise[analise["SituacaoDetalhada"].str.startswith("SINAL")])

            autorizadas_lote = [frame for frame in autorizadas_lote if not frame.empty]
            sinais_lote = [frame for frame in sinais_lote if not frame.empty]
            if autorizadas_lote:
                final = pd.concat(autorizadas_lote, ignore_index=True)
                final = (
                    final.sort_values(["Semana", "MarketProbability", "HistoricalHitRate"], ascending=[True, False, False])
                    .groupby("Semana", as_index=False)
                    .head(CFG.weekly_top_n)
                )
                st.success(f"{len(final)} seleções autorizadas no lote.")
                st.dataframe(
                    final[["Semana", "League", "Home", "Away", "Seleção", "MarketProbability", "SportsProbability", "ExecutableOdd", "HistoricalHitRate", "HistoricalROI"]]
                    .rename(columns={
                        "League": "Liga", "Home": "Mandante", "Away": "Visitante",
                        "MarketProbability": "Probabilidade do mercado",
                        "SportsProbability": "Probabilidade esportiva",
                        "ExecutableOdd": "Cotação informada",
                        "HistoricalHitRate": "Acerto histórico",
                        "HistoricalROI": "Retorno histórico",
                    })
                    .style.format({
                        "Probabilidade do mercado": "{:.2%}",
                        "Probabilidade esportiva": "{:.2%}",
                        "Cotação informada": "{:.2f}",
                        "Acerto histórico": "{:.2%}",
                        "Retorno histórico": "{:.2%}",
                    }, na_rep="—"),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.warning("Nenhuma seleção autorizada foi encontrada no lote.")
            if sinais_lote:
                sinais = pd.concat(sinais_lote, ignore_index=True)
                with st.expander(f"Ver {len(sinais)} sinais não validados"):
                    st.dataframe(
                        sinais[["Semana", "League", "Home", "Away", "Seleção", "SituacaoDetalhada", "SportsProbability", "ExecutableOdd", "ValorEsperadoEsportivo", "Motivo"]]
                        .rename(columns={
                            "League": "Liga", "Home": "Mandante", "Away": "Visitante",
                            "SituacaoDetalhada": "Situação", "SportsProbability": "Probabilidade esportiva",
                            "ExecutableOdd": "Cotação informada", "ValorEsperadoEsportivo": "Valor esperado esportivo",
                            "Motivo": "Motivo",
                        })
                        .style.format({
                            "Probabilidade esportiva": "{:.2%}",
                            "Cotação informada": "{:.2f}",
                            "Valor esperado esportivo": "{:.2%}",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )
        except Exception as erro:
            st.error(str(erro))

with aba_historico:
    st.markdown("### Histórico cumulativo")
    sincronizar_historico = st.button("SINCRONIZAR HISTÓRICO AGORA", type="secondary", use_container_width=True)
    st.caption("A planilha não é relida a cada clique. Use este botão somente quando precisar atualizar a tela de auditoria.")
    cotacoes_historicas, analises_historicas = historico_local(sincronizar_google=sincronizar_historico)
    st.write("Cada salvamento acrescenta novas linhas ao mesmo arquivo da Planilha Google. As antigas não são substituídas.")
    sub1, sub2, sub3 = st.tabs(["Cotações", "Probabilidades e decisões", "Resultados e desempenho"])
    with sub1:
        if cotacoes_historicas.empty:
            st.info("Ainda não há cotações salvas.")
        else:
            st.metric("Jogos salvos", cotacoes_historicas["ID Coleta"].nunique())
            st.dataframe(cotacoes_historicas.iloc[::-1], use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar histórico de cotações",
                cotacoes_historicas.to_csv(index=False).encode("utf-8-sig"),
                "historico_cotacoes_v25.csv",
                "text/csv",
            )
    with sub2:
        if analises_historicas.empty:
            st.info("Ainda não há probabilidades salvas.")
        else:
            filtro_liga = st.selectbox("Filtrar por liga", ["Todas"] + sorted(analises_historicas["Liga"].dropna().unique().tolist()))
            situacoes_disponiveis = sorted(analises_historicas["Situação"].dropna().astype(str).unique().tolist())
            filtro_situacao = st.selectbox("Filtrar por situação", ["Todas"] + situacoes_disponiveis)
            filtrado = analises_historicas.copy()
            if filtro_liga != "Todas":
                filtrado = filtrado[filtrado["Liga"] == filtro_liga]
            if filtro_situacao != "Todas":
                filtrado = filtrado[filtrado["Situação"].astype(str).str.startswith(filtro_situacao)]
            st.dataframe(filtrado.iloc[::-1], use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar histórico de probabilidades",
                analises_historicas.to_csv(index=False).encode("utf-8-sig"),
                "historico_probabilidades_v25.csv",
                "text/csv",
            )
    with sub3:
        if analises_historicas.empty:
            st.info("Ainda não há operações salvas.")
        else:
            autorizadas = analises_historicas[analises_historicas["Situação"].astype(str) == "AUTORIZADA"]
            confirmadas = autorizadas[autorizadas["Resultado confirmado"].astype(str).str.upper() == "SIM"]
            lucro = pd.to_numeric(confirmadas["Lucro em unidades"], errors="coerce").sum() if not confirmadas.empty else 0.0
            vitorias = (confirmadas["Seleção vencedora"].astype(str).str.upper() == "SIM").sum() if not confirmadas.empty else 0
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Seleções autorizadas", len(autorizadas))
            c2.metric("Resultados confirmados", len(confirmadas))
            c3.metric("Vitórias", int(vitorias))
            c4.metric("Lucro", f"{lucro:.2f} unidades")

    st.markdown("### Confirmar resultado")
    if google_configurado(st.secrets):
        r1, r2, r3 = st.columns([2, 1, 1])
        with r1:
            identificador_resultado = st.text_input("Identificador da análise")
        with r2:
            gols_mandante = st.number_input("Gols do mandante", min_value=0, max_value=20, step=1)
        with r3:
            gols_visitante = st.number_input("Gols do visitante", min_value=0, max_value=20, step=1)
        observacao_resultado = st.text_input("Observação sobre o resultado")
        if st.button("Confirmar resultado na Planilha Google"):
            try:
                atualizadas = confirmar_resultado(
                    st.secrets,
                    identificador_resultado,
                    int(gols_mandante),
                    int(gols_visitante),
                    observacao_resultado,
                )
                if atualizadas:
                    st.success(f"Resultado confirmado em {atualizadas} linhas.")
                else:
                    st.warning("Identificador não encontrado.")
            except Exception as erro:
                st.error(str(erro))
    else:
        st.warning("A confirmação permanente exige conexão com a Planilha Google.")

    st.markdown("### Auditoria do modelo")
    try:
        registro = pd.read_json(REGISTRY, typ="series")
        teste = registro["test"]
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Entradas no teste final", int(teste["bets"]))
        a2.metric("Taxa de acerto", f"{teste['hit_rate']:.2%}")
        a3.metric("Retorno sobre as entradas", f"{teste['roi']:.2%}")
        a4.metric("Média por semana ativa", f"{teste['average_bets_per_active_week']:.2f}")
        st.write(
            f"Teste de 2022 a 2025: {int(teste['wins'])} vitórias em {int(teste['bets'])} seleções; "
            f"lucro de {teste['profit_units']:.2f} unidades; queda máxima acumulada de "
            f"{teste['max_drawdown_units']:.2f} unidades."
        )
    except Exception as erro:
        st.warning(f"Não foi possível abrir o registro do backtest: {erro}")

with aba_atualizacao:
    st.markdown("### Dados esportivos — Football-Data.co.uk")
    st.write(
        "Os jogos concluídos das 24 ligas são baixados diretamente dos arquivos CSV do Football-Data. "
        "Não existe leitura, mesclagem ou fallback para o ZIP antigo."
    )
    st.info(
        "A consulta fica em cache por 12 horas para evitar downloads repetidos a cada clique. "
        "O botão abaixo descarta o cache e força uma nova leitura direta da fonte."
    )
    falhas = sum(1 for item in relatorio_atualizacao if item.get("situacao") == "FALHA")
    parciais = sum(1 for item in relatorio_atualizacao if item.get("situacao") == "PARCIAL")
    atualizadas = sum(1 for item in relatorio_atualizacao if item.get("situacao") == "ATUALIZADA")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jogos concluídos carregados", len(partidas))
    c2.metric("Ligas atualizadas", atualizadas)
    c3.metric("Ligas parciais", parciais)
    c4.metric("Ligas com falha", falhas)
    if st.button("Atualizar agora"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    quadro_atualizacao = pd.DataFrame(relatorio_atualizacao)
    if not quadro_atualizacao.empty:
        quadro_atualizacao = quadro_atualizacao.rename(
            columns={
                "liga": "Liga",
                "ultima_data": "Último jogo na fonte",
                "quantidade": "Partidas carregadas",
                "arquivos_ok": "Arquivos carregados",
                "arquivos_tentados": "Arquivos consultados",
                "situacao": "Situação",
                "erro": "Detalhe",
            }
        )
        colunas = [
            coluna for coluna in
            ["Liga", "Último jogo na fonte", "Partidas carregadas", "Arquivos carregados", "Arquivos consultados", "Situação", "Detalhe"]
            if coluna in quadro_atualizacao
        ]
        st.dataframe(quadro_atualizacao[colunas], use_container_width=True, hide_index=True)

with aba_planilha:
    st.markdown("### Planilha Google histórica")
    cfg_google = configuracao_google(st.secrets)
    st.write("O aplicativo usa a mesma planilha das versões anteriores. Não é necessário criar outra.")
    st.link_button("ABRIR A PLANILHA ANTIGA", url_planilha_configurada(st.secrets), use_container_width=True)
    st.write(f"- **{cfg_google['worksheet_catalogo']}**: catálogo cumulativo de cotações.")
    st.write(f"- **{cfg_google['worksheet_historico']}**: probabilidades, decisões e resumos numéricos das análises.")
    st.write(f"- **{cfg_google['worksheet_auditoria']}**: auditoria das entradas confirmadas.")
    st.success("As gravações são somente de acréscimo: nenhuma linha antiga é apagada, sobrescrita ou substituída.")
    if google_configurado(st.secrets):
        st.success(f"Conexão ativa com a planilha antiga. Conta de serviço: {cfg_google['client_email']}")
    else:
        st.error(
            "A planilha antiga já está definida no aplicativo, mas a conta de serviço não foi encontrada. "
            "O aplicativo aceita o mesmo bloco [google_sheets] que já era usado nas versões anteriores."
        )
        st.code(
            '''[google_sheets]
spreadsheet_id = "1exfvkvNC_7W-0Nk51ZOue5Do7LtR9sS-8x5R0Gf_zMo"
worksheet_catalogo = "catalogo_odds"
worksheet_auditoria = "auditoria_entradas"
worksheet_historico = "historico_analises"

[gcp_service_account]
# mantenha aqui a mesma conta de serviço que já era usada pelo aplicativo antigo''',
            language="toml",
        )

