from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any, Iterable

import pandas as pd

ABA_COTACOES = "COTACOES_V25"
ABA_ANALISES = "ANALISES_V25"

# As colunas antigas são mantidas para que o mesmo arquivo da Planilha Google
# continue mostrando todo o histórico já gravado. As novas linhas usam as
# colunas "Cotação informada".
COLUNAS_COTACOES = [
    "Identificador da análise", "Salvo em Brasília", "Data da análise", "Horário da partida (Brasília)",
    "Banca informada (R$)", "Percentual da unidade (%)", "Valor da unidade (R$)", "Liga", "Temporada",
    "Mandante", "Visitante", "Fonte das cotações",
    "Cotação informada — vitória do mandante", "Cotação informada — empate", "Cotação informada — vitória do visitante",
    "Cotação informada — mais de 2,5 gols", "Cotação informada — menos de 2,5 gols",
    "Cotação informada — ambas as equipes marcam: sim", "Cotação informada — ambas as equipes marcam: não",
    "Posição do mandante", "Posição do visitante", "Pontos do mandante", "Pontos do visitante",
    "Pontos por jogo do mandante", "Pontos por jogo do visitante",
    "Gols por jogo do mandante", "Gols por jogo do visitante",
    "Gols sofridos por jogo do mandante", "Gols sofridos por jogo do visitante",
    "Resultado — gols do mandante", "Resultado — gols do visitante", "Resultado confirmado", "Observações",
]

COLUNAS_ANALISES = [
    "Identificador da análise", "Salvo em Brasília", "Data da análise", "Horário da partida (Brasília)",
    "Banca informada (R$)", "Percentual da unidade (%)", "Valor da unidade (R$)", "Liga", "Temporada",
    "Mandante", "Visitante", "Fonte das cotações", "Situação", "Mercado",
    "Código da seleção", "Seleção", "Motivo da decisão",
    "Probabilidade do mercado", "Probabilidade esportiva", "Probabilidade mínima exigida pela cotação",
    "Diferença entre modelo e mercado", "Valor esperado esportivo", "Valor histórico no preço atual",
    "Cotação informada", "Amostra histórica",
    "Acerto histórico", "Retorno histórico", "Gols esperados do mandante", "Gols esperados do visitante",
    "Posição do mandante", "Posição do visitante", "Pontos do mandante", "Pontos do visitante",
    "Pontos por jogo do mandante", "Pontos por jogo do visitante",
    "Gols por jogo do mandante", "Gols por jogo do visitante",
    "Gols sofridos por jogo do mandante", "Gols sofridos por jogo do visitante",
    "Resultado — gols do mandante", "Resultado — gols do visitante", "Resultado confirmado",
    "Seleção vencedora", "Lucro em unidades", "Observações",
]


def agora_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def agora_brasilia() -> str:
    fuso = ZoneInfo("America/Sao_Paulo")
    return datetime.now(fuso).replace(microsecond=0).strftime("%d/%m/%Y %H:%M:%S")


def _cliente_google(informacoes_conta: dict[str, Any]):
    import gspread
    from google.oauth2.service_account import Credentials

    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credenciais = Credentials.from_service_account_info(dict(informacoes_conta), scopes=escopos)
    return gspread.authorize(credenciais)


def configuracao_google(secrets: Any) -> tuple[dict[str, Any] | None, str | None]:
    try:
        conta = dict(secrets["gcp_service_account"])
        id_planilha = str(secrets["google_sheet"]["spreadsheet_id"]).strip()
        if conta and id_planilha:
            return conta, id_planilha
    except Exception:
        pass
    return None, None


def google_configurado(secrets: Any) -> bool:
    conta, id_planilha = configuracao_google(secrets)
    return bool(conta and id_planilha)


def _abrir_planilha(secrets: Any):
    conta, id_planilha = configuracao_google(secrets)
    if not conta or not id_planilha:
        raise RuntimeError("A Planilha Google não está configurada nos segredos do aplicativo.")
    return _cliente_google(conta).open_by_key(id_planilha)


def _letra_coluna(numero: int) -> str:
    texto = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        texto = chr(65 + resto) + texto
    return texto


def _garantir_aba(secrets: Any, titulo: str, colunas: list[str]):
    planilha = _abrir_planilha(secrets)
    try:
        aba = planilha.worksheet(titulo)
    except Exception:
        aba = planilha.add_worksheet(title=titulo, rows=10000, cols=max(70, len(colunas) + 5))

    cabecalho = aba.row_values(1)
    if not cabecalho:
        aba.append_row(colunas, value_input_option="RAW")
        cabecalho = list(colunas)
    else:
        # Migração segura e cumulativa: nunca limpa a aba e nunca remove colunas antigas.
        faltantes = [coluna for coluna in colunas if coluna not in cabecalho]
        if faltantes:
            cabecalho = cabecalho + faltantes
            ultima_coluna = _letra_coluna(len(cabecalho))
            aba.update(f"A1:{ultima_coluna}1", [cabecalho], value_input_option="RAW")
    return aba, cabecalho


def _normalizar(registros: Iterable[dict[str, Any]], colunas: list[str]) -> list[dict[str, Any]]:
    saida: list[dict[str, Any]] = []
    for registro in registros:
        linha: dict[str, Any] = {}
        for coluna in colunas:
            valor = registro.get(coluna, "")
            if valor is None or (not isinstance(valor, (dict, list, tuple)) and pd.isna(valor)):
                valor = ""
            linha[coluna] = valor
        saida.append(linha)
    return saida


