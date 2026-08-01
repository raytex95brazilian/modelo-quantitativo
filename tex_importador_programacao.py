from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from difflib import SequenceMatcher
from typing import Any, Iterable
import math
import re
import unicodedata

IMPORTER_API_VERSION = "28.3.8"

_DATE_RE = re.compile(r"^(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{2}|\d{4}))?$")
_TIME_RE = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})$")
_NUMBER_RE = re.compile(r"^\d+(?:[\.,]\d+)?$")
_INLINE_ODD_RE = re.compile(r"^(?P<label>.+?)\s+(?P<odd>\d{1,3}[\.,]\d{1,3})$")

_UI_NOISE_PREFIXES = (
    "rodada ", "sabado", "sábado", "domingo", "segunda", "terca", "terça",
    "quarta", "quinta", "sexta", "resultado final", "todos os mercados",
    "principal", "tempos", "gols", "escanteios", "jogadores", "especiais",
    "periodo", "período", "combos", "criador de apostas", "buscar mercado",
    "mostrar mais", "minhas apostas", "meus bonus", "meus bônus", "minhas ofertas",
)

# Equivalências frequentes entre sites de apostas e a nomenclatura da base local.
_EXPLICIT_ALIASES: dict[str, tuple[str, str]] = {
    "flamengo": ("BRA", "Flamengo RJ"),
    "flamengo rj": ("BRA", "Flamengo RJ"),
    "sao paulo sp": ("BRA", "Sao Paulo"),
    "sao paulo fc": ("BRA", "Sao Paulo"),
    "clube do remo": ("BRA", "Remo"),
    "clube de remo": ("BRA", "Remo"),
    "atletico mg": ("BRA", "Atletico-MG"),
    "atletico mineiro": ("BRA", "Atletico-MG"),
    "chapecoense": ("BRA", "Chapecoense-SC"),
    "associacao chapecoense": ("BRA", "Chapecoense-SC"),
    "vasco da gama": ("BRA", "Vasco"),
    "cr vasco da gama": ("BRA", "Vasco"),
    "sc internacional": ("BRA", "Internacional"),
    "sport club internacional": ("BRA", "Internacional"),
    "ec bahia": ("BRA", "Bahia"),
    "esporte clube bahia": ("BRA", "Bahia"),
    "athletico paranaense": ("BRA", "Athletico-PR"),
    "athletico pr": ("BRA", "Athletico-PR"),
    "atletico paranaense": ("BRA", "Athletico-PR"),
    "rb bragantino": ("BRA", "Bragantino"),
    "red bull bragantino": ("BRA", "Bragantino"),
    "botafogo": ("BRA", "Botafogo RJ"),
    "botafogo rj": ("BRA", "Botafogo RJ"),
    "gremio fbpa": ("BRA", "Gremio"),
    "ny city": ("USA", "New York City"),
    "nycfc": ("USA", "New York City"),
    "new york city fc": ("USA", "New York City"),
    "la galaxy": ("USA", "Los Angeles Galaxy"),
    "lafc": ("USA", "Los Angeles FC"),
    "inter miami cf": ("USA", "Inter Miami"),
    "manchester city": ("E0", "Man City"),
    "manchester united": ("E0", "Man United"),
    "nottingham forest": ("E0", "Nott'm Forest"),
    "psg": ("F1", "Paris SG"),
    "paris saint germain": ("F1", "Paris SG"),
    "sporting cp": ("P1", "Sp Lisbon"),
    "sporting lisboa": ("P1", "Sp Lisbon"),
    "sporting braga": ("P1", "Sp Braga"),
    # Variações exibidas na programação oficial/operadores da 2. Bundesliga.
    "hertha berlin": ("D2", "Hertha"),
    "hertha bsc": ("D2", "Hertha"),
    "eintracht braunschweig": ("D2", "Braunschweig"),
    "dynamo dresden": ("D2", "Dresden"),
    "sg dynamo dresden": ("D2", "Dresden"),
    "energie cottbus": ("D2", "Cottbus"),
    "fc energie cottbus": ("D2", "Cottbus"),
    "spvgg greuther furth": ("D2", "Greuther Furth"),
    "greuther furth": ("D2", "Greuther Furth"),
    "1 fc nurnberg": ("D2", "Nurnberg"),
    "vfl osnabruck": ("D2", "Osnabruck"),
    "vfl bochum": ("D2", "Bochum"),
    "vfl wolfsburg": ("D2", "Wolfsburg"),
    "fc st pauli": ("D2", "St Pauli"),
    "1 fc heidenheim": ("D2", "Heidenheim"),
    "karlsruher sc": ("D2", "Karlsruhe"),
    "arminia bielefeld": ("D2", "Bielefeld"),
    "dsc arminia bielefeld": ("D2", "Bielefeld"),
    "sv darmstadt 98": ("D2", "Darmstadt"),
    "1 fc magdeburg": ("D2", "Magdeburg"),
    "1 fc kaiserslautern": ("D2", "Kaiserslautern"),
    "hannover 96": ("D2", "Hannover"),
}

