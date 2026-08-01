from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Iterable
from numbers import Real
from types import SimpleNamespace
from uuid import uuid4
import json
import re
import time
import random

import pandas as pd

STORAGE_API_VERSION = "28.3.5"

from tex_v28_finance import COLUNAS_APOSTAS, identificador_registro, liquidar_registro

ABA_COTACOES = "catalogo_odds"
ABA_ANALISES = "historico_analises"
ABA_AUDITORIA = "auditoria_entradas"
ABA_LOTE_PENDENTE = "lote_pendente"
ABA_EVENTOS_LOTE = "entrada_jogos"

# Cache em memória do processo do Streamlit. Evita reabrir a planilha e reler
# metadados a cada clique/rerun, que era a causa do erro 429 de leitura.
_CLIENTES_GOOGLE: dict[tuple[str, str], Any] = {}
_PLANILHAS_GOOGLE: dict[tuple[str, str], Any] = {}
_ABAS_GOOGLE: dict[tuple[str, str, str], Any] = {}
_CHAVES_GRAVADAS_NO_PROCESSO: dict[tuple[str, str, str], set[tuple[str, ...]]] = {}
_CABECALHOS_SINCRONIZADOS: set[tuple[str, str, str]] = set()
_CABECALHOS_ATUAIS: dict[tuple[str, str, str], list[str]] = {}
_FORMATOS_NUMERICOS_SINCRONIZADOS: set[tuple[str, str, str]] = set()

# Colunas que precisam permanecer numéricas no Google Sheets. Algumas planilhas
# antigas carregavam formatação de data nessas posições; nesse caso, valores
# como 3.44 eram exibidos como 02.01 e 1.80 como 31.12.
COLUNAS_NUMERICAS_PLANILHA = {
    "Cotação", "Probabilidade implícita bruta %", "Margem do mercado %",
    "Probabilidade ajustada sem margem %", "Banca no momento",
    "Probabilidade operacional %", "Probabilidade Poisson %",
    "Probabilidade empírica %", "Probabilidade de mercado ajustada %",
    "Cotação justa", "Valor esperado %", "Gols projetados casa",
    "Gols projetados fora", "Gols projetados total", "Chance mandante marcar %",
    "Chance visitante marcar %", "Estabilidade", "Entrada %",
    "Probabilidade mínima exigida %", "Diferença modelo–mercado (p.p.)",
    "Retorno histórico %", "Pontos por jogo do mandante",
    "Pontos por jogo do visitante", "Lucro em unidades",
    "Probabilidade conservadora %", "Valor esperado do modelo %",
    "Valor esperado conservador %", "Limite conservador da faixa histórica %",
    "Odd mandante", "Odd empate", "Odd visitante", "Odd mais de 2,5",
    "Odd menos de 2,5", "Odd ambas marcam — Sim", "Odd ambas marcam — Não",
    "Entrada (R$)", "Lucro ou prejuízo (R$)", "Banca antes (R$)",
    "Banca depois (R$)", "Regra 3 — gols do mandante nas últimas 5",
    "Regra 4 — gols do visitante nas últimas 5", "Fator total da múltipla",
    "Probabilidade conjunta da múltipla %", "Valor esperado da múltipla %",
}

# O Google devolve números inteiros sem a parte decimal. Ex.: um valor enviado
# como 17.0 volta como 17 em UNFORMATTED_VALUE. Essas colunas precisam ser
# comparadas numericamente, sem que 17.0 x 17 seja tratado como falha.
COLUNAS_INTEIRAS_PLANILHA = {
    "Temporada", "Posição do mandante", "Posição do visitante",
    "Pontos do mandante", "Pontos do visitante", "Amostra casa",
    "Amostra fora", "Amostra histórica",
    "Regra 3 — gols do mandante nas últimas 5",
    "Regra 4 — gols do visitante nas últimas 5",
}
COLUNAS_NUMERICAS_PLANILHA.update(COLUNAS_INTEIRAS_PLANILHA)

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
    "Filtro 2018 — status", "Filtro 2018 — elegível operacional",
    "Regra 1 — resultado", "Regra 1 — fundamento", "Regra 1 — detalhe",
    "Regra 2 — resultado", "Regra 2 — detalhe",
    "Regra 3 — resultado", "Regra 3 — gols do mandante nas últimas 5", "Regra 3 — detalhe",
    "Regra 4 — resultado", "Regra 4 — gols do visitante nas últimas 5", "Regra 4 — detalhe",
    "Último confronto direto — data", "Último confronto direto — placar",
    "Último confronto direto — ambas marcaram", "Resumo do filtro 2018",
    "Decisão operacional", "Mercado escolhido para simples",
    "Incluído na sugestão de múltipla", "Fator total da múltipla",
    "Versão do filtro 2018",
]

COLUNAS_LOTE_PENDENTE = [
    "ID do lote", "Salvo em", "Quantidade de partidas", "Lote JSON",
    "Versão da interface", "Origem",
]

# Log durável e append-only. Cada inclusão, alteração, remoção ou limpeza gera
# uma nova linha. A restauração do lote não depende de uma única célula JSON.
COLUNAS_EVENTOS_LOTE = [
    "ID Evento", "ID do lote", "Tipo de evento", "Registrado em",
    "ID da partida", "Data", "Hora", "Código da liga", "Liga",
    "Mandante", "Visitante", "Casa de apostas",
    "Odd mandante", "Odd empate", "Odd visitante",
    "Odd mais de 2,5", "Odd menos de 2,5",
    "Odd ambas marcam — Sim", "Odd ambas marcam — Não",
    "Versão da interface", "Origem",
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
    "Limite conservador da faixa histórica %", "Código do mercado", "Código da seleção",
    "Filtro 2018 — status", "Filtro 2018 — elegível operacional",
    "Regra 1 — resultado", "Regra 1 — fundamento", "Regra 1 — detalhe",
    "Regra 2 — resultado", "Regra 2 — detalhe",
    "Regra 3 — resultado", "Regra 3 — gols do mandante nas últimas 5", "Regra 3 — detalhe",
    "Regra 4 — resultado", "Regra 4 — gols do visitante nas últimas 5", "Regra 4 — detalhe",
    "Último confronto direto — data", "Último confronto direto — placar",
    "Último confronto direto — ambas marcaram", "Resumo do filtro 2018",
    "Decisão operacional", "Mercado escolhido para simples",
    "Incluído na sugestão de múltipla", "Fator total da múltipla",
    "Probabilidade conjunta da múltipla %", "Valor esperado da múltipla %",
    "Versão do filtro 2018",
]


def agora_brasilia() -> str:
    return datetime.now(ZoneInfo("America/Fortaleza")).replace(microsecond=0).strftime("%d/%m/%Y %H:%M:%S")


def _dict_seguro(obj: Any) -> dict[str, Any]:
    try:
        return dict(obj)
    except Exception:
        return {}


def _extrair_id_planilha(valor: Any) -> str:
    """Extrai um ID explícito de uma chave ou URL do Google Sheets.

    Não existe fallback silencioso para outra planilha. Gravar em uma planilha
    diferente daquela que o usuário está conferindo é pior do que bloquear.
    """
    texto = str(valor or "").strip()
    if not texto:
        return ""
    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", texto)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{5,}", texto):
        return texto
    return ""


