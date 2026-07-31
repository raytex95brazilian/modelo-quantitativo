from __future__ import annotations

import re

import tex_v25_storage as storage


class FakeWorksheet:
    def __init__(self, title: str, rows: list[list] | None = None):
        self.title = title
        self.header = list(storage.COLUNAS_COTACOES)
        self.rows = [list(row) for row in (rows or [])]
        self.row_count = 20000
        self.update_calls = 0
        self.batch_update_calls = 0
        self.append_rows_calls = 0
        self.batch_get_calls = 0
        self.col_values_calls = 0

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
        self.append_rows_calls += 1
        start = len(self.rows) + 2
        self.rows.extend([list(row) for row in rows])
        end = len(self.rows) + 1
        last = storage._letra_coluna(len(self.header))
        return {"updates": {"updatedRange": f"'{self.title}'!A{start}:{last}{end}"}}

    def update(self, range_name, values, value_input_option=None):
        self.update_calls += 1
        if range_name.startswith("A1:"):
            self.header = list(values[0])
            return
        match = re.fullmatch(r"A(\d+):[A-Z]+(\d+)", range_name)
        assert match and match.group(1) == match.group(2), range_name
        idx = int(match.group(1)) - 2
        while len(self.rows) <= idx:
            self.rows.append([""] * len(self.header))
        self.rows[idx] = list(values[0])

    def batch_update(self, data, value_input_option=None):
        self.batch_update_calls += 1
        for item in data:
            match = re.fullmatch(r"A(\d+):[A-Z]+(\d+)", item["range"])
            assert match and match.group(1) == match.group(2), item["range"]
            idx = int(match.group(1)) - 2
            while len(self.rows) <= idx:
                self.rows.append([""] * len(self.header))
            self.rows[idx] = list(item["values"][0])
        return {"totalUpdatedRanges": len(data)}

    def get(self, range_name, value_render_option=None, date_time_render_option=None):
        match = re.fullmatch(r"[A-Z]+(\d+):[A-Z]+(\d+)", range_name)
        assert match, range_name
        start_row, end_row = int(match.group(1)), int(match.group(2))
        return [
            list(self.rows[row - 2])
            for row in range(start_row, end_row + 1)
            if 0 <= row - 2 < len(self.rows)
        ]

    def batch_get(self, ranges, value_render_option=None, date_time_render_option=None):
        self.batch_get_calls += 1
        return [self.get(item, value_render_option, date_time_render_option) for item in ranges]

    def col_values(self, number: int):
        self.col_values_calls += 1
        values = [self.header[number - 1]]
        values.extend(row[number - 1] if number - 1 < len(row) else "" for row in self.rows)
        return values

    def batch_format(self, formats):
        return None


class FakeSpreadsheet:
    def __init__(self, sheet: FakeWorksheet):
        self.sheet = sheet

    def worksheet(self, title: str):
        assert title == "catalogo_odds"
        return self.sheet


def reset(sheet: FakeWorksheet):
    storage._ABAS_GOOGLE.clear()
    storage._CABECALHOS_ATUAIS.clear()
    storage._CABECALHOS_SINCRONIZADOS.clear()
    storage._FORMATOS_NUMERICOS_SINCRONIZADOS.clear()
    storage._CHAVES_GRAVADAS_NO_PROCESSO.clear()
    storage._abrir_planilha = lambda secrets: FakeSpreadsheet(sheet)


secrets = {
    "google_sheets": {"spreadsheet_id": "planilha_teste_quota", "worksheet_catalogo": "catalogo_odds"},
    "gcp_service_account": {"client_email": "teste@example.com", "private_key": "fake"},
}


def records(total: int, observation: str):
    output = []
    for idx in range(total):
        record = {column: "" for column in storage.COLUNAS_COTACOES}
        record.update({
            "ID Coleta": f"id-{idx:04d}",
            "Jogo": f"Casa {idx} x Fora {idx}",
            "Cotação": 1.50 + (idx % 100) / 100,
            "Observação": observation,
        })
        output.append(record)
    return output


# Cenário real do erro: 210 cotações já existem e a análise precisa enriquecê-las.
initial = records(210, "antes")
initial_rows = [[record.get(column, "") for column in storage.COLUNAS_COTACOES] for record in initial]
sheet = FakeWorksheet("catalogo_odds", initial_rows)
reset(sheet)
enriched = records(210, "depois da análise")
assert storage.salvar_cotacoes(secrets, enriched) == 210
assert sheet.batch_update_calls == 1, sheet.batch_update_calls
assert sheet.update_calls == 0, sheet.update_calls
assert sheet.append_rows_calls == 0, sheet.append_rows_calls
assert sheet.batch_get_calls == 1, sheet.batch_get_calls
assert sheet.col_values_calls == 1, sheet.col_values_calls

# Cenário de inclusão: 210 linhas novas devem usar um único append_rows.
sheet_new = FakeWorksheet("catalogo_odds")
reset(sheet_new)
assert storage.salvar_cotacoes(secrets, initial) == 210
assert sheet_new.append_rows_calls == 1, sheet_new.append_rows_calls
assert sheet_new.batch_update_calls == 0, sheet_new.batch_update_calls
assert sheet_new.update_calls == 0, sheet_new.update_calls
assert sheet_new.batch_get_calls == 1, sheet_new.batch_get_calls
assert sheet_new.col_values_calls == 1, sheet_new.col_values_calls

print("TESTE DE GRAVAÇÃO EM LOTE E CONTROLE DE QUOTA V28.1.5.13: OK")