# O catálogo histórico só contém a temporada mais recente já baixada. Em ligas
# com promoção e rebaixamento, a programação da temporada seguinte pode trazer
# clubes que ainda não aparecem no recorte mais recente da base. O overlay é
# aplicado somente ao ano/temporada indicado pela data importada.
_SEASONAL_ROSTER_OVERLAYS: dict[tuple[str, int], tuple[str, ...]] = {
    ("D2", 2026): (
        "Bielefeld", "Bochum", "Braunschweig", "Cottbus", "Darmstadt",
        "Dresden", "Greuther Furth", "Hannover", "Heidenheim", "Hertha",
        "Kaiserslautern", "Karlsruhe", "Holstein Kiel", "Magdeburg",
        "Nurnberg", "Osnabruck", "St Pauli", "Wolfsburg",
    ),
}

_DROP_TOKENS = {
    "fc", "sc", "ec", "ac", "cf", "afc", "club", "clube", "futebol", "football",
    "de", "do", "da", "dos", "das", "the", "sp", "rj", "mg", "pr", "rs", "sc",
}


@dataclass
class ImportedMatch:
    data: str
    hora: str
    mandante_original: str
    visitante_original: str
    odd_mandante: float | None
    odd_empate: float | None
    odd_visitante: float | None
    bloco_origem: str
    aviso: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TeamResolution:
    league_code: str
    league_name: str
    home: str
    away: str
    home_score: float
    away_score: float
    confidence: str
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def simplified_name(value: Any) -> str:
    tokens = [token for token in normalize_name(value).split() if token not in _DROP_TOKENS]
    return " ".join(tokens)


def _clean_lines(raw_text: str) -> list[str]:
    lines: list[str] = []
    for raw in str(raw_text or "").replace("\xa0", " ").splitlines():
        line = " ".join(raw.strip().split())
        if not line:
            continue
        if normalize_name(line).startswith("icon "):
            continue
        # A cópia visual frequentemente duplica o nome logo após "Icon:".
        if lines and normalize_name(lines[-1]) == normalize_name(line):
            continue
        lines.append(line)
    return lines


def _parse_date_line(value: str, default_year: int) -> date | None:
    match = _DATE_RE.fullmatch(str(value).strip())
    if not match:
        return None
    day = int(match.group("day"))
    month = int(match.group("month"))
    year_text = match.group("year")
    year = int(default_year)
    if year_text:
        year = int(year_text)
        if year < 100:
            year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _valid_time(value: str) -> bool:
    match = _TIME_RE.fullmatch(str(value).strip())
    if not match:
        return False
    return 0 <= int(match.group("hour")) <= 23 and 0 <= int(match.group("minute")) <= 59


def _odd(value: Any) -> float | None:
    text = str(value or "").strip().replace(",", ".")
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or not (1.01 <= number <= 100.0):
        return None
    return round(number, 4)


def _is_team_candidate(value: str) -> bool:
    normalized = normalize_name(value)
    if not normalized or _NUMBER_RE.fullmatch(str(value).strip()):
        return False
    if normalized in {"empate", "sim", "nao", "mais de", "menos de"}:
        return False
    return not any(normalized.startswith(normalize_name(prefix)) for prefix in _UI_NOISE_PREFIXES)


def _pair_at(lines: list[str], index: int) -> tuple[str, float, int] | None:
    if index >= len(lines):
        return None
    if index + 1 < len(lines):
        value = _odd(lines[index + 1])
        if value is not None:
            return lines[index], value, index + 2
    inline = _INLINE_ODD_RE.fullmatch(lines[index])
    if inline:
        value = _odd(inline.group("odd"))
        if value is not None:
            return inline.group("label").strip(), value, index + 1
    return None


def _label_similarity(label: str, team: str) -> float:
    a = normalize_name(label)
    b = normalize_name(team)
    if a == b:
        return 1.0
    sa = simplified_name(label)
    sb = simplified_name(team)
    if sa and sa == sb:
        return 0.98
    return max(SequenceMatcher(None, a, b).ratio(), SequenceMatcher(None, sa, sb).ratio())


