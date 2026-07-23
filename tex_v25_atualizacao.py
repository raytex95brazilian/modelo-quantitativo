from __future__ import annotations

import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any

import requests

from tex_v25_core import (
    ANNUAL_CODES,
    LEAGUES,
    _decode,
    _first_number,
    _number,
    _parse_date,
    _season_start,
    normalize_zip,
)

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

CODIGOS_EUROPEUS = [
    "E0", "E1", "SP1", "SP2", "I1", "I2", "D1", "D2",
    "F1", "P1", "N1", "B1", "T1", "G1",
]


def codigo_temporada(inicio: int) -> str:
    return f"{inicio % 100:02d}{(inicio + 1) % 100:02d}"


def temporadas_europeias_para_tentar(referencia: date | None = None) -> list[int]:
    referencia = referencia or date.today()
    inicio_atual = referencia.year if referencia.month >= 7 else referencia.year - 1
    # Tenta a temporada atual e a imediatamente anterior. No começo de julho,
    # alguns arquivos da nova temporada ainda podem não existir.
    return [inicio_atual, inicio_atual - 1]


def _parece_csv(texto: str) -> bool:
    primeira = texto.lstrip().splitlines()[0] if texto.strip() else ""
    return "," in primeira and not primeira.lower().startswith("<!doctype") and "<html" not in primeira.lower()


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
            temporada = _season_start(linha.get("Season"))
            media_casa = _first_number(linha, ["AvgCH"])
            media_empate = _first_number(linha, ["AvgCD"])
            media_fora = _first_number(linha, ["AvgCA"])
            maxima_casa = _first_number(linha, ["MaxCH"])
            maxima_empate = _first_number(linha, ["MaxCD"])
            maxima_fora = _first_number(linha, ["MaxCA"])
            media_mais = media_menos = maxima_mais = maxima_menos = None
        else:
            data_jogo = _parse_date(linha.get("Date"))
            mandante = str(linha.get("HomeTeam") or "").strip()
            visitante = str(linha.get("AwayTeam") or "").strip()
            gols_mandante = _number(linha.get("FTHG"))
            gols_visitante = _number(linha.get("FTAG"))
            temporada = temporada_forcada
            media_casa = _first_number(linha, ["AvgCH", "AvgH", "BbAvH"])
            media_empate = _first_number(linha, ["AvgCD", "AvgD", "BbAvD"])
            media_fora = _first_number(linha, ["AvgCA", "AvgA", "BbAvA"])
            maxima_casa = _first_number(linha, ["MaxCH", "MaxH", "BbMxH"])
            maxima_empate = _first_number(linha, ["MaxCD", "MaxD", "BbMxD"])
            maxima_fora = _first_number(linha, ["MaxCA", "MaxA", "BbMxA"])
            media_mais = _first_number(linha, ["AvgC>2.5", "Avg>2.5", "BbAv>2.5"])
            media_menos = _first_number(linha, ["AvgC<2.5", "Avg<2.5", "BbAv<2.5"])
            maxima_mais = _first_number(linha, ["MaxC>2.5", "Max>2.5", "BbMx>2.5"])
            maxima_menos = _first_number(linha, ["MaxC<2.5", "Max<2.5", "BbMx<2.5"])

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


def _baixar_url(url: str, codigo: str, temporada: int | None = None, timeout: int = 20) -> dict[str, Any]:
    cabecalhos = {"User-Agent": "Tex-Statistics-v25 atualização estatística"}
    resposta = requests.get(url, timeout=timeout, headers=cabecalhos)
    resposta.raise_for_status()
    texto = _decode(resposta.content)
    if not _parece_csv(texto):
        raise ValueError("a resposta não é um arquivo CSV válido")
    partidas = _normalizar_csv(texto, codigo, temporada)
    if not partidas:
        raise ValueError("o arquivo não contém partidas concluídas")
    return {
        "codigo": codigo,
        "liga": LEAGUES[codigo],
        "url": url,
        "partidas": partidas,
        "ultima_data": max(item["DateParsed"] for item in partidas),
        "quantidade": len(partidas),
        "situacao": "ATUALIZADA",
        "erro": "",
    }


def _baixar_liga(codigo: str, referencia: date | None = None) -> dict[str, Any]:
    if codigo in URLS_ANUAIS:
        try:
            return _baixar_url(URLS_ANUAIS[codigo], codigo)
        except Exception as erro:
            return {
                "codigo": codigo,
                "liga": LEAGUES[codigo],
                "url": URLS_ANUAIS[codigo],
                "partidas": [],
                "ultima_data": None,
                "quantidade": 0,
                "situacao": "FALHA",
                "erro": str(erro),
            }

    erros: list[str] = []
    for inicio in temporadas_europeias_para_tentar(referencia):
        temporada_csv = codigo_temporada(inicio)
        url = f"https://www.football-data.co.uk/mmz4281/{temporada_csv}/{codigo}.csv"
        try:
            return _baixar_url(url, codigo, inicio)
        except Exception as erro:
            erros.append(f"{temporada_csv}: {erro}")
    return {
        "codigo": codigo,
        "liga": LEAGUES[codigo],
        "url": "",
        "partidas": [],
        "ultima_data": None,
        "quantidade": 0,
        "situacao": "FALHA",
        "erro": " | ".join(erros),
    }


def baixar_partidas_recentes(referencia: date | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resultados: list[dict[str, Any]] = []
    relatorio: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        tarefas = {executor.submit(_baixar_liga, codigo, referencia): codigo for codigo in LEAGUES}
        for tarefa in as_completed(tarefas):
            resposta = tarefa.result()
            resultados.extend(resposta.pop("partidas"))
            relatorio.append(resposta)
    resultados.sort(key=lambda item: (item["DateParsed"], item["League"], item["Home"], item["Away"]))
    relatorio.sort(key=lambda item: item["liga"])
    return resultados, relatorio


def mesclar_partidas(historico: list[dict[str, Any]], recentes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    mapa = {
        (item["Code"], item["DateParsed"], item["Home"].casefold(), item["Away"].casefold()): dict(item)
        for item in historico
    }
    quantidade_antes = len(mapa)
    for item in recentes:
        chave = (item["Code"], item["DateParsed"], item["Home"].casefold(), item["Away"].casefold())
        if chave in mapa:
            antigo = mapa[chave]
            combinado = dict(antigo)
            for campo, valor in item.items():
                if valor is not None and valor != "":
                    combinado[campo] = valor
            mapa[chave] = combinado
        else:
            mapa[chave] = dict(item)
    saida = sorted(mapa.values(), key=lambda item: (item["DateParsed"], item["League"], item["Home"], item["Away"]))
    return saida, max(0, len(mapa) - quantidade_antes)


def carregar_base_com_atualizacao(zip_historico: str | Path, referencia: date | None = None):
    historico = normalize_zip(zip_historico, include_incomplete_annual_2026=True)
    recentes, relatorio = baixar_partidas_recentes(referencia)
    combinado, novos = mesclar_partidas(historico, recentes)
    return combinado, relatorio, novos
