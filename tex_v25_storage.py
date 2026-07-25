from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Iterable
import json

import pandas as pd

from tex_v28_finance import COLUNAS_APOSTAS, liquidar_registro

# Planilha histórica que já era usada pelas versões anteriores.
PLANILHA_ANTIGA_ID = "1exfvkvNC_7W-0Nk51ZOue5Do7LtR9sS-8x5R0Gf_zMo"
PLANILHA_ANTIGA_URL = f"https://docs.google.com/spreadsheets/d/{PLANILHA_ANTIGA_ID}/edit"

ABA_COTACOES = "catalogo_odds"
ABA_ANALISES = "historico_analises"
ABA_AUDITORIA = "auditoria_entradas"

# Cache em memória do processo do Streamlit. Evita reabrir a planilha e reler
# metadados a cada clique/rerun, que era a causa do erro 429 de leitura.
_CLIENTES_GOOGLE: dict[tuple[str, str], Any] = {}
_PLANILHAS_GOOGLE: dict[tuple[str, str], Any] = {}
_ABAS_GOOGLE: dict[tuple[str, str, str], Any] = {}
_CHAVES_GRAVADAS_NO_PROCESSO: dict[tuple[str, str, str], set[tuple[str, ...]]] = {}
_CABECALHOS_SINCRONIZADOS: set[tuple[str, str, str]] = set()
_CABECALHOS_ATUAIS: dict[tuple[str, str, str], list[str]] = {}

# Mantém a estrutura histórica da planilha antiga e apenas acrescenta campos novos à direita.
COLUNAS_COTACOES = [
    "ID Coleta", "Registrado em", "Casa de apostas", "Liga", "Jogo", "Mandante", "Visitante",
    "Data do jogo", "Hora do jogo", "Mercado", "Seleção", "Cotação",
    "Grupo do mercado", "Mercado completo", "Probabilidade implícita bruta %",
    "Margem do mercado %", "Probabilidade ajustada sem margem %",
    "Banca no momento", "Perfil", "Origem", "Observação",
    "Temporada", "Posição do mandante", "Posição do visitante",
    "Pontos do mandante", "Pontos do visitante", "Pontos por jogo do mandante",
    "Pontos por jogo do visitante",
    "Versão da interface", "Versão da API do núcleo", "Versão do modelo",
]

COLUNAS_ANALISES = [
    "ID Análise", "ID Coleta", "Registrado em", "Liga", "Jogo", "Mandante", "Visitante",
    "Data do jogo", "Hora do jogo", "Casa de apostas", "Origem", "Mercado", "Cotação",
    "Probabilidade operacional %", "Probabilidade Poisson %", "Probabilidade empírica %",
    "Probabilidade de mercado ajustada %", "Cotação justa", "Valor esperado %",
    "Gols projetados casa", "Gols projetados fora", "Gols projetados total",
    "Chance mandante marcar %", "Chance visitante marcar %",
    "Amostra casa", "Amostra fora", "Estabilidade", "Situação", "Entrada %",
    "Versão do modelo", "Configuração JSON",
    "Probabilidade mínima exigida %", "Diferença modelo–mercado (p.p.)",
    "Amostra histórica", "Retorno histórico %", "Motivo da decisão",
    "Posição do mandante", "Posição do visitante", "Pontos do mandante", "Pontos do visitante",
    "Pontos por jogo do mandante", "Pontos por jogo do visitante",
    "Resultado — gols do mandante", "Resultado — gols do visitante", "Resultado confirmado",
    "Seleção vencedora", "Lucro em unidades", "Observações",
    "Versão da interface", "Versão da API do núcleo", "Probabilidade conservadora %",
    "Valor esperado do modelo %", "Valor esperado conservador %",
    "Limite conservador dos casos semelhantes %", "Código do mercado", "Código da seleção",
]


def agora_brasilia() -> str:
    return datetime.now(ZoneInfo("America/Fortaleza")).replace(microsecond=0).strftime("%d/%m/%Y %H:%M:%S")


def _dict_seguro(obj: Any) -> dict[str, Any]:
    try:
        return dict(obj)
    except Exception:
        return {}