def _extract_first_1x2(block: list[str], home: str, away: str) -> tuple[float | None, float | None, float | None, str]:
    start = 4
    for i in range(start, len(block)):
        home_pair = _pair_at(block, i)
        if not home_pair or _label_similarity(home_pair[0], home) < 0.82:
            continue
        _, odd_home, cursor = home_pair
        draw_pair: tuple[str, float, int] | None = None
        for j in range(cursor, min(len(block), cursor + 8)):
            candidate = _pair_at(block, j)
            if candidate and normalize_name(candidate[0]) == "empate":
                draw_pair = candidate
                break
        if draw_pair is None:
            continue
        _, odd_draw, cursor = draw_pair
        away_pair: tuple[str, float, int] | None = None
        for j in range(cursor, min(len(block), cursor + 8)):
            candidate = _pair_at(block, j)
            if candidate and _label_similarity(candidate[0], away) >= 0.82:
                away_pair = candidate
                break
        if away_pair is None:
            continue
        return odd_home, odd_draw, away_pair[1], ""
    return None, None, None, "Resultado Final 1X2 não foi identificado com segurança."


def parse_pasted_schedule(raw_text: str, *, default_year: int) -> list[dict[str, Any]]:
    """Extrai data, hora, equipes e o primeiro mercado Resultado Final 1X2.

    Mercados posteriores são deliberadamente ignorados. O objetivo é evitar que
    números sem o cabeçalho visual do site sejam atribuídos à coluna errada.
    """
    lines = _clean_lines(raw_text)
    starts: list[int] = []
    for i in range(max(0, len(lines) - 3)):
        if _parse_date_line(lines[i], default_year) and _valid_time(lines[i + 1]):
            if _is_team_candidate(lines[i + 2]) and _is_team_candidate(lines[i + 3]):
                starts.append(i)
    results: list[dict[str, Any]] = []
    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
        block = lines[start:end]
        parsed_date = _parse_date_line(block[0], default_year)
        if parsed_date is None or len(block) < 4:
            continue
        home, away = block[2], block[3]
        odd_home, odd_draw, odd_away, warning = _extract_first_1x2(block, home, away)
        item = ImportedMatch(
            data=parsed_date.isoformat(),
            hora=block[1],
            mandante_original=home,
            visitante_original=away,
            odd_mandante=odd_home,
            odd_empate=odd_draw,
            odd_visitante=odd_away,
            bloco_origem="\n".join(block),
            aviso=warning,
        )
        results.append(item.to_dict())
    return results


def _candidate_forms(name: str) -> set[str]:
    normalized = normalize_name(name)
    simplified = simplified_name(name)
    forms = {normalized}
    if simplified:
        forms.add(simplified)
    return {item for item in forms if item}


def _team_match_score(raw_name: str, code: str, canonical: str) -> float:
    raw_normalized = normalize_name(raw_name)
    explicit = _EXPLICIT_ALIASES.get(raw_normalized)
    if explicit == (code, canonical):
        return 1.0
    raw_forms = _candidate_forms(raw_name)
    canonical_forms = _candidate_forms(canonical)
    if raw_forms & canonical_forms:
        return 0.98
    score = 0.0
    for left in raw_forms:
        for right in canonical_forms:
            score = max(score, SequenceMatcher(None, left, right).ratio())
            left_tokens, right_tokens = set(left.split()), set(right.split())
            if left_tokens and right_tokens:
                jaccard = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
                score = max(score, 0.70 * jaccard + 0.30 * SequenceMatcher(None, left, right).ratio())
    # Nomes muito curtos não podem vencer apenas por semelhança acidental.
    if min(len(raw_normalized), len(normalize_name(canonical))) <= 3 and raw_normalized != normalize_name(canonical):
        score *= 0.82
    return score


def resolve_team_in_league(
    raw_name: str,
    league_code: str,
    teams_by_code: dict[str, list[str]],
    *,
    extra_candidates: Iterable[str] | None = None,
) -> tuple[str, float]:
    candidates = list(teams_by_code.get(str(league_code), []))
    if extra_candidates:
        candidates = sorted(set(candidates) | {str(item) for item in extra_candidates if str(item).strip()})
    if not candidates:
        return "", 0.0
    ranked = sorted(
        ((canonical, _team_match_score(raw_name, str(league_code), canonical)) for canonical in candidates),
        key=lambda item: item[1],
        reverse=True,
    )
    return ranked[0]


