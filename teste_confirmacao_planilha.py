from __future__ import annotations

import re

import tex_v25_storage as storage


class FakeWorksheet:
    def __init__(self, title: str, corrupt_odd: bool = False):
        self.title = title
        self.header: list[str] = []
        self.rows: list[list] = []
        self.corrupt_odd = corrupt_odd

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
        row = len(self.rows) + 1
        return {"updates": {"updatedRange": f"'{self.title}'!A{row}:T{row}"}}

    def append_rows(self, rows, value_input_option=None):
        for values in rows:
            current = list(values)
            if self.corrupt_odd and self.header and "Odd mandante" in self.header:
                current[self.header.index("Odd mandante")] = 9.99
            self.rows.append(current)
        row = len(self.rows) + 1
        return {"updates": {"updatedRange": f"'{self.title}'!A{row}:T{row}"}}

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

    def col_values(self, number: int):
        values = [self.header[number - 1]] if self.header else []
        values.extend(row[number - 1] if number - 1 < len(row) else "" for row in self.rows)
        return values

    def get_all_values(self):
        return [list(self.header)] + [list(row) for row in self.rows]


class FakeSpreadsheet:
    def __init__(self, corrupt_odd: bool = False):
        self.sheets: dict[str, FakeWorksheet] = {}
        self.corrupt_odd = corrupt_odd

    def worksheet(self, title: str):
        if title not in self.sheets:
            raise RuntimeError(f"worksheet not found: {title}")
        return self.sheets[title]

    def add_worksheet(self, title: str, rows: int, cols: int):
        sheet = FakeWorksheet(title, corrupt_odd=self.corrupt_odd)
        self.sheets[title] = sheet
        return sheet


def reset(spreadsheet: FakeSpreadsheet):
    storage._ABAS_GOOGLE.clear()
    storage._CABECALHOS_ATUAIS.clear()
    storage._CABECALHOS_SINCRONIZADOS.clear()
    storage._CHAVES_GRAVADAS_NO_PROCESSO.clear()
    storage._abrir_planilha = lambda secrets: spreadsheet


# Sem destino explícito, a V28.1.5.12 deve bloquear; não pode usar planilha legada oculta.
missing_destination = {
    "gcp_service_account": {"client_email": "teste@example.com", "private_key": "fake"},
}
assert storage.google_configurado(missing_destination) is False
assert storage.diagnostico_google(missing_destination)["spreadsheet_id"] == ""

secrets = {
    "google_sheets": {"spreadsheet_id": "planilha_teste_1234567890"},
    "gcp_service_account": {"client_email": "teste@example.com", "private_key": "fake"},
}

game = {
    "ID": "mx-001",
    "Data": "2026-08-01",
    "Hora": "18:00",
    "Código da liga": "MEX",
    "Liga": "México - Liga MX",
    "Mandante": "Club America",
    "Visitante": "Tigres UANL",
    "Casa de apostas": "PIXBET",
    "Odd mandante": 1.77,
    "Odd empate": 3.45,
    "Odd visitante": 4.80,
    "Odd mais de 2,5": 1.92,
    "Odd menos de 2,5": 1.84,
    "Odd ambas marcam — Sim": None,
    "Odd ambas marcam — Não": None,
}

spreadsheet = FakeSpreadsheet()
reset(spreadsheet)
confirmation = storage.registrar_evento_lote(
    secrets,
    tipo_evento="UPSERT",
    jogo=game,
    interface_version="V28.1.5.12",
)
assert confirmation["Verificação"] == "GRAVADO E RELIDO"
assert confirmation["Aba"] == "entrada_jogos"
assert confirmation["Linha"] == 2
assert float(confirmation["Cotações verificadas"]["Odd mandante"]) == 1.77
assert float(confirmation["Cotações verificadas"]["Odd mais de 2,5"]) == 1.92

# Se a planilha devolver uma cotação diferente, o app deve falhar e manter o formulário.
corrupt = FakeSpreadsheet(corrupt_odd=True)
reset(corrupt)
try:
    storage.registrar_evento_lote(
        secrets,
        tipo_evento="UPSERT",
        jogo=game,
        interface_version="V28.1.5.12",
    )
except RuntimeError as exc:
    assert "Odd mandante" in str(exc)
else:
    raise AssertionError("A divergência de cotação deveria ter bloqueado a confirmação.")

print("TESTE DE DESTINO EXPLÍCITO E LEITURA PÓS-GRAVAÇÃO V28.1.5.12: OK")
