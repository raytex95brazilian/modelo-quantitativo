from __future__ import annotations

import re

import tex_v25_storage as storage


class FakeWorksheet:
    def __init__(self, title: str):
        self.title = title
        self.header = list(storage.COLUNAS_COTACOES)
        self.rows: list[list] = []
        self.row_count = 20000
        self.formats: list[dict] = []

    def row_values(self, row: int):
        if row == 1:
            return list(self.header)
        idx = row - 2
        if not (0 <= idx < len(self.rows)):
            return []
        values = list(self.rows[idx])
        # Simula a máscara visual de data herdada no Google Sheets.
        cot = self.header.index("Cotação")
        if values[cot] == 3.44:
            values[cot] = "02.01"
        elif values[cot] == 1.80:
            values[cot] = "31.12"
        return values

    def append_rows(self, rows, value_input_option=None):
        start = len(self.rows) + 2
        self.rows.extend([list(row) for row in rows])
        end = len(self.rows) + 1
        last = storage._letra_coluna(len(self.header))
        return {"updates": {"updatedRange": f"'{self.title}'!A{start}:{last}{end}"}}

    def append_row(self, values, value_input_option=None):
        if not self.header:
            self.header = list(values)
        else:
            self.rows.append(list(values))

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

    def get(self, range_name, value_render_option=None, date_time_render_option=None):
        # Para UNFORMATTED_VALUE retorna o número bruto; sem a opção, simula o
        # valor visual da célula formatada como data.
        match = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", range_name)
        assert match, range_name
        start_row, end_row = int(match.group(2)), int(match.group(4))
        result = []
        for row_number in range(start_row, end_row + 1):
            idx = row_number - 2
            if not (0 <= idx < len(self.rows)):
                continue
            values = list(self.rows[idx])
            if value_render_option != "UNFORMATTED_VALUE":
                cot = self.header.index("Cotação")
                if values[cot] == 3.44:
                    values[cot] = "02.01"
                elif values[cot] == 1.80:
                    values[cot] = "31.12"
            result.append(values)
        return result

    def get_all_values(self, value_render_option=None):
        values = [list(self.header)]
        for row in self.rows:
            current = list(row)
            if value_render_option != "UNFORMATTED_VALUE":
                cot = self.header.index("Cotação")
                if current[cot] == 3.44:
                    current[cot] = "02.01"
                elif current[cot] == 1.80:
                    current[cot] = "31.12"
            values.append(current)
        return values

    def col_values(self, number: int):
        values = [self.header[number - 1]]
        values.extend(row[number - 1] if number - 1 < len(row) else "" for row in self.rows)
        return values

    def batch_format(self, formats):
        self.formats.extend(formats)


class FakeSpreadsheet:
    def __init__(self):
        self.sheet = FakeWorksheet("catalogo_odds")

    def worksheet(self, title: str):
        assert title == "catalogo_odds"
        return self.sheet


def reset(spreadsheet: FakeSpreadsheet):
    storage._ABAS_GOOGLE.clear()
    storage._CABECALHOS_ATUAIS.clear()
    storage._CABECALHOS_SINCRONIZADOS.clear()
    storage._FORMATOS_NUMERICOS_SINCRONIZADOS.clear()
    storage._CHAVES_GRAVADAS_NO_PROCESSO.clear()
    storage._abrir_planilha = lambda secrets: spreadsheet


secrets = {
    "google_sheets": {"spreadsheet_id": "planilha_teste_123", "worksheet_catalogo": "catalogo_odds"},
    "gcp_service_account": {"client_email": "teste@example.com", "private_key": "fake"},
}

records = []
for idx, odd in enumerate((3.44, 1.80), start=1):
    record = {column: "" for column in storage.COLUNAS_COTACOES}
    record.update({
        "ID Coleta": f"id-{idx}",
        "Mercado": "Resultado final 1X2",
        "Cotação": odd,
        "Jogo": f"Casa {idx} x Fora {idx}",
    })
    records.append(record)

spreadsheet = FakeSpreadsheet()
reset(spreadsheet)
saved = storage.salvar_cotacoes(secrets, records)
assert saved == 2
# Repetir após uma confirmação anterior não pode duplicar registros já
# existentes na aba, inclusive os gravados por uma versão que falhou depois do append.
storage._CHAVES_GRAVADAS_NO_PROCESSO.clear()
assert storage.salvar_cotacoes(secrets, records) == 0
assert len(spreadsheet.sheet.rows) == 2

# A máscara visual antiga produziria datas, mas a conferência precisa usar o
# valor bruto e aceitar a gravação.
assert spreadsheet.sheet.row_values(2)[storage.COLUNAS_COTACOES.index("Cotação")] == "02.01"
assert spreadsheet.sheet.row_values(3)[storage.COLUNAS_COTACOES.index("Cotação")] == "31.12"
assert spreadsheet.sheet.rows[0][storage.COLUNAS_COTACOES.index("Cotação")] == 3.44
assert spreadsheet.sheet.rows[1][storage.COLUNAS_COTACOES.index("Cotação")] == 1.80

loaded = storage.carregar_cotacoes(secrets)
assert float(loaded.iloc[0]["Cotação"]) == 3.44
assert float(loaded.iloc[1]["Cotação"]) == 1.80

cot_letter = storage._letra_coluna(storage.COLUNAS_COTACOES.index("Cotação") + 1)
assert any(item["range"].startswith(f"{cot_letter}2:") for item in spreadsheet.sheet.formats)

print("TESTE DE COTAÇÃO FORMATADA COMO DATA V28.1.5.11: OK")
