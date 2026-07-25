from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo
import hashlib
import json
import os

import numpy as np
import pandas as pd

FUSO = ZoneInfo("America/Fortaleza")

COLUNAS_APOSTAS = [
    "ID Aposta", "ID Análise", "Registrado em", "Versão da interface", "Versão da API do núcleo", "Versão do modelo",
    "Liga", "Código da liga", "Data do jogo", "Hora do jogo", "Jogo", "Mandante", "Visitante",
    "Grupo do mercado", "Mercado", "Código da seleção", "Seleção", "Casa de apostas",
    "Cotação", "Cotação após desconto", "Probabilidade do modelo %",
    "Probabilidade conservadora %", "Valor esperado conservador %", "Casos semelhantes",
    "Confiança da amostra", "Estabilidade %", "Entrada (R$)", "Banca de referência (R$)",
    "Situação da liquidação", "Gols do mandante", "Gols do visitante", "Resultado da aposta",
    "Retorno bruto (R$)", "Lucro ou prejuízo (R$)", "Liquidado em", "Observações",
]

SITUACAO_PENDENTE = "PENDENTE"
SITUACAO_LIQUIDADA = "LIQUIDADA"


def agora_brasilia() -> str:
    return datetime.now(FUSO).replace(microsecond=0).strftime("%d/%m/%Y %H:%M:%S")


def _texto(value: Any) -> str:
    if value is None or (not isinstance(value, (dict, list, tuple)) and pd.isna(value)):
        return ""
    return str(value).strip()


def _numero(value: Any, default: float = 0.0) -> float:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return default
    text = str(value).strip().replace("R$", "").replace("%", "").replace(" ", "")
    if not text:
        return default
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def identificador_registro(row: Any) -> str:
    """Identificador estável compartilhado por cotação, análise e aposta.

    O vínculo usa partida, mercado, seleção, cotação e casa de apostas. Assim,
    as três camadas podem ser auditadas sem depender do identificador temporário
    da sessão do Streamlit.
    """
    payload = {
        "partida": _texto(getattr(row, "MatchID", "")),
        "mercado": _texto(getattr(row, "Market", "")),
        "selecao": _texto(getattr(row, "Side", "")),
        "cotacao": round(_numero(getattr(row, "Odd", 0.0)), 4),
        "casa": _texto(getattr(row, "Bookmaker", "")),
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]
    return f"TEX-{digest.upper()}"


def identificador_aposta(row: Any) -> str:
    """Compatibilidade com o nome usado nas primeiras versões financeiras."""
    return identificador_registro(row)


def criar_registros_apostas(
    entries: pd.DataFrame,
    bankroll: float,
    interface_version: str,
    core_api_version: str,
    model_version: str,
) -> list[dict[str, Any]]:
    if entries is None or entries.empty:
        return []
    registered = agora_brasilia()
    records: list[dict[str, Any]] = []
    for row in entries.itertuples(index=False):
        record = {column: "" for column in COLUNAS_APOSTAS}
        record.update(
            {
                "ID Aposta": identificador_registro(row),
                "ID Análise": identificador_registro(row),
                "Registrado em": registered,
                "Versão da interface": interface_version,
                "Versão da API do núcleo": core_api_version,
                "Versão do modelo": model_version,
                "Liga": row.League,
                "Código da liga": row.Code,
                "Data do jogo": pd.Timestamp(row.DateParsed).strftime("%d/%m/%Y"),
                "Hora do jogo": row.Time,
                "Jogo": f"{row.Home} x {row.Away}",
                "Mandante": row.Home,
                "Visitante": row.Away,
                "Grupo do mercado": row.Market,
                "Mercado": row.MarketName,
                "Código da seleção": row.Side,
                "Seleção": row.Selection,
                "Casa de apostas": row.Bookmaker,
                "Cotação": float(row.Odd),
                "Cotação após desconto": float(row.EffectiveOdd),
                "Probabilidade do modelo %": float(row.DecisionProbability) * 100.0,
                "Probabilidade conservadora %": float(row.ConservativeProbability) * 100.0,
                "Valor esperado conservador %": float(row.ExpectedValue) * 100.0,
                "Casos semelhantes": int(row.ProfileSample),
                "Confiança da amostra": row.SampleConfidence,
                "Estabilidade %": float(row.Reliability) * 100.0,
                "Entrada (R$)": float(row.Stake),
                "Banca de referência (R$)": float(bankroll),
                "Situação da liquidação": SITUACAO_PENDENTE,
                "Resultado da aposta": "PENDENTE",
            }
        )
        records.append(record)
    return records


