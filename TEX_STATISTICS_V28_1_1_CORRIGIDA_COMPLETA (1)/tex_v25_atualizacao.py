from __future__ import annotations

"""Coleta direta dos CSVs do Football-Data para a Tex Statistics v.25.

Este módulo é autônomo: não importa funções internas de ``tex_v25_core``.
Isso evita incompatibilidade entre versões durante a atualização pelo GitHub.
"""

import csv
import io
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Any, Iterable, Optional

import requests

VERSAO_COLETOR = "football-data-direto-2026-07-23-r2"

LEAGUES = {
    "BRA": "Brasileirão Série A",
    "ARG": "Argentina - Primera Division",
    "USA": "EUA - MLS",
    "MEX": "México - Liga MX",
    "JPN": "Japão - J1 League",
    "CHN": "China - Super League",
    "SWE": "Suécia - Allsvenskan",
    "NOR": "Noruega - Eliteserien",
    "FIN": "Finlândia - Veikkausliiga",
    "IRL": "Irlanda - Premier Division",
    "E0": "Inglaterra - Premier League",
    "E1": "Inglaterra - Championship",
    "SP1": "Espanha - La Liga",
    "SP2": "Espanha - Segunda Divisão",
    "I1": "Itália - Série A",
    "I2": "Itália - Série B",
    "D1": "Alemanha - Bundesliga",
    "D2": "Alemanha - 2. Bundesliga",
    "F1": "França - Ligue 1",
    "P1": "Portugal - Primeira Liga",
    "N1": "Holanda - Eredivisie",
    "B1": "Bélgica - Pro League",
    "T1": "Turquia - Super Lig",
    "G1": "Grécia - Super League",
}

ANNUAL_CODES = {"BRA", "ARG", "USA", "MEX", "JPN", "CHN", "SWE", "NOR", "FIN", "IRL"}

URLS_ANUAIS = {
    "BRA": "https://www.football-data.co.uk/new/BRA.csv",
    "ARG": "https://www.football-data.co.uk/new/ARG.csv",
    "USA": "https://www.football-data.co.uk/new/USA.csv",
    "MEX": "https://www.football-data.co.uk/new/MEX.csv",
    "JPN": "https://www.football-data.co.uk/new/JPN.csv",
    "CHN": "https://www.football-data.co.uk/new/CHN.csv",
    "SWE": "https://www.football-data.co.uk/new/SWE.csv",
    "NOR": "https://www.football-data.co.uk/new/NOR.csv",
    "FIN": "https://www.football-data.co.uk/new/FIN.csv",
    "IRL": "https://www.football-data.co.uk/new/IRL.csv",
}

CODIGOS_EUROPEUS = (
    "E0", "E1", "SP1", "SP2", "I1", "I2", "D1", "D2",
    "F1", "P1", "N1", "B1", "T1", "G1",
)

# Atual + cinco anteriores: suficiente para aquecimento e quatro temporadas de validação.
TEMPORADAS_EUROPEIAS_CARREGADAS = 6


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin1", errors="replace")


def _number(value: Any) -> Optional[float]:
    if value is None:
        return None
    texto = str(value).strip().replace(",", ".")
    if not texto:
        return None
    try:
        numero = float(texto)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def _first_number(row: dict[str, Any], names: Iterable[str]) -> Optional[float]:
    for name in names:
        numero = _number(row.get(name))
        if numero is not None:
            return numero
    return None


def _parse_date(value: Any) -> Optional[date]:
    texto = str(value or "").strip()
    if not texto:
        return None
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _season_start(label: Any, fallback: int | None = None) -> Optional[int]:
    texto = str(label or "").strip()
    if texto:
        partes = "".join(caractere if caractere.isdigit() else " " for caractere in texto).split()
        if partes:
            ano = int(partes[0])
            return ano + 2000 if ano < 100 else ano
    return fallback


def codigo_temporada(inicio: int) -> str:
    return f"{inicio % 100:02d}{(inicio + 1) % 100:02d}"


def inicio_temporada_europeia_atual(referencia: date | None = None) -> int:
    referencia = referencia or date.today()
    return referencia.year if referencia.month >= 7 else referencia.year - 1


def temporadas_europeias_para_baixar(referencia: date | None = None) -> list[int]:
    atual = inicio_temporada_europeia_atual(referencia)
    return list(range(atual - (TEMPORADAS_EUROPEIAS_CARREGADAS - 1), atual + 1))


