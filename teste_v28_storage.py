import re

import tex_v25_storage as storage
from tex_v28_finance import COLUNAS_APOSTAS


class FakeWorksheet:
    def __init__(self):
        self.header = ["Campo antigo", "Observação antiga"]
        self.rows = []

    def row_values(self, row):
        if row == 1:
            return list(self.header)
        index = row - 2
        return list(self.rows[index]) if 0 <= index < len(self.rows) else []

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
        row_index = int(match.group(1)) - 2
        while len(self.rows) <= row_index:
            self.rows.append([""] * len(self.header))
        self.rows[row_index] = list(values[0])

    def append_rows(self, rows, value_input_option=None):
        self.rows.extend([list(row) for row in rows])

    def col_values(self, number):
        values = [self.header[number - 1]]
        values.extend(row[number - 1] if number - 1 < len(row) else "" for row in self.rows)
        return values

    def get_all_values(self):
        return [list(self.header)] + [list(row) for row in self.rows]


class FakeSpreadsheet:
    def __init__(self, worksheet):
        self.sheet = worksheet

    def worksheet(self, title):
        return self.sheet


worksheet = FakeWorksheet()
spreadsheet = FakeSpreadsheet(worksheet)
storage._ABAS_GOOGLE.clear()
storage._CABECALHOS_ATUAIS.clear()
storage._CABECALHOS_SINCRONIZADOS.clear()
storage._CHAVES_GRAVADAS_NO_PROCESSO.clear()
storage._abrir_planilha = lambda secrets: spreadsheet

secrets = {
    "google_sheets": {"spreadsheet_id": "teste", "worksheet_auditoria": "auditoria_entradas"},
    "gcp_service_account": {"client_email": "teste@example.com", "private_key": "fake"},
}

record = {column: "" for column in COLUNAS_APOSTAS}
record.update(
    {
        "ID Aposta": "TEX-123",
        "Jogo": "Casa x Fora",
        "Grupo do mercado": "1X2",
        "Código da seleção": "H",
        "Cotação": 2.0,
        "Entrada (R$)": 10.0,
        "Situação da liquidação": "PENDENTE",
        "Resultado da aposta": "PENDENTE",
    }
)
saved = storage.salvar_apostas(secrets, [record])
assert saved == 1
assert worksheet.header[:2] == ["Campo antigo", "Observação antiga"]
assert all(column in worksheet.header for column in COLUNAS_APOSTAS)
assert len(worksheet.rows) == 1
row = worksheet.rows[0]
assert row[worksheet.header.index("ID Aposta")] == "TEX-123"
assert row[worksheet.header.index("Jogo")] == "Casa x Fora"
assert storage.identificadores_apostas(secrets) == {"TEX-123"}

updated = storage.liquidar_aposta(secrets, "TEX-123", 2, 1, "Teste em lote")
assert updated["Resultado da aposta"] == "GANHA"
assert worksheet.rows[0][worksheet.header.index("Situação da liquidação")] == "LIQUIDADA"
assert float(worksheet.rows[0][worksheet.header.index("Lucro ou prejuízo (R$)")]) == 10.0
# O lote bruto é salvo imediatamente e pode ser restaurado após perda da sessão.
games = [
    {
        "ID": "mx-1",
        "Data": "2026-07-30",
        "Hora": "21:00",
        "Código da liga": "MEX",
        "Liga": "México - Liga MX",
        "Mandante": "Club America",
        "Visitante": "Tigres UANL",
        "Casa de apostas": "PIXBET",
        "Odd mandante": 2.10,
        "Odd empate": 3.20,
        "Odd visitante": 3.40,
    }
]
snapshot = storage.salvar_lote_pendente(
    secrets, games, interface_version="V28.1.5.11"
)
assert snapshot["Quantidade de partidas"] == 1
restored = storage.carregar_lote_pendente(secrets)
assert restored["Jogos"] == games
assert restored["Versão da interface"] == "V28.1.5.11"

# Atualizar o lote sobrescreve o snapshot atual em vez de depender da sessão.
storage.salvar_lote_pendente(secrets, [], interface_version="V28.1.5.11")
restored_empty = storage.carregar_lote_pendente(secrets)
assert restored_empty["Jogos"] == []

print("TESTE DE ARMAZENAMENTO, AUTOSAVE, RESTAURAÇÃO E LIQUIDAÇÃO: OK")