def venceu_selecao(market: str, side: str, home_goals: int, away_goals: int) -> bool:
    market = _texto(market)
    side = _texto(side)
    try:
        home_goals = int(home_goals)
        away_goals = int(away_goals)
    except (TypeError, ValueError) as exc:
        raise ValueError("Os gols devem ser números inteiros não negativos.") from exc
    if home_goals < 0 or away_goals < 0:
        raise ValueError("Os gols não podem ser negativos.")

    allowed = {
        "1X2": {"H", "D", "A"},
        "OU25": {"O25", "U25"},
        "BTTS": {"BTTS_Y", "BTTS_N"},
    }
    if market not in allowed:
        raise ValueError(f"Código de mercado desconhecido: {market or 'ausente'}.")
    if side not in allowed[market]:
        raise ValueError(
            f"A seleção {side or 'ausente'} não pertence ao mercado {market}."
        )

    total = home_goals + away_goals
    both_score = home_goals > 0 and away_goals > 0
    rules = {
        "H": home_goals > away_goals,
        "D": home_goals == away_goals,
        "A": home_goals < away_goals,
        "O25": total >= 3,
        "U25": total <= 2,
        "BTTS_Y": both_score,
        "BTTS_N": not both_score,
    }
    return bool(rules[side])


def liquidar_registro(
    record: dict[str, Any],
    home_goals: int,
    away_goals: int,
    observations: str = "",
) -> dict[str, Any]:
    updated = {column: record.get(column, "") for column in COLUNAS_APOSTAS}
    side = _texto(updated.get("Código da seleção"))
    market = _texto(updated.get("Grupo do mercado"))
    won = venceu_selecao(market, side, home_goals, away_goals)
    odd = _numero(updated.get("Cotação"), default=float("nan"))
    stake = _numero(updated.get("Entrada (R$)"), default=float("nan"))
    if not np.isfinite(odd) or odd <= 1.0:
        raise ValueError("A cotação registrada precisa ser maior que 1,00.")
    if not np.isfinite(stake) or stake < 0.0:
        raise ValueError("A entrada registrada não pode ser negativa.")

    home_goals = int(home_goals)
    away_goals = int(away_goals)
    gross_return = stake * odd if won else 0.0
    profit = gross_return - stake
    updated.update(
        {
            "Situação da liquidação": SITUACAO_LIQUIDADA,
            "Gols do mandante": home_goals,
            "Gols do visitante": away_goals,
            "Resultado da aposta": "GANHA" if won else "PERDIDA",
            "Retorno bruto (R$)": round(gross_return, 2),
            "Lucro ou prejuízo (R$)": round(profit, 2),
            "Liquidado em": agora_brasilia(),
            "Observações": _texto(observations),
        }
    )
    return updated


def normalizar_ledger(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=COLUNAS_APOSTAS)
    result = frame.copy()
    for column in COLUNAS_APOSTAS:
        if column not in result.columns:
            result[column] = ""
    return result[COLUNAS_APOSTAS]


def mesclar_registros(frame: pd.DataFrame | None, records: Iterable[dict[str, Any]]) -> tuple[pd.DataFrame, int]:
    current = normalizar_ledger(frame)
    incoming = normalizar_ledger(pd.DataFrame(list(records)))
    if incoming.empty:
        return current, 0
    existing_ids = set(current["ID Aposta"].astype(str))
    new_rows = incoming[~incoming["ID Aposta"].astype(str).isin(existing_ids)].copy()
    if new_rows.empty:
        return current, 0
    if current.empty:
        return normalizar_ledger(new_rows.reset_index(drop=True)), int(len(new_rows))
    merged = pd.concat([current, new_rows], ignore_index=True)
    return normalizar_ledger(merged), int(len(new_rows))