def _parece_csv(texto: str) -> bool:
    primeira_linha = texto.lstrip().splitlines()[0] if texto.strip() else ""
    primeira_minuscula = primeira_linha.lower()
    return "," in primeira_linha and not primeira_minuscula.startswith("<!doctype") and "<html" not in primeira_minuscula


def _normalizar_csv(texto: str, codigo: str, temporada_forcada: int | None = None) -> list[dict[str, Any]]:
    leitor = csv.DictReader(io.StringIO(texto))
    partidas: list[dict[str, Any]] = []

    for linha in leitor:
        if codigo in ANNUAL_CODES:
            data_jogo = _parse_date(linha.get("Date"))
            mandante = str(linha.get("Home") or "").strip()
            visitante = str(linha.get("Away") or "").strip()
            gols_mandante = _number(linha.get("HG"))
            gols_visitante = _number(linha.get("AG"))
            temporada = _season_start(linha.get("Season"), data_jogo.year if data_jogo else None)
            media_casa = _first_number(linha, ("AvgCH", "AvgH", "BbAvH"))
            media_empate = _first_number(linha, ("AvgCD", "AvgD", "BbAvD"))
            media_fora = _first_number(linha, ("AvgCA", "AvgA", "BbAvA"))
            maxima_casa = _first_number(linha, ("MaxCH", "MaxH", "BbMxH"))
            maxima_empate = _first_number(linha, ("MaxCD", "MaxD", "BbMxD"))
            maxima_fora = _first_number(linha, ("MaxCA", "MaxA", "BbMxA"))
            media_mais = _first_number(linha, ("AvgC>2.5", "Avg>2.5", "BbAv>2.5"))
            media_menos = _first_number(linha, ("AvgC<2.5", "Avg<2.5", "BbAv<2.5"))
            maxima_mais = _first_number(linha, ("MaxC>2.5", "Max>2.5", "BbMx>2.5"))
            maxima_menos = _first_number(linha, ("MaxC<2.5", "Max<2.5", "BbMx<2.5"))
        else:
            data_jogo = _parse_date(linha.get("Date"))
            mandante = str(linha.get("HomeTeam") or "").strip()
            visitante = str(linha.get("AwayTeam") or "").strip()
            gols_mandante = _number(linha.get("FTHG"))
            gols_visitante = _number(linha.get("FTAG"))
            temporada = temporada_forcada
            media_casa = _first_number(linha, ("AvgCH", "AvgH", "BbAvH"))
            media_empate = _first_number(linha, ("AvgCD", "AvgD", "BbAvD"))
            media_fora = _first_number(linha, ("AvgCA", "AvgA", "BbAvA"))
            maxima_casa = _first_number(linha, ("MaxCH", "MaxH", "BbMxH"))
            maxima_empate = _first_number(linha, ("MaxCD", "MaxD", "BbMxD"))
            maxima_fora = _first_number(linha, ("MaxCA", "MaxA", "BbMxA"))
            media_mais = _first_number(linha, ("AvgC>2.5", "Avg>2.5", "BbAv>2.5"))
            media_menos = _first_number(linha, ("AvgC<2.5", "Avg<2.5", "BbAv<2.5"))
            maxima_mais = _first_number(linha, ("MaxC>2.5", "Max>2.5", "BbMx>2.5"))
            maxima_menos = _first_number(linha, ("MaxC<2.5", "Max<2.5", "BbMx<2.5"))

        if not (
            data_jogo
            and mandante
            and visitante
            and gols_mandante is not None
            and gols_visitante is not None
            and temporada is not None
        ):
            continue

        partidas.append(
            {
                "Code": codigo,
                "League": LEAGUES[codigo],
                "Season": int(temporada),
                "DateParsed": data_jogo,
                "Date": data_jogo.strftime("%d/%m/%Y"),
                "Home": mandante,
                "Away": visitante,
                "HG": int(gols_mandante),
                "AG": int(gols_visitante),
                "AvgH": media_casa,
                "AvgD": media_empate,
                "AvgA": media_fora,
                "MaxH": maxima_casa,
                "MaxD": maxima_empate,
                "MaxA": maxima_fora,
                "AvgO25": media_mais,
                "AvgU25": media_menos,
                "MaxO25": maxima_mais,
                "MaxU25": maxima_menos,
            }
        )

    return partidas


def _baixar_url(url: str, codigo: str, temporada: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
    resposta = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "Tex-Statistics-v25/Football-Data"},
    )
    resposta.raise_for_status()
    texto = _decode(resposta.content)
    if not _parece_csv(texto):
        raise ValueError("a resposta recebida não é um CSV válido")
    partidas = _normalizar_csv(texto, codigo, temporada)
    if not partidas:
        raise ValueError("o CSV não contém partidas concluídas")
    return partidas