def _season_from_imported_date(value: Any) -> int | None:
    if isinstance(value, date):
        parsed = value
    else:
        text = str(value or "").strip()
        try:
            parsed = date.fromisoformat(text[:10])
        except (TypeError, ValueError):
            return None
    # Ligas europeias usam o ano de início da temporada.
    return parsed.year if parsed.month >= 7 else parsed.year - 1


def infer_league_and_teams(
    home_raw: str,
    away_raw: str,
    *,
    teams_by_code: dict[str, list[str]],
    leagues: dict[str, str],
    match_date: Any = None,
) -> dict[str, Any]:
    season = _season_from_imported_date(match_date)
    ranking: list[tuple[str, str, str, float, float, float]] = []
    for code, league_name in leagues.items():
        overlay = _SEASONAL_ROSTER_OVERLAYS.get((str(code), int(season))) if season is not None else None
        home, home_score = resolve_team_in_league(
            home_raw, code, teams_by_code, extra_candidates=overlay
        )
        away, away_score = resolve_team_in_league(
            away_raw, code, teams_by_code, extra_candidates=overlay
        )
        pair_score = min(home_score, away_score) * 0.65 + ((home_score + away_score) / 2.0) * 0.35
        ranking.append((code, league_name, home, home_score, away_score, pair_score))
    ranking.sort(key=lambda item: item[5], reverse=True)
    best = ranking[0] if ranking else ("", "", "", 0.0, 0.0, 0.0)
    runner_score = ranking[1][5] if len(ranking) > 1 else 0.0
    code, league_name, home, home_score, away_score, pair_score = best
    best_overlay = (
        _SEASONAL_ROSTER_OVERLAYS.get((str(code), int(season)))
        if code and season is not None else None
    )
    away, _ = (
        resolve_team_in_league(away_raw, code, teams_by_code, extra_candidates=best_overlay)
        if code else ("", 0.0)
    )
    margin = pair_score - runner_score
    accepted = bool(code and home_score >= 0.72 and away_score >= 0.72 and (margin >= 0.035 or pair_score >= 0.965))
    if accepted:
        confidence = "Alta" if min(home_score, away_score) >= 0.94 else "Média"
        reason = (
            f"Ambas as equipes foram reconhecidas na mesma liga; "
            f"escores {home_score:.2f} e {away_score:.2f}."
        )
        status = "RECONHECIDO"
    else:
        confidence = "Baixa"
        status = "REVISAR"
        reason = (
            "Não foi possível determinar a liga com margem segura. "
            f"Melhor candidato: {league_name or 'nenhum'} ({pair_score:.2f}; margem {margin:.2f})."
        )
    return TeamResolution(
        league_code=code if accepted else "",
        league_name=league_name if accepted else "",
        home=home if accepted else home_raw,
        away=away if accepted else away_raw,
        home_score=float(home_score),
        away_score=float(away_score),
        confidence=confidence,
        status=status,
        reason=reason,
    ).to_dict()


def resolve_imported_matches(
    parsed: Iterable[dict[str, Any]],
    *,
    teams_by_code: dict[str, list[str]],
    leagues: dict[str, str],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for item in parsed:
        resolution = infer_league_and_teams(
            str(item.get("mandante_original", "")),
            str(item.get("visitante_original", "")),
            teams_by_code=teams_by_code,
            leagues=leagues,
            match_date=item.get("data"),
        )
        complete_odds = all(item.get(key) is not None for key in ("odd_mandante", "odd_empate", "odd_visitante"))
        status = str(resolution["status"])
        reasons = [str(resolution["reason"])]
        if not complete_odds:
            status = "REVISAR"
            reasons.append(str(item.get("aviso") or "Cotações 1X2 incompletas."))
        resolved.append({
            "Usar": status == "RECONHECIDO",
            "Status": status,
            "Confiança": resolution["confidence"],
            "Liga": resolution["league_name"],
            "Código da liga": resolution["league_code"],
            "Data": item.get("data", ""),
            "Hora": item.get("hora", ""),
            "Mandante": resolution["home"],
            "Visitante": resolution["away"],
            "Nome original mandante": item.get("mandante_original", ""),
            "Nome original visitante": item.get("visitante_original", ""),
            "Odd mandante": item.get("odd_mandante"),
            "Odd empate": item.get("odd_empate"),
            "Odd visitante": item.get("odd_visitante"),
            "Diagnóstico": " ".join(reason for reason in reasons if reason),
        })
    return resolved
