from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from difflib import SequenceMatcher
from typing import Any, Iterable
import math
import re
import unicodedata

IMPORTER_API_VERSION = "28.3.15"

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

# O importador usa um catálogo universal construído em tempo de execução a partir
# de todas as temporadas das 24 ligas. As equivalências abaixo cobrem apenas os
# casos em que o nome comercial não pode ser deduzido por normalização, sigla,
# prefixo/sufixo institucional ou comparação por tokens.
_EXPLICIT_CANONICAL_ALIASES: dict[str, str] = {
    # Brasil
    "flamengo": "Flamengo RJ",
    "flamengo rj": "Flamengo RJ",
    "cr flamengo": "Flamengo RJ",
    "sao paulo sp": "Sao Paulo",
    "sao paulo fc": "Sao Paulo",
    "clube do remo": "Remo",
    "clube de remo": "Remo",
    "atletico mg": "Atletico-MG",
    "atletico mineiro": "Atletico-MG",
    "america mineiro": "America MG",
    "atletico goianiense": "Atletico GO",
    "associacao chapecoense": "Chapecoense-SC",
    "vasco da gama": "Vasco",
    "cr vasco da gama": "Vasco",
    "sc internacional": "Internacional",
    "sport club internacional": "Internacional",
    "esporte clube bahia": "Bahia",
    "athletico paranaense": "Athletico-PR",
    "atletico paranaense": "Athletico-PR",
    "red bull bragantino": "Bragantino",
    "rb bragantino": "Bragantino",
    "botafogo": "Botafogo RJ",
    "gremio fbpa": "Gremio",
    "sport club do recife": "Sport Recife",
    # Argentina
    "argentinos juniors": "Argentinos Jrs",
    "atletico tucuman": "Atl. Tucuman",
    "atletico rafaela": "Atl. Rafaela",
    "estudiantes de la plata": "Estudiantes L.P.",
    "gimnasia y esgrima la plata": "Gimnasia L.P.",
    "newells old boys": "Newells Old Boys",
    "union santa fe": "Union de Santa Fe",
    # Estados Unidos / MLS
    "ny city": "New York City",
    "nycfc": "New York City",
    "new york city fc": "New York City",
    "la galaxy": "Los Angeles Galaxy",
    "lafc": "Los Angeles FC",
    "inter miami cf": "Inter Miami",
    "atlanta united": "Atlanta Utd",
    "ny red bulls": "New York Red Bulls",
    "sporting kc": "Sporting Kansas City",
    "st louis city sc": "St. Louis City",
    # México
    "atletico san luis": "Atl. San Luis",
    "club america mexico": "Club America",
    "chivas guadalajara": "Guadalajara Chivas",
    "pumas unam": "UNAM Pumas",
    "tigres": "Tigres UANL",
    # Japão
    "jubilo iwata": "Iwata",
    "tokyo verdy": "Verdy",
    "consadole sapporo": "Hokkaido Consadole Sapporo",
    # Escandinávia e Finlândia
    "ifk goteborg": "Goteborg",
    "malmo": "Malmo FF",
    "djurgardens if": "Djurgarden",
    "bk hacken": "Hacken",
    "kuopion palloseura": "KuPS",
    "kotkan tyovaen palloilijat": "KTP",
    "ifk mariehamn": "Mariehamn",
    "vps vaasa": "VPS",
    "vaasan palloseura": "VPS",
    "ilves tampere": "Ilves",
    "tampereen ilves": "Ilves",
    "seinajoen jk": "SJK",
    "sjk seinajoki": "SJK",
    "seinajoen jalkapallokerho": "SJK",
    "helsingin jk": "HJK",
    # Irlanda
    "university college dublin": "UC Dublin",
    "st patricks athletic": "St. Patricks",
    # Inglaterra
    "manchester city": "Man City",
    "manchester united": "Man United",
    "nottingham forest": "Nott'm Forest",
    "wolverhampton wanderers": "Wolves",
    "tottenham hotspur": "Tottenham",
    "west bromwich albion": "West Brom",
    "queens park rangers": "QPR",
    "sheffield wednesday": "Sheffield Weds",
    "peterborough united": "Peterboro",
    "milton keynes dons": "Milton Keynes Dons",
    "mk dons": "Milton Keynes Dons",
    # Espanha
    "athletic bilbao": "Ath Bilbao",
    "atletico madrid": "Ath Madrid",
    "real betis": "Betis",
    "real sociedad": "Sociedad",
    "deportivo la coruna": "La Coruna",
    "rayo vallecano": "Vallecano",
    "sporting gijon": "Sp Gijon",
    "espanyol": "Espanol",
    "real oviedo": "Oviedo",
    "real valladolid": "Valladolid",
    "real zaragoza": "Zaragoza",
    # Itália
    "inter milan": "Inter",
    "internazionale": "Inter",
    "ac milan": "Milan",
    "as roma": "Roma",
    "hellas verona": "Verona",
    # Alemanha
    "bayern munchen": "Bayern Munich",
    "bayern muenchen": "Bayern Munich",
    "borussia dortmund": "Dortmund",
    "eintracht frankfurt": "Ein Frankfurt",
    "borussia monchengladbach": "M'gladbach",
    "borussia moenchengladbach": "M'gladbach",
    "bayer leverkusen": "Leverkusen",
    "tsg hoffenheim": "Hoffenheim",
    "hamburger sv": "Hamburg",
    "hertha berlin": "Hertha",
    "hertha bsc": "Hertha",
    "eintracht braunschweig": "Braunschweig",
    "dynamo dresden": "Dresden",
    "sg dynamo dresden": "Dresden",
    "energie cottbus": "Cottbus",
    "fc energie cottbus": "Cottbus",
    "spvgg greuther furth": "Greuther Furth",
    "greuther furth": "Greuther Furth",
    "1 fc nurnberg": "Nurnberg",
    "vfl osnabruck": "Osnabruck",
    "vfl bochum": "Bochum",
    "vfl wolfsburg": "Wolfsburg",
    "fc st pauli": "St Pauli",
    "1 fc heidenheim": "Heidenheim",
    "karlsruher sc": "Karlsruhe",
    "arminia bielefeld": "Bielefeld",
    "dsc arminia bielefeld": "Bielefeld",
    "sv darmstadt 98": "Darmstadt",
    "1 fc magdeburg": "Magdeburg",
    "1 fc kaiserslautern": "Kaiserslautern",
    "hannover 96": "Hannover",
    # França
    "psg": "Paris SG",
    "paris saint germain": "Paris SG",
    "paris st germain": "Paris SG",
    "olympique marseille": "Marseille",
    "olympique lyonnais": "Lyon",
    "as monaco": "Monaco",
    "losc lille": "Lille",
    "as saint etienne": "St Etienne",
    # Portugal
    "sporting cp": "Sp Lisbon",
    "sporting lisboa": "Sp Lisbon",
    "sporting lisbon": "Sp Lisbon",
    "sporting braga": "Sp Braga",
    "vitoria guimaraes": "Guimaraes",
    "sl benfica": "Benfica",
    "pacos de ferreira": "Pacos Ferreira",
    "academico viseu": "Academico Viseu",
    "academico de viseu": "Academico Viseu",
    "academico de viseu fc": "Academico Viseu",
    "ac viseu": "Academico Viseu",
    "academico viseu fc": "Academico Viseu",
    "cs maritimo": "Maritimo",
    "maritimo madeira": "Maritimo",
    "maritimo m": "Maritimo",
    # Holanda
    "psv": "PSV Eindhoven",
    "fortuna sittard": "For Sittard",
    "ado den haag": "Den Haag",
    "nec nijmegen": "Nijmegen",
    "rkc waalwijk": "Waalwijk",
    "pec zwolle": "Zwolle",
    "vitesse arnhem": "Vitesse",
    # Bélgica
    "royal antwerp": "Antwerp",
    "union saint gilloise": "St. Gilloise",
    "union st gilloise": "St. Gilloise",
    "standard liege": "Standard",
    "kv mechelen": "Mechelen",
    "zulte waregem": "Waregem",
    "oh leuven": "Oud-Heverlee Leuven",
    # Turquia
    "istanbul basaksehir": "Buyuksehyr",
    "adana demirspor": "Ad. Demirspor",
    "fatih karagumruk": "Karagumruk",
    "goztepe": "Goztep",
    # Grécia
    "aek athens": "AEK",
    "paok thessaloniki": "PAOK",
    "olympiacos": "Olympiakos",
    "olympiacos piraeus": "Olympiakos",
    "pas giannina": "Giannina",
    "aris thessaloniki": "Aris",
}