def _deduplicar(partidas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapa: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in partidas:
        chave = (
            item["Code"],
            item["DateParsed"],
            str(item["Home"]).casefold(),
            str(item["Away"]).casefold(),
        )
        if chave not in mapa:
            mapa[chave] = dict(item)
            continue
        combinado = dict(mapa[chave])
        for campo, valor in item.items():
            if valor is not None and valor != "":
                combinado[campo] = valor
        mapa[chave] = combinado
    return sorted(
        mapa.values(),
        key=lambda item: (item["DateParsed"], item["League"], item["Home"], item["Away"]),
    )


def _baixar_liga_anual(codigo: str) -> dict[str, Any]:
    url = URLS_ANUAIS[codigo]
    try:
        partidas = _baixar_url(url, codigo)
        return {
            "codigo": codigo,
            "liga": LEAGUES[codigo],
            "urls": [url],
            "partidas": partidas,
            "ultima_data": max(item["DateParsed"] for item in partidas),
            "quantidade": len(partidas),
            "arquivos_ok": 1,
            "arquivos_tentados": 1,
            "situacao": "ATUALIZADA",
            "erro": "",
        }
    except Exception as erro:
        return {
            "codigo": codigo,
            "liga": LEAGUES[codigo],
            "urls": [url],
            "partidas": [],
            "ultima_data": None,
            "quantidade": 0,
            "arquivos_ok": 0,
            "arquivos_tentados": 1,
            "situacao": "FALHA",
            "erro": str(erro),
        }


def _baixar_liga_europeia(codigo: str, referencia: date | None = None) -> dict[str, Any]:
    partidas: list[dict[str, Any]] = []
    urls: list[str] = []
    erros: list[str] = []
    sucessos = 0
    temporadas = temporadas_europeias_para_baixar(referencia)

    for inicio in temporadas:
        etiqueta = codigo_temporada(inicio)
        url = f"https://www.football-data.co.uk/mmz4281/{etiqueta}/{codigo}.csv"
        urls.append(url)
        try:
            partidas.extend(_baixar_url(url, codigo, inicio))
            sucessos += 1
        except Exception as erro:
            erros.append(f"{etiqueta}: {erro}")

    partidas = _deduplicar(partidas)
    situacao = "FALHA" if sucessos == 0 else ("PARCIAL" if sucessos < len(temporadas) else "ATUALIZADA")
    return {
        "codigo": codigo,
        "liga": LEAGUES[codigo],
        "urls": urls,
        "partidas": partidas,
        "ultima_data": max((item["DateParsed"] for item in partidas), default=None),
        "quantidade": len(partidas),
        "arquivos_ok": sucessos,
        "arquivos_tentados": len(temporadas),
        "situacao": situacao,
        "erro": " | ".join(erros),
    }


def _baixar_liga(codigo: str, referencia: date | None = None) -> dict[str, Any]:
    if codigo in URLS_ANUAIS:
        return _baixar_liga_anual(codigo)
    return _baixar_liga_europeia(codigo, referencia)


def carregar_base_football_data(
    referencia: date | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Baixa as 24 ligas diretamente do Football-Data, sem abrir ZIP local."""
    partidas_totais: list[dict[str, Any]] = []
    relatorio: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        tarefas = {
            executor.submit(_baixar_liga, codigo, referencia): codigo
            for codigo in LEAGUES
        }
        for tarefa in as_completed(tarefas):
            resposta = tarefa.result()
            partidas_totais.extend(resposta.pop("partidas"))
            relatorio.append(resposta)

    partidas_totais = _deduplicar(partidas_totais)
    relatorio.sort(key=lambda item: item["liga"])

    if not partidas_totais:
        detalhes = " | ".join(
            item.get("erro", "") for item in relatorio if item.get("erro")
        )
        raise RuntimeError(
            f"O Football-Data não retornou nenhuma partida concluída. {detalhes}".strip()
        )

    return partidas_totais, relatorio




def carregar_base_com_atualizacao(zip_historico=None, referencia: date | None = None):
    """Compatibilidade com apps anteriores; mantém a consulta direta sem ZIP."""
    partidas, relatorio = carregar_base_football_data(referencia)
    return partidas, relatorio, 0


__all__ = [
    "VERSAO_COLETOR",
    "carregar_base_football_data",
    "carregar_base_com_atualizacao",
]
