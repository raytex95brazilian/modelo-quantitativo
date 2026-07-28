from __future__ import annotations

import re

import tex_v25_storage as storage


class FakeWorksheet:
    def __init__(self, title: str):
        self.title = title
        self.header: list[str] = []
        self.rows: list[list] = []

    def row_values(self, row: int):
        if row == 1:
            return list(self.header)
        idx = row - 2
        return list(self.rows[idx]) if 0 <= idx < len(self.rows) else []

    def append_row(self, values, value_input_option=None):
        if not self.header:
            self.header = list(values)
        else:
            self.rows.append(list(values))

    def append_rows(self, rows, value_input_option=None):
        self.rows.extend([list(row) for row in rows])

    def update(self, range_name, values, value_input_option=None):
        if range_name.startswith("A1:"):
            self.header = list(values[0])
            return
        match = re.fullmatch(r"A(\d+):[A-Z]+(\d+)", range_name)
        assert match and match.group(1) == match.group(2), range_name
        idx = int(match.group(1)) - 2
        while len(self.rows) <= idx:
            self.rows.append([""] * len(self.header))
        self.rows[idx] = list(values[0])

    def get_all_values(self):
        return [list(self.header)] + [list(row) for row in self.rows]

    def col_values(self, number):
        values = [self.header[number - 1]] if self.header else []
        values.extend(row[number - 1] if number - 1 < len(row) else "" for row in self.rows)
        return values


class FakeSpreadsheet:
    def __init__(self):
        self.sheets: dict[str, FakeWorksheet] = {}

    def worksheet(self, title: str):
        if title not in self.sheets:
            raise RuntimeError(f"worksheet not found: {title}")
        return self.sheets[title]

    def add_worksheet(self, title: str, rows: int, cols: int):
        sheet = FakeWorksheet(title)
        self.sheets[title] = sheet
        return sheet


spreadsheet = FakeSpreadsheet()
storage._ABAS_GOOGLE.clear()
storage._CABECALHOS_ATUAIS.clear()
storage._CABECALHOS_SINCRONIZADOS.clear()
storage._CHAVES_GRAVADAS_NO_PROCESSO.clear()
storage._abrir_planilha = lambda secrets: spreadsheet

secrets = {
    "google_sheets": {"spreadsheet_id": "teste"},
    "gcp_service_account": {"client_email": "teste@example.com", "private_key": "fake"},
}

def game(game_id: str, home: str, away: str):
    return {
        "ID": game_id,
        "Data": "2026-08-01",
        "Hora": "18:00",
        "Código da liga": "MEX",
        "Liga": "México - Liga MX",
        "Mandante": home,
        "Visitante": away,
        "Casa de apostas": "PIXBET",
        "Odd mandante": 2.10,
        "Odd empate": 3.20,
        "Odd visitante": 3.40,
        "Odd mais de 2,5": 1.80,
        "Odd menos de 2,5": 2.00,
        "Odd ambas marcam — Sim": None,
        "Odd ambas marcam — Não": None,
    }

first = game("g-1", "Club America", "Tigres UANL")
second = game("g-2", "Monterrey", "Pachuca")
storage.registrar_evento_lote(secrets, tipo_evento="UPSERT", jogo=first, interface_version="V28.1.5.12")
storage.registrar_evento_lote(secrets, tipo_evento="UPSERT", jogo=second, interface_version="V28.1.5.12")
restored = storage.carregar_lote_pendente(secrets)
assert [item["ID"] for item in restored["Jogos"]] == ["g-1", "g-2"]
assert restored["Jogos"][0]["Casa de apostas"] == "PIXBET"

updated = dict(first)
updated["Odd mandante"] = 2.25
storage.registrar_evento_lote(secrets, tipo_evento="UPSERT", jogo=updated, interface_version="V28.1.5.12")
restored = storage.carregar_lote_pendente(secrets)
assert len(restored["Jogos"]) == 2
assert restored["Jogos"][0]["Odd mandante"] == 2.25

storage.registrar_evento_lote(secrets, tipo_evento="DELETE", jogo=first, interface_version="V28.1.5.12")
restored = storage.carregar_lote_pendente(secrets)
assert [item["ID"] for item in restored["Jogos"]] == ["g-2"]

storage.registrar_evento_lote(secrets, tipo_evento="CLEAR", interface_version="V28.1.5.12")
restored = storage.carregar_lote_pendente(secrets)
assert restored["Jogos"] == []
assert restored["Eventos encontrados"] == 5

sheet = spreadsheet.sheets["entrada_jogos"]
assert len(sheet.rows) == 5
assert [row[sheet.header.index("Tipo de evento")] for row in sheet.rows] == [
    "UPSERT", "UPSERT", "UPSERT", "DELETE", "CLEAR"
]
print("TESTE DE PERSISTÊNCIA DURÁVEL APPEND-ONLY V28.1.5.12: OK")