def _chaves_existentes(aba, cabecalho: list[str], campos: list[str]) -> set[tuple[str, ...]]:
    valores = aba.get_all_values()
    if len(valores) <= 1:
        return set()
    indices = {campo: cabecalho.index(campo) for campo in campos if campo in cabecalho}
    if len(indices) != len(campos):
        return set()
    existentes: set[tuple[str, ...]] = set()
    for linha in valores[1:]:
        linha = linha + [""] * (len(cabecalho) - len(linha))
        existentes.add(tuple(str(linha[indices[campo]]).strip() for campo in campos))
    return existentes


def _acrescentar_sem_sobrescrever(
    secrets: Any,
    titulo: str,
    colunas: list[str],
    registros: Iterable[dict[str, Any]],
    campos_chave: list[str],
) -> int:
    normalizados = _normalizar(registros, colunas)
    if not normalizados:
        return 0
    aba, cabecalho = _garantir_aba(secrets, titulo, colunas)
    existentes = _chaves_existentes(aba, cabecalho, campos_chave)
    novas_linhas = []
    for registro in normalizados:
        chave = tuple(str(registro.get(campo, "")).strip() for campo in campos_chave)
        if chave in existentes:
            continue
        novas_linhas.append([registro.get(coluna, "") for coluna in cabecalho])
        existentes.add(chave)
    if novas_linhas:
        aba.append_rows(novas_linhas, value_input_option="USER_ENTERED")
    return len(novas_linhas)


def salvar_cotacao(secrets: Any, registro: dict[str, Any]) -> int:
    return _acrescentar_sem_sobrescrever(
        secrets, ABA_COTACOES, COLUNAS_COTACOES, [registro], ["Identificador da análise"]
    )


def salvar_analises(secrets: Any, registros: Iterable[dict[str, Any]]) -> int:
    return _acrescentar_sem_sobrescrever(
        secrets,
        ABA_ANALISES,
        COLUNAS_ANALISES,
        registros,
        ["Identificador da análise", "Mercado", "Código da seleção"],
    )


def _carregar_aba(secrets: Any, titulo: str, colunas: list[str]) -> pd.DataFrame:
    aba, cabecalho = _garantir_aba(secrets, titulo, colunas)
    valores = aba.get_all_values()
    if len(valores) <= 1:
        return pd.DataFrame(columns=cabecalho)
    frame = pd.DataFrame(valores[1:], columns=cabecalho)
    # Mantém também as colunas antigas da mesma planilha para que o histórico
    # anterior continue visível na interface.
    ordem = colunas + [coluna for coluna in cabecalho if coluna not in colunas]
    for coluna in ordem:
        if coluna not in frame.columns:
            frame[coluna] = ""
    return frame[ordem]


def carregar_cotacoes(secrets: Any) -> pd.DataFrame:
    return _carregar_aba(secrets, ABA_COTACOES, COLUNAS_COTACOES)


def carregar_analises(secrets: Any) -> pd.DataFrame:
    return _carregar_aba(secrets, ABA_ANALISES, COLUNAS_ANALISES)


def confirmar_resultado(
    secrets: Any,
    identificador: str,
    gols_mandante: int,
    gols_visitante: int,
    observacoes: str = "",
) -> int:
    total_atualizacoes = 0
    for titulo, colunas, possui_selecao in (
        (ABA_COTACOES, COLUNAS_COTACOES, False),
        (ABA_ANALISES, COLUNAS_ANALISES, True),
    ):
        aba, cabecalho = _garantir_aba(secrets, titulo, colunas)
        valores = aba.get_all_values()
        if not valores:
            continue
        indices = {nome: posicao for posicao, nome in enumerate(cabecalho)}
        for numero_linha, linha in enumerate(valores[1:], start=2):
            linha = linha + [""] * (len(cabecalho) - len(linha))
            if str(linha[indices["Identificador da análise"]]).strip() != str(identificador).strip():
                continue
            alteracoes: dict[str, Any] = {
                "Resultado — gols do mandante": gols_mandante,
                "Resultado — gols do visitante": gols_visitante,
                "Resultado confirmado": "SIM",
                "Observações": observacoes,
            }
            if possui_selecao:
                codigo = str(linha[indices["Código da seleção"]]).strip()
                total_gols = gols_mandante + gols_visitante
                venceu = {
                    "H": gols_mandante > gols_visitante,
                    "D": gols_mandante == gols_visitante,
                    "A": gols_mandante < gols_visitante,
                    "O25": total_gols >= 3,
                    "U25": total_gols <= 2,
                }.get(codigo, False)
                coluna_odd = "Cotação informada" if "Cotação informada" in indices else ("Odd informada" if "Odd informada" in indices else "Odd conservadora")
                try:
                    odd = float(str(linha[indices[coluna_odd]]).replace(",", ".") or 0.0)
                except (ValueError, KeyError):
                    odd = 0.0
                alteracoes["Seleção vencedora"] = "SIM" if venceu else "NÃO"
                alteracoes["Lucro em unidades"] = odd - 1.0 if venceu else -1.0
            for coluna, valor in alteracoes.items():
                if coluna in indices:
                    aba.update_cell(numero_linha, indices[coluna] + 1, valor)
            total_atualizacoes += 1
    return total_atualizacoes