def configuracao_google(secrets: Any) -> dict[str, Any]:
    """Aceita tanto o formato antigo [google_sheets] quanto o formato novo [google_sheet]."""
    antigo = _dict_seguro(getattr(secrets, "get", lambda *_: {}) ("google_sheets", {}))
    novo = _dict_seguro(getattr(secrets, "get", lambda *_: {}) ("google_sheet", {}))
    cfg = antigo or novo
    conta = _dict_seguro(getattr(secrets, "get", lambda *_: {}) ("gcp_service_account", {}))
    id_planilha = str(cfg.get("spreadsheet_id") or PLANILHA_ANTIGA_ID).strip()
    return {
        "conta": conta,
        "spreadsheet_id": id_planilha,
        "worksheet_catalogo": str(cfg.get("worksheet_catalogo") or ABA_COTACOES).strip(),
        "worksheet_auditoria": str(cfg.get("worksheet_auditoria") or ABA_AUDITORIA).strip(),
        "worksheet_historico": str(cfg.get("worksheet_historico") or ABA_ANALISES).strip(),
        "client_email": str(conta.get("client_email") or "").strip(),
        "configurado": bool(conta and id_planilha and conta.get("client_email")),
    }


def google_configurado(secrets: Any) -> bool:
    return bool(configuracao_google(secrets)["configurado"])


def url_planilha_configurada(secrets: Any) -> str:
    cfg = configuracao_google(secrets)
    return f"https://docs.google.com/spreadsheets/d/{cfg['spreadsheet_id']}/edit"


def _chave_conta(informacoes_conta: dict[str, Any]) -> tuple[str, str]:
    return (
        str(informacoes_conta.get("client_email") or ""),
        str(informacoes_conta.get("private_key_id") or ""),
    )


def _cliente_google(informacoes_conta: dict[str, Any]):
    import gspread
    from google.oauth2.service_account import Credentials

    chave = _chave_conta(informacoes_conta)
    if chave in _CLIENTES_GOOGLE:
        return _CLIENTES_GOOGLE[chave]

    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credenciais = Credentials.from_service_account_info(dict(informacoes_conta), scopes=escopos)
    cliente = gspread.authorize(credenciais)
    _CLIENTES_GOOGLE[chave] = cliente
    return cliente


def _abrir_planilha(secrets: Any):
    cfg = configuracao_google(secrets)
    if not cfg["configurado"]:
        raise RuntimeError(
            "A conta de serviço do Google não foi encontrada nos segredos do Streamlit. "
            "O identificador da planilha antiga já está configurado no aplicativo."
        )
    chave = (cfg["spreadsheet_id"], cfg["client_email"])
    if chave not in _PLANILHAS_GOOGLE:
        _PLANILHAS_GOOGLE[chave] = _cliente_google(cfg["conta"]).open_by_key(cfg["spreadsheet_id"])
    return _PLANILHAS_GOOGLE[chave]


def _letra_coluna(numero: int) -> str:
    texto = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        texto = chr(65 + resto) + texto
    return texto


def _obter_aba_cacheada(secrets: Any, titulo: str, colunas: list[str]):
    """Obtém a aba uma única vez por processo, sem ler linhas ou cabeçalhos em cada gravação."""
    cfg = configuracao_google(secrets)
    chave = (cfg["spreadsheet_id"], cfg["client_email"], str(titulo))
    if chave in _ABAS_GOOGLE:
        return _ABAS_GOOGLE[chave]

    planilha = _abrir_planilha(secrets)
    try:
        aba = planilha.worksheet(str(titulo))
    except Exception as exc:
        # Só cria quando a aba realmente não existe. A planilha antiga já possui as abas principais.
        if "not found" not in str(exc).lower() and "não encontr" not in str(exc).lower():
            try:
                from gspread.exceptions import WorksheetNotFound
                if not isinstance(exc, WorksheetNotFound):
                    raise
            except ImportError:
                raise
        aba = planilha.add_worksheet(title=str(titulo), rows=20000, cols=max(80, len(colunas) + 5))
        aba.append_row(colunas, value_input_option="RAW")

    if chave not in _CABECALHOS_SINCRONIZADOS:
        cabecalho = aba.row_values(1)
        if not cabecalho:
            aba.append_row(colunas, value_input_option="RAW")
            cabecalho = list(colunas)
        elif cabecalho != colunas:
            # Preserva as colunas antigas e acrescenta somente as ausentes à direita.
            atualizado = list(cabecalho)
            for coluna in colunas:
                if coluna not in atualizado:
                    atualizado.append(coluna)
            if atualizado != cabecalho:
                ultima = _letra_coluna(len(atualizado))
                aba.update(f"A1:{ultima}1", [atualizado], value_input_option="RAW")
                cabecalho = atualizado
        _CABECALHOS_ATUAIS[chave] = list(cabecalho)
        _CABECALHOS_SINCRONIZADOS.add(chave)

    _ABAS_GOOGLE[chave] = aba
    return aba