# Temporadas anuais são indexadas pelo próprio ano. As demais usam o ano de
# início da temporada europeia.
_CALENDAR_YEAR_CODES = {"BRA", "ARG", "USA", "MEX", "JPN", "CHN", "SWE", "NOR", "FIN", "IRL"}

# Overlay somente quando o arquivo histórico ainda não contém a temporada nova.
_SEASONAL_ROSTER_OVERLAYS: dict[tuple[str, int], tuple[str, ...]] = {
    ("D2", 2026): (
        "Bielefeld", "Bochum", "Braunschweig", "Cottbus", "Darmstadt",
        "Dresden", "Greuther Furth", "Hannover", "Heidenheim", "Hertha",
        "Kaiserslautern", "Karlsruhe", "Holstein Kiel", "Magdeburg",
        "Nurnberg", "Osnabruck", "St Pauli", "Wolfsburg",
    ),
    # Primeira Liga 2026/27. O Académico de Viseu regressou à elite após
    # um intervalo anterior ao recorte histórico local; por isso precisa
    # entrar como candidato sazonal mesmo sem partidas P1 desde 2012.
    ("P1", 2026): (
        "Academico Viseu", "Alverca", "Arouca", "Benfica", "Casa Pia",
        "Estoril", "Estrela", "Famalicao", "Gil Vicente", "Guimaraes",
        "Maritimo", "Moreirense", "Nacional", "Porto", "Rio Ave",
        "Santa Clara", "Sp Braga", "Sp Lisbon",
    ),
}