def configuracao_google(secrets: Any) -> dict[str, Any]:
    """Aceita [google_sheets] ou [google_sheet], mas exige destino explícito.

    Versões anteriores podiam usar um ID de planilha embutido como fallback. Isso
    permitia uma gravação aparentemente bem-sucedida em outra planilha. A partir
    da V28.1.5.11, o ID/URL precisa estar declarado nos Secrets.
    """
    antigo = _dict_seguro(getattr(secrets, "get", lambda *_: {}) ("google_sheets", {}))
    novo = _dict_seguro(getattr(secrets, "get", lambda *_: {}) ("google_sheet", {}))
    cfg = antigo or novo
    conta = _dict_seguro(getattr(secrets, "get", lambda *_: {}) ("gcp_service_account", {}))
    destino = (
        cfg.get("spreadsheet_id")
        or cfg.get("spreadsheet_url")
        or cfg.get("url_planilha")
        or cfg.get("url")
        or ""
    )
    id_planilha = _extrair_id_planilha(destino)
    client_email = str(conta.get("client_email") or "").strip()
    private_key = str(conta.get("private_key") or "").strip()
    credenciais_ok = bool(client_email and private_key)
    erro_configuracao = ""
    if not id_planilha:
        erro_configuracao = (
            "Informe spreadsheet_id ou spreadsheet_url em [google_sheets] ou [google_sheet]."
        )
    elif not credenciais_ok:
        erro_configuracao = (
            "As credenciais [gcp_service_account] precisam conter client_email e private_key."
        )
    return {
        "conta": conta,
        "spreadsheet_id": id_planilha,
        "worksheet_catalogo": str(cfg.get("worksheet_catalogo") or ABA_COTACOES).strip(),
        "worksheet_auditoria": str(cfg.get("worksheet_auditoria") or ABA_AUDITORIA).strip(),
        "worksheet_historico": str(cfg.get("worksheet_historico") or ABA_ANALISES).strip(),
        "worksheet_lote_pendente": str(cfg.get("worksheet_lote_pendente") or ABA_LOTE_PENDENTE).strip(),
        "worksheet_eventos_lote": str(cfg.get("worksheet_eventos_lote") or ABA_EVENTOS_LOTE).strip(),
        "client_email": client_email,
        "configurado": bool(id_planilha and credenciais_ok),
        "erro_configuracao": erro_configuracao,
    }


def google_configurado(secrets: Any) -> bool:
    return bool(configuracao_google(secrets)["configurado"])


def url_planilha_configurada(secrets: Any) -> str:
    cfg = configuracao_google(secrets)
    if not cfg["spreadsheet_id"]:
        return ""
    return f"https://docs.google.com/spreadsheets/d/{cfg['spreadsheet_id']}/edit"


def diagnostico_google(secrets: Any) -> dict[str, Any]:
    """Retorna o destino exato usado nas gravações, sem expor credenciais."""
    cfg = configuracao_google(secrets)
    return {
        "configurado": bool(cfg["configurado"]),
        "spreadsheet_id": str(cfg["spreadsheet_id"]),
        "spreadsheet_id_final": str(cfg["spreadsheet_id"])[-8:] if cfg["spreadsheet_id"] else "",
        "url": url_planilha_configurada(secrets),
        "aba_eventos": str(cfg["worksheet_eventos_lote"]),
        "aba_snapshot": str(cfg["worksheet_lote_pendente"]),
        "client_email": str(cfg["client_email"]),
        "erro": str(cfg.get("erro_configuracao") or ""),
    }


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
            "O Google Sheets não está configurado. Informe spreadsheet_id ou spreadsheet_url "
            "e as credenciais da conta de serviço nos Secrets do Streamlit."
        )
    chave = (cfg["spreadsheet_id"], cfg["client_email"])
    if chave not in _PLANILHAS_GOOGLE:
        cliente = _cliente_google(cfg["conta"])
        _PLANILHAS_GOOGLE[chave] = _executar_com_backoff(
            lambda: cliente.open_by_key(cfg["spreadsheet_id"]),
            operacao="abertura da planilha",
        )
    return _PLANILHAS_GOOGLE[chave]


def _letra_coluna(numero: int) -> str:
    texto = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        texto = chr(65 + resto) + texto
    return texto


def _ler_intervalo_sem_formatacao(aba: Any, intervalo: str) -> list[list[Any]]:
    """Lê valores brutos, com nova tentativa em falhas temporárias da API."""
    getter = getattr(aba, "get", None)
    if not callable(getter):
        return []

    def chamada():
        try:
            return getter(
                intervalo,
                value_render_option="UNFORMATTED_VALUE",
                date_time_render_option="SERIAL_NUMBER",
            )
        except TypeError:
            return getter(intervalo)

    valores = _executar_com_backoff(
        chamada, operacao=f"leitura do intervalo {intervalo}"
    )
    return [list(linha) for linha in (valores or [])]


def _ler_linha_sem_formatacao(aba: Any, numero_linha: int, largura: int) -> list[Any]:
    ultima = _letra_coluna(max(1, largura))
    valores = _ler_intervalo_sem_formatacao(aba, f"A{numero_linha}:{ultima}{numero_linha}")
    if valores:
        return list(valores[0])
    return list(aba.row_values(numero_linha))


def _aplicar_formato_numerico(aba: Any, cabecalho: list[str]) -> None:
    """Remove formatação de data herdada das colunas de odds/probabilidades.

    A operação é idempotente e executada uma única vez por aba/processo. Falhas
    de formatação não impedem o append; a leitura bruta ainda garante a
    conferência correta.
    """
    if not cabecalho:
        return
    row_count = max(int(getattr(aba, "row_count", 20000) or 20000), 2)
    formatos: list[dict[str, Any]] = []
    for indice, nome in enumerate(cabecalho, start=1):
        if nome not in COLUNAS_NUMERICAS_PLANILHA:
            continue
        letra = _letra_coluna(indice)
        padrao = "0" if nome in COLUNAS_INTEIRAS_PLANILHA else "0.00"
        formatos.append({
            "range": f"{letra}2:{letra}{row_count}",
            "format": {"numberFormat": {"type": "NUMBER", "pattern": padrao}},
        })
    if not formatos:
        return
    try:
        batch = getattr(aba, "batch_format", None)
        if callable(batch):
            batch(formatos)
            return
        formatter = getattr(aba, "format", None)
        if callable(formatter):
            for item in formatos:
                formatter(item["range"], item["format"])
    except Exception:
        # A persistência não deve falhar só porque a API recusou uma alteração
        # visual. A conferência usa UNFORMATTED_VALUE e continuará correta.
        return