def _normalizar(registros: Iterable[dict[str, Any]], colunas: list[str]) -> list[dict[str, Any]]:
    saida: list[dict[str, Any]] = []
    for registro in registros:
        linha: dict[str, Any] = {}
        for coluna in colunas:
            valor = registro.get(coluna, "")
            if valor is None or (not isinstance(valor, (dict, list, tuple)) and pd.isna(valor)):
                valor = ""
            if isinstance(valor, (dict, list, tuple)):
                valor = json.dumps(valor, ensure_ascii=False)
            linha[coluna] = valor
        saida.append(linha)
    return saida


def _acrescentar_sem_leitura(
    secrets: Any,
    titulo: str,
    colunas: list[str],
    registros: Iterable[dict[str, Any]],
    campos_chave: list[str],
) -> int:
    """Acrescenta linhas sem executar row_values/get_all_values antes da escrita.

    A antiga implementação relia toda a aba para evitar duplicidade. No Streamlit,
    cada clique reroda o programa e isso consumia rapidamente a quota de leituras.
    A deduplicação durante o processo é feita em memória pelos identificadores únicos.
    """
    normalizados = _normalizar(registros, colunas)
    if not normalizados:
        return 0

    cfg = configuracao_google(secrets)
    cache_key = (cfg["spreadsheet_id"], cfg["client_email"], str(titulo))
    conhecidas = _CHAVES_GRAVADAS_NO_PROCESSO.setdefault(cache_key, set())
    novas: list[dict[str, Any]] = []
    novas_chaves: list[tuple[str, ...]] = []
    for registro in normalizados:
        chave = tuple(str(registro.get(campo, "")).strip() for campo in campos_chave)
        if chave in conhecidas:
            continue
        novas.append(registro)
        novas_chaves.append(chave)

    if not novas:
        return 0

    aba = _obter_aba_cacheada(secrets, titulo, colunas)
    worksheet_key = (cfg["spreadsheet_id"], cfg["client_email"], str(titulo))
    cabecalho_real = _CABECALHOS_ATUAIS.get(worksheet_key, list(colunas))
    linhas = [[registro.get(coluna, "") for coluna in cabecalho_real] for registro in novas]
    aba.append_rows(linhas, value_input_option="USER_ENTERED")
    conhecidas.update(novas_chaves)
    return len(linhas)


def _garantir_aba_para_leitura(secrets: Any, titulo: str, colunas: list[str]):
    """Leitura explícita usada apenas quando o usuário manda sincronizar o histórico."""
    aba = _obter_aba_cacheada(secrets, titulo, colunas)
    cabecalho = aba.row_values(1)
    if not cabecalho:
        aba.append_row(colunas, value_input_option="RAW")
        cabecalho = list(colunas)
    return aba, cabecalho


def _identificadores_existentes(
    secrets: Any, titulo: str, colunas: list[str], coluna_id: str
) -> set[str]:
    aba = _obter_aba_cacheada(secrets, titulo, colunas)
    cfg = configuracao_google(secrets)
    chave = (cfg["spreadsheet_id"], cfg["client_email"], str(titulo))
    cabecalho = _CABECALHOS_ATUAIS.get(chave) or aba.row_values(1)
    if coluna_id not in cabecalho:
        return set()
    valores = aba.col_values(cabecalho.index(coluna_id) + 1)
    return {str(value).strip() for value in valores[1:] if str(value).strip()}