# Tokens institucionais e geográficos são tratados em etapas diferentes. Isso
# preserva distinções como Atlético-GO x Atlético-MG, sem deixar de aceitar
# prefixos como FC, SC, EC e sufixos estaduais usados por alguns operadores.
_INSTITUTION_TOKENS = {
    "fc", "sc", "ec", "ac", "cf", "afc", "cfc", "club", "clube",
    "futebol", "football", "fk", "sk", "if", "bk", "ff", "ik", "kv",
    "ca", "cd", "cr", "cs", "se", "aa", "ad", "sd", "ud", "rc", "rcd",
    "ssc", "ss", "us", "sv", "vfb", "vfl", "fsv", "tsg", "sg", "dsc",
    "spvgg", "1", "04", "05", "08", "09", "96", "98",
}
_ARTICLE_TOKENS = {"de", "do", "da", "dos", "das", "the"}
_LOCATION_TOKENS = {"rj", "mg", "pr", "rs", "ba", "go", "sp"}
_DROP_TOKENS = _INSTITUTION_TOKENS | _ARTICLE_TOKENS | _LOCATION_TOKENS


_TOKEN_EQUIVALENTS = {
    "utd": "united",
    "jrs": "juniors",
    "st": "saint",
    "sankt": "saint",
    "munchen": "munich",
    "muenchen": "munich",
    "monchengladbach": "moenchengladbach",
    "dep": "deportivo",
    "atl": "atletico",
    "sp": "sporting",
    "ind": "independiente",
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


def _equivalent_token_forms(value: Any) -> set[str]:
    tokens = normalize_name(value).split()
    if not tokens:
        return set()
    replaced = [_TOKEN_EQUIVALENTS.get(token, token) for token in tokens]
    forms = {" ".join(tokens), " ".join(replaced)}
    return {form for form in forms if form}


def _strip_form(value: Any, drop_tokens: set[str]) -> str:
    return " ".join(token for token in normalize_name(value).split() if token not in drop_tokens)


def _candidate_forms(name: str) -> set[str]:
    forms = set(_equivalent_token_forms(name))
    for form in list(forms):
        institutional = _strip_form(form, _INSTITUTION_TOKENS | _ARTICLE_TOKENS)
        aggressive = _strip_form(form, _DROP_TOKENS)
        for candidate in (institutional, aggressive):
            if candidate:
                forms.add(candidate)
        forms.add(form.replace(" ", ""))
        if institutional:
            forms.add(institutional.replace(" ", ""))
        if aggressive:
            forms.add(aggressive.replace(" ", ""))
    return {item for item in forms if item}


def _acronym_forms(value: Any) -> set[str]:
    tokens = normalize_name(value).split()
    if not tokens:
        return set()
    meaningful = [token for token in tokens if token not in {"de", "do", "da", "dos", "das", "the"}]
    if not meaningful:
        meaningful = tokens
    initials = "".join(token[0] for token in meaningful if token)
    hybrid = "".join(token if len(token) <= 3 else token[0] for token in meaningful if token)
    compact = "".join(meaningful)
    return {item for item in (initials, hybrid, compact) if 2 <= len(item) <= 16}


def _token_containment_score(raw_name: str, canonical: str) -> float:
    raw_tokens = set(simplified_name(raw_name).split())
    canonical_tokens = set(simplified_name(canonical).split())
    if not raw_tokens or not canonical_tokens:
        return 0.0
    if canonical_tokens <= raw_tokens or raw_tokens <= canonical_tokens:
        smaller = canonical_tokens if len(canonical_tokens) <= len(raw_tokens) else raw_tokens
        informative = [token for token in smaller if len(token) >= 4]
        canonical_compact = normalize_name(canonical).replace(" ", "")
        canonical_is_sigla = (
            len(canonical_tokens) == 1
            and 2 <= len(canonical_compact) <= 5
            and str(canonical).strip().replace(".", "").replace("-", "").isupper()
        )
        if canonical_is_sigla and canonical_compact in raw_tokens:
            return 0.985
        if len(smaller) >= 2:
            return 0.972
        if informative:
            return 0.962 if len(informative[0]) >= 5 else 0.948
    return 0.0


def _team_match_score(raw_name: str, canonical: str) -> float:
    raw_normalized = normalize_name(raw_name)
    canonical_normalized = normalize_name(canonical)
    explicit_target = _EXPLICIT_CANONICAL_ALIASES.get(raw_normalized)
    if explicit_target and normalize_name(explicit_target) == canonical_normalized:
        return 1.0
    if raw_normalized == canonical_normalized:
        return 1.0

    raw_equivalent = _equivalent_token_forms(raw_name)
    canonical_equivalent = _equivalent_token_forms(canonical)
    if raw_equivalent & canonical_equivalent:
        return 0.998

    raw_institutional = {
        _strip_form(form, _INSTITUTION_TOKENS | _ARTICLE_TOKENS)
        for form in raw_equivalent
    } - {""}
    canonical_institutional = {
        _strip_form(form, _INSTITUTION_TOKENS | _ARTICLE_TOKENS)
        for form in canonical_equivalent
    } - {""}
    if raw_institutional & canonical_institutional:
        return 0.996

    raw_aggressive = {_strip_form(form, _DROP_TOKENS) for form in raw_equivalent} - {""}
    canonical_aggressive = {_strip_form(form, _DROP_TOKENS) for form in canonical_equivalent} - {""}
    if raw_aggressive & canonical_aggressive:
        return 0.985

    raw_acronyms = _acronym_forms(raw_name)
    canonical_acronyms = _acronym_forms(canonical)
    common_acronyms = raw_acronyms & canonical_acronyms
    if any(len(item) >= 3 for item in common_acronyms):
        return 0.982

    raw_forms = _candidate_forms(raw_name)
    canonical_forms = _candidate_forms(canonical)
    score = _token_containment_score(raw_name, canonical)
    for left in raw_forms:
        for right in canonical_forms:
            sequence = SequenceMatcher(None, left, right).ratio()
            score = max(score, sequence)
            left_tokens, right_tokens = set(left.split()), set(right.split())
            if left_tokens and right_tokens:
                jaccard = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
                containment = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
                score = max(score, 0.55 * containment + 0.25 * jaccard + 0.20 * sequence)

    if min(len(raw_normalized), len(canonical_normalized)) <= 3 and raw_normalized != canonical_normalized:
        score *= 0.82
    return score

def _season_from_imported_date(value: Any, league_code: str = "") -> int | None:
    if isinstance(value, date):
        parsed = value
    else:
        text = str(value or "").strip()
        try:
            parsed = date.fromisoformat(text[:10])
        except (TypeError, ValueError):
            return None
    if str(league_code) in _CALENDAR_YEAR_CODES:
        return parsed.year
    return parsed.year if parsed.month >= 7 else parsed.year - 1


def _preferred_candidates(
    league_code: str,
    *,
    preferred_teams_by_code: dict[str, list[str]] | None,
    teams_by_season: dict[str, dict[int, list[str]]] | None,
    match_date: Any,
) -> set[str]:
    code = str(league_code)
    preferred = set((preferred_teams_by_code or {}).get(code, []))
    season = _season_from_imported_date(match_date, code) if match_date is not None else None
    if season is not None and teams_by_season:
        seasonal = set((teams_by_season.get(code, {}) or {}).get(int(season), []))
        if len(seasonal) >= 12:
            preferred = seasonal
        else:
            preferred |= seasonal
    if season is not None:
        preferred |= set(_SEASONAL_ROSTER_OVERLAYS.get((code, int(season)), ()))
    return {str(item) for item in preferred if str(item).strip()}


def resolve_team_in_league(
    raw_name: str,
    league_code: str,
    teams_by_code: dict[str, list[str]],
    *,
    extra_candidates: Iterable[str] | None = None,
    match_date: Any = None,
    preferred_teams_by_code: dict[str, list[str]] | None = None,
    teams_by_season: dict[str, dict[int, list[str]]] | None = None,
) -> tuple[str, float]:
    code = str(league_code)
    candidates = {str(item) for item in teams_by_code.get(code, []) if str(item).strip()}
    season = _season_from_imported_date(match_date, code) if match_date is not None else None
    if season is not None:
        candidates |= set(_SEASONAL_ROSTER_OVERLAYS.get((code, int(season)), ()))
    if extra_candidates:
        candidates |= {str(item) for item in extra_candidates if str(item).strip()}
    if not candidates:
        return "", 0.0

    preferred = _preferred_candidates(
        code,
        preferred_teams_by_code=preferred_teams_by_code,
        teams_by_season=teams_by_season,
        match_date=match_date,
    )
    ranked: list[tuple[str, float, float]] = []
    for canonical in candidates:
        lexical = _team_match_score(raw_name, canonical)
        if canonical in preferred:
            adjusted = min(1.0, lexical + 0.004)
        else:
            adjusted = lexical
        ranked.append((canonical, adjusted, lexical))
    ranked.sort(key=lambda item: (item[1], item[2], item[0]), reverse=True)
    top = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else ("", 0.0, 0.0)

    # Um empate entre dois nomes da mesma liga não deve ser resolvido no chute.
    if top[1] < 0.985 and top[1] - runner[1] < 0.015:
        return "", float(top[1])
    return top[0], float(top[1])

def infer_league_and_teams(
    home_raw: str,
    away_raw: str,
    *,
    teams_by_code: dict[str, list[str]],
    leagues: dict[str, str],
    match_date: Any = None,
    preferred_teams_by_code: dict[str, list[str]] | None = None,
    teams_by_season: dict[str, dict[int, list[str]]] | None = None,
) -> dict[str, Any]:
    ranking: list[tuple[str, str, str, str, float, float, float]] = []
    for code, league_name in leagues.items():
        home, home_score = resolve_team_in_league(
            home_raw,
            code,
            teams_by_code,
            match_date=match_date,
            preferred_teams_by_code=preferred_teams_by_code,
            teams_by_season=teams_by_season,
        )
        away, away_score = resolve_team_in_league(
            away_raw,
            code,
            teams_by_code,
            match_date=match_date,
            preferred_teams_by_code=preferred_teams_by_code,
            teams_by_season=teams_by_season,
        )
        pair_score = min(home_score, away_score) * 0.65 + ((home_score + away_score) / 2.0) * 0.35
        preferred = _preferred_candidates(
            code,
            preferred_teams_by_code=preferred_teams_by_code,
            teams_by_season=teams_by_season,
            match_date=match_date,
        )
        roster_hits = int(home in preferred) + int(away in preferred)
        pair_score = min(1.0, pair_score + 0.015 * roster_hits)
        if not home or not away or home == away:
            pair_score *= 0.70
        ranking.append((code, league_name, home, away, home_score, away_score, pair_score))
    ranking.sort(key=lambda item: item[6], reverse=True)
    best = ranking[0] if ranking else ("", "", "", "", 0.0, 0.0, 0.0)
    runner_score = ranking[1][6] if len(ranking) > 1 else 0.0
    code, league_name, home, away, home_score, away_score, pair_score = best
    margin = pair_score - runner_score
    accepted = bool(
        code
        and home
        and away
        and home != away
        and home_score >= 0.72
        and away_score >= 0.72
        and (margin >= 0.020 or pair_score >= 0.995)
    )
    if accepted:
        confidence = "Alta" if min(home_score, away_score) >= 0.94 else "Média"
        reason = (
            "Ambas as equipes foram reconhecidas na mesma liga pelo catálogo universal; "
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
    preferred_teams_by_code: dict[str, list[str]] | None = None,
    teams_by_season: dict[str, dict[int, list[str]]] | None = None,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for item in parsed:
        resolution = infer_league_and_teams(
            str(item.get("mandante_original", "")),
            str(item.get("visitante_original", "")),
            teams_by_code=teams_by_code,
            leagues=leagues,
            match_date=item.get("data"),
            preferred_teams_by_code=preferred_teams_by_code,
            teams_by_season=teams_by_season,
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