def reconciliar_ledgers(primary: pd.DataFrame | None, secondary: pd.DataFrame | None) -> pd.DataFrame:
    """Mescla duas cópias do controle sem perder liquidações.

    Uma linha liquidada sempre prevalece sobre uma pendente. Em igualdade de
    situação, prevalece o registro com o timestamp mais recente. A cópia
    secundária é usada apenas como desempate final, preservando o histórico local.
    """
    first = normalizar_ledger(primary).copy()
    second = normalizar_ledger(secondary).copy()
    if first.empty:
        return second
    if second.empty:
        return first
    first["__origem"] = 0
    second["__origem"] = 1
    combined = pd.concat([first, second], ignore_index=True)
    combined = combined[combined["ID Aposta"].astype(str).str.strip().ne("")]
    output: list[dict[str, Any]] = []
    for _, group in combined.groupby("ID Aposta", sort=False):
        candidates = group.copy()
        candidates["__liquidada"] = (
            candidates["Situação da liquidação"].astype(str).eq(SITUACAO_LIQUIDADA).astype(int)
        )
        settled_at = pd.to_datetime(
            candidates["Liquidado em"], dayfirst=True, errors="coerce"
        )
        registered_at = pd.to_datetime(
            candidates["Registrado em"], dayfirst=True, errors="coerce"
        )
        candidates["__momento"] = settled_at.fillna(registered_at).fillna(pd.Timestamp.min)
        chosen = candidates.sort_values(
            ["__liquidada", "__momento", "__origem"], ascending=[False, False, False]
        ).iloc[0].to_dict()
        for _, candidate in candidates.iterrows():
            for column in COLUNAS_APOSTAS:
                if not _texto(chosen.get(column)) and _texto(candidate.get(column)):
                    chosen[column] = candidate.get(column)
        output.append({column: chosen.get(column, "") for column in COLUNAS_APOSTAS})
    return normalizar_ledger(pd.DataFrame(output))


def atualizar_registro(frame: pd.DataFrame, updated: dict[str, Any]) -> pd.DataFrame:
    result = normalizar_ledger(frame)
    bet_id = _texto(updated.get("ID Aposta"))
    mask = result["ID Aposta"].astype(str).eq(bet_id)
    if not mask.any():
        raise KeyError(f"Aposta não encontrada: {bet_id}.")
    for column in COLUNAS_APOSTAS:
        result.loc[mask, column] = updated.get(column, "")
    return result


def resumo_financeiro(frame: pd.DataFrame | None, bankroll_reference: float = 0.0) -> dict[str, float | int]:
    """Resume resultados realizados sem inferir depósitos, saques ou banca atual.

    ``bankroll_reference`` é apenas a banca informada na interface. Ela não recebe
    o lucro acumulado novamente, evitando dupla contagem quando o usuário já
    atualizou a banca após liquidações anteriores.
    """
    try:
        informed_bankroll = float(bankroll_reference)
    except (TypeError, ValueError) as exc:
        raise ValueError("A banca informada deve ser numérica.") from exc
    if not np.isfinite(informed_bankroll) or informed_bankroll < 0.0:
        raise ValueError("A banca informada deve ser não negativa.")

    ledger = normalizar_ledger(frame)
    empty_result = {
        "registradas": int(len(ledger)), "pendentes": 0, "liquidadas": 0, "ganhas": 0,
        "entradas_liquidadas": 0.0, "lucro": 0.0, "retorno_sobre_entradas": 0.0,
        "taxa_acerto": 0.0, "banca_informada": informed_bankroll,
        "banca_estimada": informed_bankroll, "maior_recuo": 0.0,
    }
    if ledger.empty:
        return empty_result

    settled = ledger[ledger["Situação da liquidação"].astype(str).eq(SITUACAO_LIQUIDADA)].copy()
    pending_count = int(ledger["Situação da liquidação"].astype(str).eq(SITUACAO_PENDENTE).sum())
    if settled.empty:
        empty_result["pendentes"] = pending_count
        return empty_result

    game_date = pd.to_datetime(settled["Data do jogo"], dayfirst=True, errors="coerce")
    game_time = pd.to_timedelta(settled["Hora do jogo"].astype(str) + ":00", errors="coerce")
    liquidated_at = pd.to_datetime(settled["Liquidado em"], dayfirst=True, errors="coerce")
    registered_at = pd.to_datetime(settled["Registrado em"], dayfirst=True, errors="coerce")
    settled["__ordem"] = (
        game_date.fillna(pd.Timestamp.min)
        + game_time.fillna(pd.Timedelta(0))
    )
    settled["__ordem"] = settled["__ordem"].where(
        game_date.notna(), liquidated_at.fillna(registered_at).fillna(pd.Timestamp.min)
    )
    settled = settled.sort_values(["__ordem", "ID Aposta"], kind="stable")

    stakes = pd.to_numeric(settled["Entrada (R$)"].map(_numero), errors="coerce").fillna(0.0)
    profits = pd.to_numeric(settled["Lucro ou prejuízo (R$)"].map(_numero), errors="coerce").fillna(0.0)
    total_stakes = float(stakes.sum())
    total_profit = float(profits.sum())
    equity = profits.cumsum().to_numpy(dtype=float)
    peaks = np.maximum.accumulate(np.concatenate([[0.0], equity]))[1:]
    max_drawdown = float(np.max(peaks - equity)) if len(equity) else 0.0
    wins = int(settled["Resultado da aposta"].astype(str).eq("GANHA").sum())
    return {
        "registradas": int(len(ledger)),
        "pendentes": pending_count,
        "liquidadas": int(len(settled)),
        "ganhas": wins,
        "entradas_liquidadas": total_stakes,
        "lucro": total_profit,
        "retorno_sobre_entradas": total_profit / total_stakes if total_stakes > 0 else 0.0,
        "taxa_acerto": wins / len(settled) if len(settled) else 0.0,
        "banca_informada": informed_bankroll,
        "banca_estimada": informed_bankroll,
        "maior_recuo": max_drawdown,
    }