def identificadores_cotacoes(secrets: Any) -> set[str]:
    cfg = configuracao_google(secrets)
    return _identificadores_existentes(
        secrets, cfg["worksheet_catalogo"], COLUNAS_COTACOES, "ID Coleta"
    )


def identificadores_analises(secrets: Any) -> set[str]:
    cfg = configuracao_google(secrets)
    return _identificadores_existentes(
        secrets, cfg["worksheet_historico"], COLUNAS_ANALISES, "ID Análise"
    )


def identificadores_apostas(secrets: Any) -> set[str]:
    cfg = configuracao_google(secrets)
    return _identificadores_existentes(
        secrets, cfg["worksheet_auditoria"], COLUNAS_APOSTAS, "ID Aposta"
    )

def salvar_cotacoes(secrets: Any, registros: Iterable[dict[str, Any]]) -> int:
    cfg = configuracao_google(secrets)
    return _acrescentar_sem_leitura(
        secrets,
        cfg["worksheet_catalogo"],
        COLUNAS_COTACOES,
        registros,
        ["ID Coleta", "Mercado"],
    )


def salvar_cotacao(secrets: Any, registro: dict[str, Any] | Iterable[dict[str, Any]]) -> int:
    if isinstance(registro, dict):
        return salvar_cotacoes(secrets, [registro])
    return salvar_cotacoes(secrets, registro)


def salvar_analises(secrets: Any, registros: Iterable[dict[str, Any]]) -> int:
    cfg = configuracao_google(secrets)
    return _acrescentar_sem_leitura(
        secrets,
        cfg["worksheet_historico"],
        COLUNAS_ANALISES,
        registros,
        ["ID Análise", "Mercado"],
    )


def _carregar_aba(secrets: Any, titulo: str, colunas: list[str]) -> pd.DataFrame:
    aba, cabecalho = _garantir_aba_para_leitura(secrets, titulo, colunas)
    valores = aba.get_all_values()
    if len(valores) <= 1:
        return pd.DataFrame(columns=cabecalho)
    largura = max(len(cabecalho), max(len(linha) for linha in valores[1:]))
    cabecalho = cabecalho + [f"Coluna extra {i}" for i in range(len(cabecalho) + 1, largura + 1)]
    linhas = [linha + [""] * (largura - len(linha)) for linha in valores[1:]]
    frame = pd.DataFrame(linhas, columns=cabecalho)
    ordem = colunas + [coluna for coluna in frame.columns if coluna not in colunas]
    for coluna in ordem:
        if coluna not in frame.columns:
            frame[coluna] = ""
    return frame[ordem]


def carregar_cotacoes(secrets: Any) -> pd.DataFrame:
    cfg = configuracao_google(secrets)
    return _carregar_aba(secrets, cfg["worksheet_catalogo"], COLUNAS_COTACOES)


def carregar_analises(secrets: Any) -> pd.DataFrame:
    cfg = configuracao_google(secrets)
    return _carregar_aba(secrets, cfg["worksheet_historico"], COLUNAS_ANALISES)



def salvar_apostas(secrets: Any, registros: Iterable[dict[str, Any]]) -> int:
    cfg = configuracao_google(secrets)
    return _acrescentar_sem_leitura(
        secrets, cfg["worksheet_auditoria"], COLUNAS_APOSTAS, registros, ["ID Aposta"]
    )


def carregar_apostas(secrets: Any) -> pd.DataFrame:
    cfg = configuracao_google(secrets)
    return _carregar_aba(secrets, cfg["worksheet_auditoria"], COLUNAS_APOSTAS)