def _obter_aba_cacheada(secrets: Any, titulo: str, colunas: list[str]):
    """Obtém a aba uma única vez por processo, sem ler linhas ou cabeçalhos em cada gravação."""
    cfg = configuracao_google(secrets)
    chave = (cfg["spreadsheet_id"], cfg["client_email"], str(titulo))
    if chave in _ABAS_GOOGLE:
        return _ABAS_GOOGLE[chave]

    planilha = _abrir_planilha(secrets)
    try:
        aba = _executar_com_backoff(
            lambda: planilha.worksheet(str(titulo)),
            operacao=f"abertura da aba {titulo}",
        )
    except Exception as exc:
        # Só cria quando a aba realmente não existe. A planilha antiga já possui as abas principais.
        if "not found" not in str(exc).lower() and "não encontr" not in str(exc).lower():
            try:
                from gspread.exceptions import WorksheetNotFound
                if not isinstance(exc, WorksheetNotFound):
                    raise
            except ImportError:
                raise
        aba = _executar_com_backoff(
            lambda: planilha.add_worksheet(
                title=str(titulo), rows=20000, cols=max(80, len(colunas) + 5)
            ),
            operacao=f"criação da aba {titulo}",
        )
        _executar_com_backoff(
            lambda: aba.append_row(colunas, value_input_option="RAW"),
            operacao=f"criação do cabeçalho de {titulo}",
        )

    if chave not in _CABECALHOS_SINCRONIZADOS:
        cabecalho = _executar_com_backoff(
            lambda: aba.row_values(1), operacao=f"leitura do cabeçalho de {titulo}"
        )
        if not cabecalho:
            _executar_com_backoff(
                lambda: aba.append_row(colunas, value_input_option="RAW"),
                operacao=f"gravação do cabeçalho de {titulo}",
            )
            cabecalho = list(colunas)
        elif cabecalho != colunas:
            # Preserva as colunas antigas e acrescenta somente as ausentes à direita.
            atualizado = list(cabecalho)
            for coluna in colunas:
                if coluna not in atualizado:
                    atualizado.append(coluna)
            if atualizado != cabecalho:
                ultima = _letra_coluna(len(atualizado))
                _executar_com_backoff(
                    lambda: aba.update(
                        f"A1:{ultima}1", [atualizado], value_input_option="RAW"
                    ),
                    operacao=f"atualização do cabeçalho de {titulo}",
                )
                cabecalho = atualizado
        _CABECALHOS_ATUAIS[chave] = list(cabecalho)
        _CABECALHOS_SINCRONIZADOS.add(chave)

    if chave not in _FORMATOS_NUMERICOS_SINCRONIZADOS:
        _aplicar_formato_numerico(aba, _CABECALHOS_ATUAIS.get(chave, list(colunas)))
        _FORMATOS_NUMERICOS_SINCRONIZADOS.add(chave)

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
    """Acrescenta, relê o intervalo gravado e só então confirma sucesso.

    O nome foi mantido por compatibilidade. A verificação pós-gravação usa
    faz uma leitura curta de verificação após cada append. Um HTTP 200 sem a
    linha correta na planilha não é considerado salvamento.
    """
    normalizados = _normalizar(registros, colunas)
    if not normalizados:
        return 0

    cfg = configuracao_google(secrets)
    if not cfg["configurado"]:
        raise RuntimeError(cfg.get("erro_configuracao") or "Google Sheets não configurado.")
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

    # Deduplicação remota por identificador. Isso evita repetir linhas que já
    # foram anexadas pelo Google quando uma versão anterior acusou falso erro
    # de conferência por causa da máscara de data. Lê apenas a coluna do ID,
    # não a aba inteira.
    if campos_chave and campos_chave[0] in cabecalho_real:
        coluna_id = cabecalho_real.index(campos_chave[0]) + 1
        ids_remotos = {
            str(valor).strip()
            for valor in _executar_com_backoff(
                lambda: list(aba.col_values(coluna_id)),
                operacao=f"leitura dos IDs em {titulo}",
            )[1:]
            if str(valor).strip()
        }
        filtradas: list[dict[str, Any]] = []
        filtradas_chaves: list[tuple[str, ...]] = []
        for registro, chave in zip(novas, novas_chaves):
            if str(registro.get(campos_chave[0], "")).strip() in ids_remotos:
                conhecidas.add(chave)
                continue
            filtradas.append(registro)
            filtradas_chaves.append(chave)
        novas, novas_chaves = filtradas, filtradas_chaves
        if not novas:
            return 0

    campo_busca = campos_chave[0]
    if campo_busca not in cabecalho_real:
        raise RuntimeError(f"Coluna de confirmação ausente: {campo_busca!r}.")
    idx_busca = cabecalho_real.index(campo_busca)
    linhas = [[registro.get(coluna, "") for coluna in cabecalho_real] for registro in novas]
    linhas_por_id = [
        (str(registro.get(campo_busca, "")).strip(), linha)
        for registro, linha in zip(novas, linhas)
    ]
    row_by_id, _ = _append_rows_idempotente(
        aba,
        linhas_por_id,
        coluna_id=idx_busca + 1,
        operacao=f"inclusão em lote em {titulo}",
    )
    valores_lidos = _batch_get_linhas_sem_formatacao(
        aba,
        [
            f"A{row_by_id[identifier]}:{_letra_coluna(len(cabecalho_real))}{row_by_id[identifier]}"
            for identifier, _ in linhas_por_id
        ],
    )

    divergencias: list[str] = []
    for indice, (esperado, valores) in enumerate(zip(novas, valores_lidos), start=1):
        valores = list(valores) + [""] * max(0, len(cabecalho_real) - len(valores))
        real = dict(zip(cabecalho_real, valores))
        for campo in campos_chave:
            if not _celula_equivalente(esperado.get(campo, ""), real.get(campo, "")):
                divergencias.append(
                    f"linha {indice}, {campo}: enviado={esperado.get(campo, '')!r}; "
                    f"lido={real.get(campo, '')!r}"
                )
        # Cotação e probabilidades são campos críticos para a auditoria. Quando
        # existirem no esquema, também são comparadas numericamente.
        for campo in (
            "Cotação", "Probabilidade operacional %", "Probabilidade Poisson %",
            "Probabilidade empírica %", "Probabilidade de mercado ajustada %",
            "Valor esperado %", "Probabilidade conservadora %",
            "Valor esperado conservador %",
        ):
            if campo in esperado and not _celula_equivalente(
                esperado.get(campo, ""), real.get(campo, ""), numerico=True
            ):
                divergencias.append(
                    f"linha {indice}, {campo}: enviado={esperado.get(campo, '')!r}; "
                    f"lido={real.get(campo, '')!r}"
                )
    if divergencias:
        raise RuntimeError(
            f"A gravação em {titulo!r} não passou na leitura de conferência: "
            + " | ".join(divergencias[:20])
        )

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

def criar_registros_cotacoes_digitadas(
    jogo: dict[str, Any],
    *,
    bankroll: float,
    interface_version: str,
    core_api_version: str,
    model_version: str,
    core_name: str,
    app_name: str,
) -> list[dict[str, Any]]:
    """Converte as odds digitadas em linhas auditáveis antes da análise.

    Os IDs são os mesmos usados pelo motor após a análise. Assim, ``salvar_cotacoes``
    atualiza as linhas existentes com probabilidades e classificação em vez de criar
    duplicatas.
    """
    home = str(jogo.get("Mandante", "") or "")
    away = str(jogo.get("Visitante", "") or "")
    bookmaker = str(jogo.get("Casa de apostas", "") or "PIXBET")
    markets = [
        (
            "1X2", "Resultado final 1X2",
            [("H", home, jogo.get("Odd mandante")),
             ("D", "Empate", jogo.get("Odd empate")),
             ("A", away, jogo.get("Odd visitante"))],
        ),
        (
            "OU25", "Total de gols 2,5",
            [("O25", "Mais de 2,5 gols", jogo.get("Odd mais de 2,5")),
             ("U25", "Menos de 2,5 gols", jogo.get("Odd menos de 2,5"))],
        ),
        (
            "BTTS", "Ambas marcam",
            [("BTTS_Y", "Ambas marcam — Sim", jogo.get("Odd ambas marcam — Sim")),
             ("BTTS_N", "Ambas marcam — Não", jogo.get("Odd ambas marcam — Não"))],
        ),
    ]
    registered = agora_brasilia()
    records: list[dict[str, Any]] = []
    for market_code, market_name, selections in markets:
        valid = [(side, selection, _valor_float_ou_none(odd)) for side, selection, odd in selections]
        valid = [(side, selection, odd) for side, selection, odd in valid if odd is not None]
        if not valid:
            continue
        total_implied = sum(1.0 / float(odd) for _, _, odd in valid)
        market_complete = len(valid) == len(selections)
        for side, selection, odd in valid:
            row = SimpleNamespace(
                MatchID=(
                    f"{str(jogo.get('Código da liga', '') or '')}|"
                    f"{str(jogo.get('Data', '') or '')}|{home}|{away}"
                ),
                Market=market_code,
                Side=side,
                Odd=float(odd),
                Bookmaker=bookmaker,
            )
            record = {column: "" for column in COLUNAS_COTACOES}
            record.update({
                "ID Coleta": identificador_registro(row),
                "Registrado em": registered,
                "Casa de apostas": bookmaker,
                "Liga": str(jogo.get("Liga", "") or ""),
                "Jogo": f"{home} x {away}",
                "Mandante": home,
                "Visitante": away,
                "Data do jogo": (
                    pd.to_datetime(str(jogo.get("Data", "") or ""), errors="coerce").strftime("%d/%m/%Y")
                    if not pd.isna(pd.to_datetime(str(jogo.get("Data", "") or ""), errors="coerce"))
                    else str(jogo.get("Data", "") or "")
                ),
                "Hora do jogo": str(jogo.get("Hora", "") or ""),
                "Mercado": market_name,
                "Seleção": selection,
                "Cotação": float(odd),
                "Grupo do mercado": market_code,
                "Mercado completo": "Sim" if market_complete else "Não",
                "Probabilidade implícita bruta %": 100.0 / float(odd),
                "Margem do mercado %": (total_implied - 1.0) * 100.0 if market_complete else "",
                "Probabilidade ajustada sem margem %": (
                    ((1.0 / float(odd)) / total_implied) * 100.0 if market_complete and total_implied > 0 else ""
                ),
                "Banca no momento": float(bankroll),
                "Perfil": str(core_name),
                "Origem": str(app_name),
                "Observação": (
                    "Cotação digitada e confirmada antes da análise. "
                    "Probabilidades e contexto serão atualizados na mesma linha após ANALISAR TODO O LOTE."
                ),
                "Versão da interface": str(interface_version),
                "Versão da API do núcleo": str(core_api_version),
                "Versão do modelo": str(model_version),
            })
            records.append(record)
    return records


