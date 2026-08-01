from __future__ import annotations

import re

import tex_v25_storage as storage


class FakeWorksheet:
    def __init__(self):
        self.title = "catalogo_odds"
        self.header = list(storage.COLUNAS_COTACOES)
        self.rows: list[list] = []
        self.row_count = 20000

    def row_values(self, row: int):
        return list(self.header) if row == 1 else list(self.rows[row - 2])

    def append_rows(self, rows, value_input_option=None):
        start = len(self.rows) + 2
        self.rows.extend([list(row) for row in rows])
        end = len(self.rows) + 1
        last = storage._letra_coluna(len(self.header))
        return {"updates": {"updatedRange": f"'{self.title}'!A{start}:{last}{end}"}}

    def col_values(self, number: int):
        values = [self.header[number - 1]]
        values.extend(row[number - 1] if number - 1 < len(row) else "" for row in self.rows)
        return values

    def batch_get(self, ranges, value_render_option=None, date_time_render_option=None):
        blocks = []
        for range_name in ranges:
            match = re.fullmatch(r"A(\d+):[A-Z]+(\d+)", range_name)
            assert match and match.group(1) == match.group(2), range_name
            row = list(self.rows[int(match.group(1)) - 2])
            # Simula UNFORMATTED_VALUE: o Google devolve 17, e não 17.0.
            row = [int(value) if isinstance(value, float) and value.is_integer() else value for value in row]
            blocks.append([row])
        return blocks

    def batch_format(self, formats):
        integer_names = storage.COLUNAS_INTEIRAS_PLANILHA
        by_range = {item["range"]: item["format"]["numberFormat"]["pattern"] for item in formats}
        for index, name in enumerate(self.header, start=1):
            if name in integer_names:
                letter = storage._letra_coluna(index)
                assert by_range[f"{letter}2:{letter}{self.row_count}"] == "0"


class FakeSpreadsheet:
    def __init__(self, sheet):
        self.sheet = sheet

    def worksheet(self, title: str):
        assert title == "catalogo_odds"
        return self.sheet


def reset(sheet):
    storage._ABAS_GOOGLE.clear()
    storage._CABECALHOS_ATUAIS.clear()
    storage._CABECALHOS_SINCRONIZADOS.clear()
    storage._FORMATOS_NUMERICOS_SINCRONIZADOS.clear()
    storage._CHAVES_GRAVADAS_NO_PROCESSO.clear()
    storage._abrir_planilha = lambda secrets: FakeSpreadsheet(sheet)


secrets = {
    "google_sheets": {"spreadsheet_id": "teste-v2831", "worksheet_catalogo": "catalogo_odds"},
    "gcp_service_account": {"client_email": "teste@example.com", "private_key": "fake"},
}

sheet = FakeWorksheet()
reset(sheet)
record = {column: "" for column in storage.COLUNAS_COTACOES}
record.update({
    "ID Coleta": "TEX-TESTE-NUMERICO",
    "Temporada": 2026,
    "Posição do mandante": 17.0,
    "Posição do visitante": 12.0,
    "Pontos do mandante": 19.0,
    "Pontos do visitante": 10.0,
    "Cotação": 2.32,
})

assert storage.STORAGE_API_VERSION == "28.3.1"
assert storage.salvar_cotacoes(secrets, [record]) == 1
assert storage._celula_equivalente(17.0, 17)
assert storage._celula_equivalente(17.0, 17, numerico=True)
assert not storage._celula_equivalente("Equipe 01", "Equipe 1")
print("TESTE DE CONFERÊNCIA NUMÉRICA V28.3.1: OK")