def liquidar_aposta(
    secrets: Any,
    identificador: str,
    gols_mandante: int,
    gols_visitante: int,
    observacoes: str = "",
) -> dict[str, Any]:
    cfg = configuracao_google(secrets)
    aba, cabecalho = _garantir_aba_para_leitura(secrets, cfg["worksheet_auditoria"], COLUNAS_APOSTAS)
    valores = aba.get_all_values()
    indices = {nome: posicao for posicao, nome in enumerate(cabecalho)}
    if "ID Aposta" not in indices:
        raise RuntimeError("A aba de auditoria não possui a coluna ID Aposta.")
    for numero_linha, linha in enumerate(valores[1:], start=2):
        linha = linha + [""] * (len(cabecalho) - len(linha))
        if str(linha[indices["ID Aposta"]]).strip() != str(identificador).strip():
            continue
        record = {coluna: linha[posicao] if posicao < len(linha) else "" for coluna, posicao in indices.items()}
        updated = liquidar_registro(record, gols_mandante, gols_visitante, observacoes)
        row_values = list(linha[:len(cabecalho)])
        for coluna, valor in updated.items():
            if coluna in indices:
                row_values[indices[coluna]] = valor
        ultima = _letra_coluna(len(cabecalho))
        aba.update(
            f"A{numero_linha}:{ultima}{numero_linha}",
            [row_values],
            value_input_option="USER_ENTERED",
        )
        return updated
    raise KeyError(f"Aposta não encontrada: {identificador}.")

def confirmar_resultado(
    secrets: Any,
    identificador: str,
    gols_mandante: int,
    gols_visitante: int,
    observacoes: str = "",
) -> int:
    cfg = configuracao_google(secrets)
    aba, cabecalho = _garantir_aba_para_leitura(secrets, cfg["worksheet_historico"], COLUNAS_ANALISES)
    valores = aba.get_all_values()
    if not valores:
        return 0
    indices = {nome: posicao for posicao, nome in enumerate(cabecalho)}
    total_atualizacoes = 0
    for numero_linha, linha in enumerate(valores[1:], start=2):
        linha = linha + [""] * (len(cabecalho) - len(linha))
        if str(linha[indices["ID Análise"]]).strip() != str(identificador).strip():
            continue
        mercado = str(linha[indices["Mercado"]]).strip()
        mandante = str(linha[indices.get("Mandante", -1)]).strip() if "Mandante" in indices else ""
        visitante = str(linha[indices.get("Visitante", -1)]).strip() if "Visitante" in indices else ""
        selecao = mercado.split("—", 1)[1].strip() if "—" in mercado else mercado
        total_gols = gols_mandante + gols_visitante
        ambas = gols_mandante > 0 and gols_visitante > 0
        venceu = (
            (selecao == mandante and gols_mandante > gols_visitante)
            or (selecao == visitante and gols_visitante > gols_mandante)
            or (selecao == "Empate" and gols_mandante == gols_visitante)
            or (selecao in {"Mais de 2,5 gols", "Mais de 2.5 gols"} and total_gols >= 3)
            or (selecao in {"Menos de 2,5 gols", "Menos de 2.5 gols"} and total_gols <= 2)
            or (selecao == "Ambas marcam — Sim" and ambas)
            or (selecao == "Ambas marcam — Não" and not ambas)
        )
        try:
            odd = float(str(linha[indices["Cotação"]]).replace(",", ".") or 0.0)
        except Exception:
            odd = 0.0
        alteracoes = {
            "Resultado — gols do mandante": gols_mandante,
            "Resultado — gols do visitante": gols_visitante,
            "Resultado confirmado": "SIM",
            "Seleção vencedora": "SIM" if venceu else "NÃO",
            "Lucro em unidades": odd - 1.0 if venceu else -1.0,
            "Observações": observacoes,
        }
        row_values = list(linha[:len(cabecalho)])
        for coluna, valor in alteracoes.items():
            if coluna in indices:
                row_values[indices[coluna]] = valor
        ultima = _letra_coluna(len(cabecalho))
        aba.update(
            f"A{numero_linha}:{ultima}{numero_linha}",
            [row_values],
            value_input_option="USER_ENTERED",
        )
        total_atualizacoes += 1
    return total_atualizacoes