def _codigo_http_erro(exc: Exception) -> int | None:
    """Extrai o código HTTP de gspread/APIError sem depender da classe concreta."""
    for objeto in (exc, getattr(exc, "response", None)):
        if objeto is None:
            continue
        for atributo in ("status_code", "status", "code"):
            valor = getattr(objeto, atributo, None)
            try:
                if valor is not None:
                    return int(valor)
            except (TypeError, ValueError):
                pass
    match = re.search(r"(?:APIError:\s*)?\[(\d{3})\]", str(exc or ""))
    return int(match.group(1)) if match else None


def _erro_de_quota(exc: Exception) -> bool:
    texto = str(exc or "").lower()
    return _codigo_http_erro(exc) == 429 or any(
        trecho in texto
        for trecho in (
            "quota exceeded", "resource_exhausted", "too many requests",
            "write requests per minute", "read requests per minute",
        )
    )


def _erro_transitorio(exc: Exception) -> bool:
    """Erros em que uma nova tentativa é apropriada para operações idempotentes."""
    codigo = _codigo_http_erro(exc)
    if codigo in {408, 425, 429, 500, 502, 503, 504}:
        return True
    texto = str(exc or "").lower()
    return any(
        trecho in texto
        for trecho in (
            "service unavailable", "temporarily unavailable", "backend error",
            "internal server error", "gateway timeout", "bad gateway",
            "connection reset", "connection aborted", "connection error",
            "read timed out", "timed out", "timeout", "resource_exhausted",
            "too many requests", "quota exceeded",
        )
    )


def _esperar_backoff(tentativa: int) -> None:
    atrasos = (0.8, 1.6, 3.2, 6.4)
    base = atrasos[min(tentativa, len(atrasos) - 1)]
    # Pequeno jitter evita que vários usuários repitam a chamada no mesmo instante.
    time.sleep(base + random.uniform(0.0, min(0.4, base * 0.20)))


def _executar_com_backoff(func, *, operacao: str, tentativas: int = 5):
    """Repete operações seguras em 429 e falhas temporárias 5xx/timeout.

    Esta função deve envolver apenas leituras ou escritas idempotentes. Append
    usa ``_append_rows_idempotente`` porque um 503 pode ocorrer após o Google já
    ter gravado as linhas, tornando uma repetição cega capaz de duplicá-las.
    """
    ultimo: Exception | None = None
    for tentativa in range(tentativas):
        try:
            return func()
        except Exception as exc:  # gspread.APIError sem dependência rígida
            ultimo = exc
            if not _erro_transitorio(exc) or tentativa >= tentativas - 1:
                raise
            _esperar_backoff(tentativa)
    raise RuntimeError(f"Falha em {operacao}: {ultimo}")


def _localizar_ids_na_coluna(
    aba: Any, coluna_id: int, identificadores: Iterable[str], *, operacao: str
) -> dict[str, int]:
    desejados = {str(item).strip() for item in identificadores if str(item).strip()}
    if not desejados:
        return {}
    valores = _executar_com_backoff(
        lambda: list(aba.col_values(coluna_id)), operacao=operacao
    )
    encontrados: dict[str, int] = {}
    for posicao in range(1, len(valores)):
        valor = str(valores[posicao]).strip()
        if valor in desejados:
            encontrados[valor] = posicao + 1
    return encontrados


def _append_rows_idempotente(
    aba: Any,
    linhas_por_id: list[tuple[str, list[Any]]],
    *,
    coluna_id: int,
    operacao: str,
    tentativas: int = 5,
) -> tuple[dict[str, int], Any]:
    """Faz append sem duplicar quando a resposta falha depois da gravação.

    Em um HTTP 503 não é possível saber, apenas pela exceção, se o Google gravou
    ou não. Antes de repetir, a função procura os mesmos IDs. Se todos já estiverem
    presentes, considera a operação concluída; se apenas parte estiver presente,
    anexa somente os ausentes.
    """
    pendentes = [(str(identifier).strip(), list(row)) for identifier, row in linhas_por_id]
    if not pendentes:
        return {}, None
    if any(not identifier for identifier, _ in pendentes):
        raise ValueError("Append idempotente exige identificadores não vazios.")

    encontrados: dict[str, int] = {}
    ultima_resposta: Any = None
    ultimo_erro: Exception | None = None

    for tentativa in range(tentativas):
        ids_tentativa = [identifier for identifier, _ in pendentes]
        try:
            ultima_resposta = aba.append_rows(
                [row for _, row in pendentes], value_input_option="RAW"
            )
            intervalo = _intervalo_linhas_append(ultima_resposta)
            if intervalo and intervalo[1] - intervalo[0] + 1 == len(pendentes):
                for offset, (identifier, _) in enumerate(pendentes):
                    encontrados[identifier] = intervalo[0] + offset
                return encontrados, ultima_resposta

            localizados = _localizar_ids_na_coluna(
                aba, coluna_id, ids_tentativa, operacao=f"confirmação após {operacao}"
            )
            encontrados.update(localizados)
            faltantes = [item for item in pendentes if item[0] not in encontrados]
            if not faltantes:
                return encontrados, ultima_resposta
            pendentes = faltantes
            ultimo_erro = RuntimeError(
                f"{len(pendentes)} registro(s) não foram localizados após {operacao}."
            )
        except Exception as exc:
            ultimo_erro = exc
            if not _erro_transitorio(exc):
                raise
            # A requisição pode ter sido aplicada apesar do 503. Confere antes de repetir.
            localizados = _localizar_ids_na_coluna(
                aba, coluna_id, ids_tentativa, operacao=f"verificação de {operacao} após erro temporário"
            )
            encontrados.update(localizados)
            pendentes = [item for item in pendentes if item[0] not in encontrados]
            if not pendentes:
                return encontrados, ultima_resposta

        if tentativa >= tentativas - 1:
            break
        _esperar_backoff(tentativa)

    raise RuntimeError(
        f"Falha temporária persistente em {operacao}; "
        f"{len(pendentes)} registro(s) não foram confirmados. Detalhe: {ultimo_erro}"
    ) from ultimo_erro