def contagens_semanais(frame: pd.DataFrame | None) -> dict[str, int]:
    """Conta apostas já registradas por semana ISO.

    Todas as apostas registradas contam para o limite, estejam pendentes ou
    liquidadas. Identificadores repetidos são eliminados antes da contagem.
    Linhas antigas sem data válida são ignoradas.
    """
    ledger = normalizar_ledger(frame)
    if ledger.empty:
        return {}
    ledger = ledger.copy()
    ledger = ledger[ledger["ID Aposta"].astype(str).str.strip().ne("")]
    ledger = ledger.drop_duplicates("ID Aposta", keep="first")
    dates = pd.to_datetime(ledger["Data do jogo"], dayfirst=True, errors="coerce")
    valid = ledger.loc[dates.notna()].copy()
    if valid.empty:
        return {}
    iso = dates[dates.notna()].dt.isocalendar()
    valid["Semana"] = (
        iso["year"].astype(str) + "-" + iso["week"].astype(int).astype(str).str.zfill(2)
    ).to_numpy()
    return {str(week): int(count) for week, count in valid.groupby("Semana").size().items()}


def identificadores_partidas_registradas(frame: pd.DataFrame | None) -> set[str]:
    """Reconstrói os identificadores das partidas que já possuem aposta."""
    ledger = normalizar_ledger(frame)
    if ledger.empty:
        return set()
    ledger = ledger.copy()
    ledger = ledger[ledger["ID Aposta"].astype(str).str.strip().ne("")]
    ledger = ledger.drop_duplicates("ID Aposta", keep="first")
    dates = pd.to_datetime(ledger["Data do jogo"], dayfirst=True, errors="coerce")
    identifiers: set[str] = set()
    for index, row in ledger.iterrows():
        parsed_date = dates.loc[index]
        code = _texto(row.get("Código da liga"))
        home = _texto(row.get("Mandante"))
        away = _texto(row.get("Visitante"))
        if pd.isna(parsed_date) or not code or not home or not away:
            continue
        identifiers.add(f"{code}|{pd.Timestamp(parsed_date).date().isoformat()}|{home}|{away}")
    return identifiers


def carregar_ledger_local(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=COLUNAS_APOSTAS)
    return normalizar_ledger(pd.read_csv(path, dtype=str, keep_default_na=False))


def salvar_ledger_local(path: str | Path, frame: pd.DataFrame) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    normalizar_ledger(frame).to_csv(temporary, index=False, encoding="utf-8-sig")
    os.replace(temporary, path)


__all__ = [
    "COLUNAS_APOSTAS", "SITUACAO_LIQUIDADA", "SITUACAO_PENDENTE", "atualizar_registro",
    "carregar_ledger_local", "contagens_semanais", "criar_registros_apostas", "identificador_aposta",
    "identificador_registro", "identificadores_partidas_registradas", "liquidar_registro",
    "mesclar_registros", "normalizar_ledger", "reconciliar_ledgers",
    "resumo_financeiro", "salvar_ledger_local", "venceu_selecao",
]
