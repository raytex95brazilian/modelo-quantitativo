from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Iterable
from uuid import uuid4
import json
import re

import pandas as pd

STORAGE_API_VERSION = "28.1.5.11"

from tex_v28_finance import COLUNAS_APOSTAS, liquidar_registro

# Planilha histórica que já era usada pelas versões anteriores.
PLANILHA_ANTIGA_ID = "1exfvkvNC_7W-0Nk51ZOue5Do7LtR9sS-8x5R0Gf_zMo"
PLANILHA_ANTIGA_URL = f"https://docs.google.com/spreadsheets/d/{PLANILHA_ANTIGA_ID}/edit"

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
    "Banca depois (R$)",
}

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

    Versões anteriores podiam usar PLANILHA_ANTIGA_ID como fallback. Isso
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
        _PLANILHAS_GOOGLE[chave] = _cliente_google(cfg["conta"]).open_by_key(cfg["spreadsheet_id"])
    return _PLANILHAS_GOOGLE[chave]


def _letra_coluna(numero: int) -> str:
    texto = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        texto = chr(65 + resto) + texto
    return texto


def _ler_intervalo_sem_formatacao(aba: Any, intervalo: str) -> list[list[Any]]:
    """Lê valores brutos, ignorando a máscara visual da célula.

    O Google Sheets pode exibir um número como data quando a coluna herdou
    formatação antiga. A validação deve comparar o valor armazenado, não o texto
    formatado mostrado na grade.
    """
    getter = getattr(aba, "get", None)
    if callable(getter):
        try:
            valores = getter(
                intervalo,
                value_render_option="UNFORMATTED_VALUE",
                date_time_render_option="SERIAL_NUMBER",
            )
        except TypeError:
            valores = getter(intervalo)
        return [list(linha) for linha in (valores or [])]
    return []


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
        formatos.append({
            "range": f"{letra}2:{letra}{row_count}",
            "format": {"numberFormat": {"type": "NUMBER", "pattern": "0.00"}},
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

    O nome foi mantido por compatibilidade, mas a V28.1.5.11 deliberadamente
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
            for valor in list(aba.col_values(coluna_id))[1:]
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

    linhas = [[registro.get(coluna, "") for coluna in cabecalho_real] for registro in novas]
    resposta = aba.append_rows(linhas, value_input_option="RAW")

    intervalo = ""
    if isinstance(resposta, dict):
        intervalo = str(
            resposta.get("updates", {}).get("updatedRange")
            or resposta.get("updatedRange")
            or ""
        )
    valores_lidos: list[list[Any]] = []
    if intervalo and "!" in intervalo:
        a1 = intervalo.split("!", 1)[1]
        valores_lidos = _ler_intervalo_sem_formatacao(aba, a1)

    # Fallback controlado para mocks ou respostas sem updatedRange: localiza cada
    # chave na planilha e lê apenas as linhas correspondentes.
    if len(valores_lidos) != len(novas):
        valores_lidos = []
        campo_busca = campos_chave[0]
        if campo_busca not in cabecalho_real:
            raise RuntimeError(f"Coluna de confirmação ausente: {campo_busca!r}.")
        idx_busca = cabecalho_real.index(campo_busca)
        ids = list(aba.col_values(idx_busca + 1))
        for registro in novas:
            alvo = str(registro.get(campo_busca, "")).strip()
            linha_numero = None
            for posicao in range(len(ids) - 1, 0, -1):
                if str(ids[posicao]).strip() == alvo:
                    linha_numero = posicao + 1
                    break
            if linha_numero is None:
                raise RuntimeError(
                    f"O registro {alvo!r} não foi encontrado em {titulo!r} após o append."
                )
            valores_lidos.append(_ler_linha_sem_formatacao(aba, linha_numero, len(cabecalho_real)))

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

def salvar_cotacoes(secrets: Any, registros: Iterable[dict[str, Any]]) -> int:
    cfg = configuracao_google(secrets)
    return _acrescentar_sem_leitura(
        secrets,
        cfg["worksheet_catalogo"],
        COLUNAS_COTACOES,
        registros,
        ["ID Coleta"],
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

    A V28.1.5.11 apenas confiava no retorno do append. A partir da V28.1.5.11,
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

    resposta = aba.append_rows([linha], value_input_option="RAW")
    linha_api = _numero_linha_append(resposta)
    numero_linha, valores_reais = _ler_linha_por_id(
        aba, cabecalho, "ID Evento", registro["ID Evento"], linha_api
    )
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
    aba.update(f"A2:{ultima}2", [linha], value_input_option="RAW")
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