def _intervalo_linhas_append(resposta: Any) -> tuple[int, int] | None:
    if not isinstance(resposta, dict):
        return None
    intervalo = str(
        resposta.get("updates", {}).get("updatedRange")
        or resposta.get("updatedRange")
        or ""
    )
    match = re.search(r"![A-Z]+(\d+):[A-Z]+(\d+)$", intervalo)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _batch_get_linhas_sem_formatacao(
    aba: Any, intervalos: list[str]
) -> list[list[Any]]:
    if not intervalos:
        return []
    batch_get = getattr(aba, "batch_get", None)
    if callable(batch_get):
        try:
            blocos = _executar_com_backoff(
                lambda: batch_get(
                    intervalos,
                    value_render_option="UNFORMATTED_VALUE",
                    date_time_render_option="SERIAL_NUMBER",
                ),
                operacao="leitura em lote",
            )
        except TypeError:
            blocos = _executar_com_backoff(
                lambda: batch_get(intervalos), operacao="leitura em lote"
            )
        saida: list[list[Any]] = []
        for bloco in blocos or []:
            if bloco and isinstance(bloco, list) and isinstance(bloco[0], list):
                saida.append(list(bloco[0]))
            else:
                saida.append([])
        return saida
    # Compatibilidade com mocks/implementações antigas. Em produção (gspread 6)
    # o caminho acima é usado e consome uma única requisição de leitura.
    saida: list[list[Any]] = []
    for intervalo in intervalos:
        match = re.fullmatch(r"[A-Z]+(\d+):[A-Z]+(\d+)", intervalo)
        if match and match.group(1) == match.group(2):
            saida.append(_ler_linha_sem_formatacao(aba, int(match.group(1)), 1))
        else:
            bloco = _ler_intervalo_sem_formatacao(aba, intervalo)
            saida.append(list(bloco[0]) if bloco else [])
    return saida


def _salvar_cotacoes_upsert(secrets: Any, registros: Iterable[dict[str, Any]]) -> int:
    """Insere/atualiza cotações com no máximo duas gravações por lote.

    A implementação anterior executava ``worksheet.update`` dentro de um loop.
    Em um lote de 210 seleções isso gerava até 210 solicitações de escrita e
    inevitavelmente ultrapassava a cota de 60 gravações/minuto por usuário.
    Agora todas as linhas existentes são atualizadas por ``batch_update`` em uma
    única chamada e todas as novas são anexadas por um único ``append_rows``.
    A conferência também é feita por um único ``batch_get``.
    """
    normalizados = _normalizar(registros, COLUNAS_COTACOES)
    if not normalizados:
        return 0
    cfg = configuracao_google(secrets)
    if not cfg["configurado"]:
        raise RuntimeError(cfg.get("erro_configuracao") or "Google Sheets não configurado.")
    titulo = cfg["worksheet_catalogo"]
    aba = _obter_aba_cacheada(secrets, titulo, COLUNAS_COTACOES)
    worksheet_key = (cfg["spreadsheet_id"], cfg["client_email"], str(titulo))
    header = _CABECALHOS_ATUAIS.get(worksheet_key, list(COLUNAS_COTACOES))
    if "ID Coleta" not in header:
        raise RuntimeError("A aba catalogo_odds não contém a coluna 'ID Coleta'.")

    id_index = header.index("ID Coleta")
    remote_ids = _executar_com_backoff(
        lambda: list(aba.col_values(id_index + 1)),
        operacao="leitura dos IDs de cotações",
    )
    row_by_id: dict[str, int] = {}
    for position in range(1, len(remote_ids)):
        value = str(remote_ids[position]).strip()
        if value:
            row_by_id[value] = position + 1

    last_col = _letra_coluna(len(header))
    updates: list[dict[str, Any]] = []
    appends: list[dict[str, Any]] = []
    record_by_id: dict[str, dict[str, Any]] = {}
    for record in normalizados:
        identifier = str(record.get("ID Coleta", "")).strip()
        if not identifier:
            raise RuntimeError("Cotação sem ID Coleta não pode ser persistida.")
        record_by_id[identifier] = record
        line = [record.get(column, "") for column in header]
        existing_row = row_by_id.get(identifier)
        if existing_row is None:
            appends.append(record)
        else:
            updates.append({
                "range": f"A{existing_row}:{last_col}{existing_row}",
                "values": [line],
            })

    # Uma única solicitação de escrita para todas as linhas já existentes.
    if updates:
        batch_update = getattr(aba, "batch_update", None)
        if callable(batch_update):
            _executar_com_backoff(
                lambda: batch_update(updates, value_input_option="RAW"),
                operacao="atualização em lote de cotações",
            )
        else:
            # Compatibilidade exclusiva com mocks e clientes antigos. Em produção,
            # requirements.txt fixa gspread>=6 e usa uma única chamada batch_update.
            for item in updates:
                aba.update(item["range"], item["values"], value_input_option="RAW")

    # Uma única inclusão lógica para todas as linhas novas. Em erro 503,
    # confirma os IDs antes de repetir para não duplicar cotações.
    if appends:
        linhas_por_id = [
            (
                str(record.get("ID Coleta", "")).strip(),
                [record.get(column, "") for column in header],
            )
            for record in appends
        ]
        linhas_confirmadas, _ = _append_rows_idempotente(
            aba,
            linhas_por_id,
            coluna_id=id_index + 1,
            operacao="inclusão em lote de cotações",
        )
        row_by_id.update(linhas_confirmadas)

    faltantes = [identifier for identifier in record_by_id if identifier not in row_by_id]
    if faltantes:
        raise RuntimeError(
            "A API respondeu, mas estes IDs não foram localizados na planilha: "
            + ", ".join(faltantes[:10])
        )

    # Uma única solicitação de leitura para conferir todas as linhas afetadas.
    ordered_ids = list(record_by_id)
    ranges = [
        f"A{row_by_id[identifier]}:{last_col}{row_by_id[identifier]}"
        for identifier in ordered_ids
    ]
    values_by_range = _batch_get_linhas_sem_formatacao(aba, ranges)
    if len(values_by_range) != len(ordered_ids):
        raise RuntimeError(
            f"A conferência em lote retornou {len(values_by_range)} linha(s), "
            f"mas eram esperadas {len(ordered_ids)}."
        )

    numeric_columns = set(COLUNAS_NUMERICAS_PLANILHA)
    divergencias: list[str] = []
    for identifier, values in zip(ordered_ids, values_by_range):
        values = list(values) + [""] * max(0, len(header) - len(values))
        real = dict(zip(header, values))
        record = record_by_id[identifier]
        for column in COLUNAS_COTACOES:
            expected = record.get(column, "")
            if not _celula_equivalente(
                expected, real.get(column, ""), numerico=column in numeric_columns
            ):
                divergencias.append(
                    f"{identifier}, {column}: enviado={expected!r}; "
                    f"lido={real.get(column, '')!r}"
                )
                if len(divergencias) >= 20:
                    break
        if len(divergencias) >= 20:
            break
    if divergencias:
        raise RuntimeError(
            "As cotações não passaram na conferência em lote: "
            + " | ".join(divergencias)
        )

    cache_key = (cfg["spreadsheet_id"], cfg["client_email"], str(titulo))
    known = _CHAVES_GRAVADAS_NO_PROCESSO.setdefault(cache_key, set())
    known.update((identifier,) for identifier in ordered_ids)
    return len(normalizados)

def salvar_cotacoes(secrets: Any, registros: Iterable[dict[str, Any]]) -> int:
    return _salvar_cotacoes_upsert(secrets, registros)


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
        ["ID Análise"],
    )


def _carregar_aba(secrets: Any, titulo: str, colunas: list[str]) -> pd.DataFrame:
    aba, cabecalho = _garantir_aba_para_leitura(secrets, titulo, colunas)
    valores = []
    try:
        getter_all = getattr(aba, "get_all_values", None)
        if callable(getter_all):
            try:
                valores = getter_all(value_render_option="UNFORMATTED_VALUE")
            except TypeError:
                valores = getter_all()
    except Exception:
        valores = []
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



def _valor_float_ou_none(valor: Any) -> float | None:
    texto = str(valor or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def _numero_linha_append(resposta: Any) -> int | None:
    """Extrai a linha confirmada pela API Sheets a partir de updatedRange."""
    if not isinstance(resposta, dict):
        return None
    intervalo = str(
        resposta.get("updates", {}).get("updatedRange")
        or resposta.get("updatedRange")
        or ""
    )
    match = re.search(r"!(?:[^!]*?)(\d+):(?:[^!]*?)(\d+)$", intervalo)
    if match and match.group(1) == match.group(2):
        return int(match.group(1))
    match = re.search(r"!(?:[A-Z]+)(\d+):(?:[A-Z]+)(\d+)$", intervalo)
    if match and match.group(1) == match.group(2):
        return int(match.group(1))
    return None


def _numero_equivalente(a: Any, b: Any) -> bool:
    def conv(v: Any) -> float | None:
        texto = str(v if v is not None else "").strip().replace(".", "").replace(",", ".")
        # Se já veio no formato Python 1.77, a remoção acima produziria 177.
        original = str(v if v is not None else "").strip()
        if "," not in original and original.count(".") <= 1:
            texto = original
        if not texto:
            return None
        try:
            return float(texto)
        except (TypeError, ValueError):
            return None
    na, nb = conv(a), conv(b)
    if na is None or nb is None:
        return na is nb
    return abs(na - nb) <= 1e-9


def _celula_equivalente(esperado: Any, real: Any, *, numerico: bool = False) -> bool:
    if esperado is None or (not isinstance(esperado, (dict, list, tuple)) and pd.isna(esperado)):
        esperado = ""
    if real is None:
        real = ""
    if numerico:
        if str(esperado).strip() == "" and str(real).strip() == "":
            return True
        return _numero_equivalente(esperado, real)

    # Proteção adicional para respostas UNFORMATTED_VALUE do Google Sheets:
    # números equivalentes podem mudar apenas de tipo (17.0 -> 17).
    esperado_numero = isinstance(esperado, Real) and not isinstance(esperado, bool)
    real_numero = isinstance(real, Real) and not isinstance(real, bool)
    if esperado_numero and real_numero:
        return _numero_equivalente(esperado, real)
    return str(esperado).strip() == str(real).strip()


def _ler_linha_por_id(
    aba: Any,
    cabecalho: list[str],
    coluna_id: str,
    valor_id: str,
    linha_sugerida: int | None,
) -> tuple[int, list[Any]]:
    """Lê de volta exatamente a linha gravada; não confia só no HTTP 200."""
    if linha_sugerida and linha_sugerida >= 2:
        valores = _ler_linha_sem_formatacao(aba, linha_sugerida, len(cabecalho))
        if coluna_id in cabecalho:
            idx = cabecalho.index(coluna_id)
            if idx < len(valores) and str(valores[idx]).strip() == str(valor_id).strip():
                return linha_sugerida, valores

    if coluna_id not in cabecalho:
        raise RuntimeError(f"A aba não contém a coluna de verificação {coluna_id!r}.")
    coluna = cabecalho.index(coluna_id) + 1
    valores_id = list(aba.col_values(coluna))
    for posicao in range(len(valores_id) - 1, 0, -1):
        if str(valores_id[posicao]).strip() == str(valor_id).strip():
            numero_linha = posicao + 1
            return numero_linha, _ler_linha_sem_formatacao(aba, numero_linha, len(cabecalho))
    raise RuntimeError(
        f"A API respondeu ao append, mas o ID {valor_id!r} não foi encontrado na aba após a gravação."
    )


def registrar_evento_lote(
    secrets: Any,
    *,
    tipo_evento: str,
    jogo: dict[str, Any] | None = None,
    interface_version: str = "",
    lote_id: str = "principal",
) -> dict[str, Any]:
    """Grava e relê uma ação do lote antes de confirmar sucesso ao app.

    Versões anteriores confiavam apenas no retorno do append. Nesta versão,
    a linha é lida novamente e os identificadores e todas as cotações são
    comparados campo a campo. O formulário só pode ser limpo depois disso.
    """
    tipo = str(tipo_evento or "").strip().upper()
    if tipo not in {"UPSERT", "DELETE", "CLEAR"}:
        raise ValueError(f"Tipo de evento do lote inválido: {tipo_evento!r}")
    dados = dict(jogo or {})
    if tipo in {"UPSERT", "DELETE"} and not str(dados.get("ID", "")).strip():
        raise ValueError("O evento do lote exige o ID da partida.")

    cfg = configuracao_google(secrets)
    if not cfg["configurado"]:
        raise RuntimeError(
            cfg.get("erro_configuracao")
            or "O Google Sheets não está configurado com um spreadsheet_id explícito."
        )

    registrado_em = datetime.now(ZoneInfo("America/Fortaleza")).replace(microsecond=0).isoformat()
    registro = {
        "ID Evento": f"{registrado_em}-{uuid4().hex}",
        "ID do lote": str(lote_id or "principal"),
        "Tipo de evento": tipo,
        "Registrado em": registrado_em,
        "ID da partida": str(dados.get("ID", "") or ""),
        "Data": str(dados.get("Data", "") or ""),
        "Hora": str(dados.get("Hora", "") or ""),
        "Código da liga": str(dados.get("Código da liga", "") or ""),
        "Liga": str(dados.get("Liga", "") or ""),
        "Mandante": str(dados.get("Mandante", "") or ""),
        "Visitante": str(dados.get("Visitante", "") or ""),
        "Casa de apostas": str(dados.get("Casa de apostas", "") or "PIXBET"),
        "Odd mandante": dados.get("Odd mandante", ""),
        "Odd empate": dados.get("Odd empate", ""),
        "Odd visitante": dados.get("Odd visitante", ""),
        "Odd mais de 2,5": dados.get("Odd mais de 2,5", ""),
        "Odd menos de 2,5": dados.get("Odd menos de 2,5", ""),
        "Odd ambas marcam — Sim": dados.get("Odd ambas marcam — Sim", ""),
        "Odd ambas marcam — Não": dados.get("Odd ambas marcam — Não", ""),
        "Versão da interface": str(interface_version),
        "Origem": "Autosave verificado Tex Statistics",
    }
    normalizado = _normalizar([registro], COLUNAS_EVENTOS_LOTE)[0]
    aba = _obter_aba_cacheada(secrets, cfg["worksheet_eventos_lote"], COLUNAS_EVENTOS_LOTE)
    chave_aba = (cfg["spreadsheet_id"], cfg["client_email"], cfg["worksheet_eventos_lote"])
    cabecalho = _CABECALHOS_ATUAIS.get(chave_aba, list(COLUNAS_EVENTOS_LOTE))
    linha = [normalizado.get(coluna, "") for coluna in cabecalho]

    if "ID Evento" not in cabecalho:
        raise RuntimeError("A aba entrada_jogos não contém a coluna 'ID Evento'.")
    id_index = cabecalho.index("ID Evento")
    linhas_confirmadas, _ = _append_rows_idempotente(
        aba,
        [(str(registro["ID Evento"]), linha)],
        coluna_id=id_index + 1,
        operacao="inclusão da partida",
    )
    numero_linha = linhas_confirmadas[str(registro["ID Evento"])]
    valores_reais = _ler_linha_sem_formatacao(aba, numero_linha, len(cabecalho))
    valores_reais += [""] * max(0, len(cabecalho) - len(valores_reais))
    real = dict(zip(cabecalho, valores_reais))

    campos_texto = [
        "ID Evento", "ID do lote", "Tipo de evento", "ID da partida", "Data", "Hora",
        "Código da liga", "Liga", "Mandante", "Visitante", "Casa de apostas",
        "Versão da interface",
    ]
    campos_numericos = [
        "Odd mandante", "Odd empate", "Odd visitante", "Odd mais de 2,5",
        "Odd menos de 2,5", "Odd ambas marcam — Sim", "Odd ambas marcam — Não",
    ]
    divergencias: list[str] = []
    for campo in campos_texto:
        if not _celula_equivalente(normalizado.get(campo, ""), real.get(campo, "")):
            divergencias.append(
                f"{campo}: enviado={normalizado.get(campo, '')!r}; lido={real.get(campo, '')!r}"
            )
    for campo in campos_numericos:
        if not _celula_equivalente(
            normalizado.get(campo, ""), real.get(campo, ""), numerico=True
        ):
            divergencias.append(
                f"{campo}: enviado={normalizado.get(campo, '')!r}; lido={real.get(campo, '')!r}"
            )
    if divergencias:
        raise RuntimeError(
            "A linha apareceu na planilha, mas a leitura de conferência encontrou diferenças: "
            + " | ".join(divergencias)
        )

    url_base = url_planilha_configurada(secrets)
    worksheet_id = getattr(aba, "id", None)
    url_linha = (
        f"{url_base}#gid={worksheet_id}&range=A{numero_linha}"
        if worksheet_id is not None else url_base
    )
    return {
        **registro,
        "Planilha ID": cfg["spreadsheet_id"],
        "Planilha URL": url_linha,
        "Aba": cfg["worksheet_eventos_lote"],
        "Linha": numero_linha,
        "Cotações verificadas": {
            campo: real.get(campo, "") for campo in campos_numericos
        },
        "Verificação": "GRAVADO E RELIDO",
    }


def registrar_eventos_lote(
    secrets: Any,
    jogos: Iterable[dict[str, Any]],
    *,
    interface_version: str = "",
    lote_id: str = "principal",
) -> dict[str, Any]:
    """Grava e confere vários UPSERTs do lote com uma única escrita e uma leitura.

    A função preserva o mesmo formato append-only de ``registrar_evento_lote``,
    mas evita uma requisição por partida ao importar uma rodada inteira.
    """
    itens = [dict(jogo or {}) for jogo in jogos]
    if not itens:
        return {
            "Eventos confirmados": 0,
            "Primeira linha": None,
            "Última linha": None,
            "Verificação": "NENHUM EVENTO",
        }
    sem_id = [str(item.get("Mandante", "") or "?") for item in itens if not str(item.get("ID", "")).strip()]
    if sem_id:
        raise ValueError("Todos os eventos em lote exigem ID de partida. Sem ID: " + ", ".join(sem_id[:5]))

    cfg = configuracao_google(secrets)
    if not cfg["configurado"]:
        raise RuntimeError(
            cfg.get("erro_configuracao")
            or "O Google Sheets não está configurado com um spreadsheet_id explícito."
        )

    registrado_em = datetime.now(ZoneInfo("America/Fortaleza")).replace(microsecond=0).isoformat()
    registros: list[dict[str, Any]] = []
    for posicao, dados in enumerate(itens):
        registros.append({
            "ID Evento": f"{registrado_em}-{posicao:04d}-{uuid4().hex}",
            "ID do lote": str(lote_id or "principal"),
            "Tipo de evento": "UPSERT",
            "Registrado em": registrado_em,
            "ID da partida": str(dados.get("ID", "") or ""),
            "Data": str(dados.get("Data", "") or ""),
            "Hora": str(dados.get("Hora", "") or ""),
            "Código da liga": str(dados.get("Código da liga", "") or ""),
            "Liga": str(dados.get("Liga", "") or ""),
            "Mandante": str(dados.get("Mandante", "") or ""),
            "Visitante": str(dados.get("Visitante", "") or ""),
            "Casa de apostas": str(dados.get("Casa de apostas", "") or "PIXBET"),
            "Odd mandante": dados.get("Odd mandante", ""),
            "Odd empate": dados.get("Odd empate", ""),
            "Odd visitante": dados.get("Odd visitante", ""),
            "Odd mais de 2,5": dados.get("Odd mais de 2,5", ""),
            "Odd menos de 2,5": dados.get("Odd menos de 2,5", ""),
            "Odd ambas marcam — Sim": dados.get("Odd ambas marcam — Sim", ""),
            "Odd ambas marcam — Não": dados.get("Odd ambas marcam — Não", ""),
            "Versão da interface": str(interface_version),
            "Origem": "Importação em lote verificada Tex Statistics",
        })

    normalizados = _normalizar(registros, COLUNAS_EVENTOS_LOTE)
    aba = _obter_aba_cacheada(secrets, cfg["worksheet_eventos_lote"], COLUNAS_EVENTOS_LOTE)
    chave_aba = (cfg["spreadsheet_id"], cfg["client_email"], cfg["worksheet_eventos_lote"])
    cabecalho = _CABECALHOS_ATUAIS.get(chave_aba, list(COLUNAS_EVENTOS_LOTE))
    linhas = [[registro.get(coluna, "") for coluna in cabecalho] for registro in normalizados]

    if "ID Evento" not in cabecalho:
        raise RuntimeError("A aba entrada_jogos não contém a coluna 'ID Evento'.")
    id_index = cabecalho.index("ID Evento")
    row_by_event, _ = _append_rows_idempotente(
        aba,
        [
            (str(registro["ID Evento"]), linha)
            for registro, linha in zip(normalizados, linhas)
        ],
        coluna_id=id_index + 1,
        operacao="inclusão em lote de partidas",
    )

    missing = [str(registro["ID Evento"]) for registro in normalizados if str(registro["ID Evento"]) not in row_by_event]
    if missing:
        raise RuntimeError(
            "A API respondeu, mas estes eventos não foram localizados na planilha: "
            + ", ".join(missing[:10])
        )

    last_col = _letra_coluna(len(cabecalho))
    ordered_ids = [str(registro["ID Evento"]) for registro in normalizados]
    ranges = [f"A{row_by_event[event_id]}:{last_col}{row_by_event[event_id]}" for event_id in ordered_ids]
    values_by_range = _batch_get_linhas_sem_formatacao(aba, ranges)
    if len(values_by_range) != len(normalizados):
        raise RuntimeError(
            f"A conferência em lote retornou {len(values_by_range)} linha(s), "
            f"mas eram esperadas {len(normalizados)}."
        )

    numeric_fields = [
        "Odd mandante", "Odd empate", "Odd visitante", "Odd mais de 2,5",
        "Odd menos de 2,5", "Odd ambas marcam — Sim", "Odd ambas marcam — Não",
    ]
    text_fields = [
        "ID Evento", "ID do lote", "Tipo de evento", "ID da partida", "Data", "Hora",
        "Código da liga", "Liga", "Mandante", "Visitante", "Casa de apostas",
        "Versão da interface",
    ]
    divergencias: list[str] = []
    for registro, values in zip(normalizados, values_by_range):
        values = list(values) + [""] * max(0, len(cabecalho) - len(values))
        real = dict(zip(cabecalho, values))
        for field in text_fields:
            if not _celula_equivalente(registro.get(field, ""), real.get(field, "")):
                divergencias.append(f"{registro['ID Evento']}, {field}")
        for field in numeric_fields:
            if not _celula_equivalente(registro.get(field, ""), real.get(field, ""), numerico=True):
                divergencias.append(f"{registro['ID Evento']}, {field}")
        if len(divergencias) >= 20:
            break
    if divergencias:
        raise RuntimeError(
            "As partidas importadas apareceram na planilha, mas a conferência encontrou diferenças: "
            + ", ".join(divergencias)
        )

    rows = [row_by_event[event_id] for event_id in ordered_ids]
    url_base = url_planilha_configurada(secrets)
    worksheet_id = getattr(aba, "id", None)
    first_row, last_row = min(rows), max(rows)
    url_range = (
        f"{url_base}#gid={worksheet_id}&range=A{first_row}:A{last_row}"
        if worksheet_id is not None else url_base
    )
    return {
        "Eventos confirmados": len(normalizados),
        "Primeira linha": first_row,
        "Última linha": last_row,
        "Aba": cfg["worksheet_eventos_lote"],
        "Planilha URL": url_range,
        "Verificação": "GRAVADO E RELIDO EM LOTE",
        "IDs dos eventos": ordered_ids,
    }

def _jogo_de_evento(registro: dict[str, Any]) -> dict[str, Any]:
    return {
        "ID": str(registro.get("ID da partida", "") or ""),
        "Data": str(registro.get("Data", "") or ""),
        "Hora": str(registro.get("Hora", "") or ""),
        "Código da liga": str(registro.get("Código da liga", "") or ""),
        "Liga": str(registro.get("Liga", "") or ""),
        "Mandante": str(registro.get("Mandante", "") or ""),
        "Visitante": str(registro.get("Visitante", "") or ""),
        "Casa de apostas": str(registro.get("Casa de apostas", "") or "PIXBET"),
        "Odd mandante": _valor_float_ou_none(registro.get("Odd mandante")),
        "Odd empate": _valor_float_ou_none(registro.get("Odd empate")),
        "Odd visitante": _valor_float_ou_none(registro.get("Odd visitante")),
        "Odd mais de 2,5": _valor_float_ou_none(registro.get("Odd mais de 2,5")),
        "Odd menos de 2,5": _valor_float_ou_none(registro.get("Odd menos de 2,5")),
        "Odd ambas marcam — Sim": _valor_float_ou_none(registro.get("Odd ambas marcam — Sim")),
        "Odd ambas marcam — Não": _valor_float_ou_none(registro.get("Odd ambas marcam — Não")),
    }


def carregar_lote_por_eventos(secrets: Any, *, lote_id: str = "principal") -> dict[str, Any]:
    """Reconstrói o lote a partir do histórico append-only."""
    cfg = configuracao_google(secrets)
    frame = _carregar_aba(secrets, cfg["worksheet_eventos_lote"], COLUNAS_EVENTOS_LOTE)
    if frame.empty:
        return {"ID do lote": str(lote_id), "Salvo em": "", "Jogos": [], "Eventos encontrados": 0}

    estado: dict[str, dict[str, Any]] = {}
    ordem: list[str] = []
    eventos_encontrados = 0
    salvo_em = ""
    versao = ""
    for registro in frame.to_dict(orient="records"):
        if str(registro.get("ID do lote", "principal") or "principal").strip() != str(lote_id):
            continue
        tipo = str(registro.get("Tipo de evento", "") or "").strip().upper()
        if tipo not in {"UPSERT", "DELETE", "CLEAR"}:
            continue
        eventos_encontrados += 1
        salvo_em = str(registro.get("Registrado em", "") or salvo_em)
        versao = str(registro.get("Versão da interface", "") or versao)
        if tipo == "CLEAR":
            estado.clear()
            ordem.clear()
            continue
        partida_id = str(registro.get("ID da partida", "") or "").strip()
        if not partida_id:
            continue
        if tipo == "DELETE":
            estado.pop(partida_id, None)
            ordem = [item for item in ordem if item != partida_id]
            continue
        jogo = _jogo_de_evento(registro)
        if partida_id not in estado:
            ordem.append(partida_id)
        estado[partida_id] = jogo

    return {
        "ID do lote": str(lote_id),
        "Salvo em": salvo_em,
        "Versão da interface": versao,
        "Jogos": [estado[item] for item in ordem if item in estado],
        "Eventos encontrados": eventos_encontrados,
        "Origem": "entrada_jogos",
    }


def salvar_lote_pendente(
    secrets: Any,
    jogos: Iterable[dict[str, Any]],
    *,
    interface_version: str = "",
    lote_id: str = "principal",
) -> dict[str, Any]:
    """Persiste o lote bruto imediatamente em uma aba própria do Google Sheets.

    A aba mantém um único snapshot atual em A2:F2. Isso evita depender do
    ``st.session_state`` e permite restaurar o lote após rerun, queda da sessão
    ou reinicialização do Streamlit.
    """
    cfg = configuracao_google(secrets)
    jogos_normalizados = [dict(item) for item in jogos]
    payload = json.dumps(jogos_normalizados, ensure_ascii=False, separators=(",", ":"))
    # Uma célula do Google Sheets suporta aproximadamente 50 mil caracteres.
    if len(payload) > 45000:
        raise ValueError(
            "O lote ficou grande demais para o snapshot automático da planilha. "
            "Divida-o em lotes menores antes de continuar."
        )
    salvo_em = datetime.now(ZoneInfo("America/Fortaleza")).replace(microsecond=0).isoformat()
    registro = {
        "ID do lote": str(lote_id or "principal"),
        "Salvo em": salvo_em,
        "Quantidade de partidas": len(jogos_normalizados),
        "Lote JSON": payload,
        "Versão da interface": str(interface_version),
        "Origem": "Autosave Tex Statistics",
    }
    aba = _obter_aba_cacheada(secrets, cfg["worksheet_lote_pendente"], COLUNAS_LOTE_PENDENTE)
    chave = (cfg["spreadsheet_id"], cfg["client_email"], cfg["worksheet_lote_pendente"])
    cabecalho = _CABECALHOS_ATUAIS.get(chave, list(COLUNAS_LOTE_PENDENTE))
    linha = [registro.get(coluna, "") for coluna in cabecalho]
    ultima = _letra_coluna(len(cabecalho))
    _executar_com_backoff(
        lambda: aba.update(f"A2:{ultima}2", [linha], value_input_option="RAW"),
        operacao="atualização do snapshot do lote",
    )
    return registro


def carregar_lote_pendente(secrets: Any, *, lote_id: str = "principal") -> dict[str, Any]:
    """Carrega o lote durável; prioriza o log append-only e usa o snapshot como fallback."""
    eventos = carregar_lote_por_eventos(secrets, lote_id=lote_id)
    if int(eventos.get("Eventos encontrados", 0) or 0) > 0:
        return eventos

    cfg = configuracao_google(secrets)
    aba = _obter_aba_cacheada(secrets, cfg["worksheet_lote_pendente"], COLUNAS_LOTE_PENDENTE)
    chave = (cfg["spreadsheet_id"], cfg["client_email"], cfg["worksheet_lote_pendente"])
    cabecalho = _CABECALHOS_ATUAIS.get(chave) or aba.row_values(1)
    valores = aba.row_values(2)
    if not valores:
        return {"ID do lote": str(lote_id), "Salvo em": "", "Jogos": [], "Eventos encontrados": 0}
    valores = valores + [""] * max(0, len(cabecalho) - len(valores))
    registro = {coluna: valores[i] if i < len(valores) else "" for i, coluna in enumerate(cabecalho)}
    if str(registro.get("ID do lote", "principal")).strip() not in {"", str(lote_id)}:
        return {"ID do lote": str(lote_id), "Salvo em": "", "Jogos": [], "Eventos encontrados": 0}
    bruto = str(registro.get("Lote JSON", "") or "").strip()
    if not bruto:
        jogos: list[dict[str, Any]] = []
    else:
        try:
            parsed = json.loads(bruto)
        except json.JSONDecodeError as exc:
            raise RuntimeError("O snapshot do lote na planilha está corrompido.") from exc
        if not isinstance(parsed, list):
            raise RuntimeError("O snapshot do lote na planilha não contém uma lista de partidas.")
        jogos = [dict(item) for item in parsed if isinstance(item, dict)]
    return {
        "ID do lote": str(registro.get("ID do lote", lote_id) or lote_id),
        "Salvo em": str(registro.get("Salvo em", "") or ""),
        "Versão da interface": str(registro.get("Versão da interface", "") or ""),
        "Jogos": jogos,
        "Eventos encontrados": 0,
        "Origem": "lote_pendente",
    }


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
