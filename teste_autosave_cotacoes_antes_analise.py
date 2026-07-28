from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

import tex_v25_storage as storage
from tex_v25_core import normalize_zip
from tex_v28_core_2812 import INPUT_COLUMNS, analyze_games, load_v28_model
from tex_v28_finance import identificador_registro


class FakeWorksheet:
    def __init__(self, title: str):
        self.title = title
        self.header = list(storage.COLUNAS_COTACOES)
        self.rows: list[list] = []
        self.row_count = 20000

    def row_values(self, row: int):
        if row == 1:
            return list(self.header)
        idx = row - 2
        return list(self.rows[idx]) if 0 <= idx < len(self.rows) else []

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
        match = re.fullmatch(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", range_name)
        assert match, range_name
        start_row, end_row = int(match.group(2)), int(match.group(4))
        result = []
        for row_number in range(start_row, end_row + 1):
            idx = row_number - 2
            if 0 <= idx < len(self.rows):
                result.append(list(self.rows[idx]))
        return result

    def col_values(self, number: int):
        values = [self.header[number - 1]]
        values.extend(row[number - 1] if number - 1 < len(row) else "" for row in self.rows)
        return values

    def batch_format(self, formats):
        return None


class FakeSpreadsheet:
    def __init__(self):
        self.sheet = FakeWorksheet("catalogo_odds")

    def worksheet(self, title: str):
        if title != "catalogo_odds":
            raise RuntimeError(f"worksheet not found: {title}")
        return self.sheet


def reset(spreadsheet: FakeSpreadsheet):
    storage._ABAS_GOOGLE.clear()
    storage._CABECALHOS_ATUAIS.clear()
    storage._CABECALHOS_SINCRONIZADOS.clear()
    storage._FORMATOS_NUMERICOS_SINCRONIZADOS.clear()
    storage._CHAVES_GRAVADAS_NO_PROCESSO.clear()
    storage._abrir_planilha = lambda secrets: spreadsheet


ROOT = Path(__file__).resolve().parent
secrets = {
    "google_sheets": {"spreadsheet_id": "planilha_teste_autosave", "worksheet_catalogo": "catalogo_odds"},
    "gcp_service_account": {"client_email": "teste@example.com", "private_key": "fake"},
}
game = {
    "ID": "jogo-autosave-001",
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
records = storage.criar_registros_cotacoes_digitadas(
    game,
    bankroll=1000.0,
    interface_version="V28.1.5.12",
    core_api_version="28.1.2",
    model_version="V28.0",
    core_name="Tex Statistics V28.1.2 — Estado Isolado",
    app_name="Tex Statistics V28.1.5.12",
)
assert len(records) == 5
assert all(record["Cotação"] for record in records)
assert all("antes da análise" in record["Observação"] for record in records)

spreadsheet = FakeSpreadsheet()
reset(spreadsheet)
assert storage.salvar_cotacoes(secrets, records) == 5
assert len(spreadsheet.sheet.rows) == 5

# Os IDs pré-análise devem ser exatamente os IDs produzidos pelo motor.
matches = normalize_zip(ROOT / "data" / "TEX_V22_DADOS_24_LIGAS.zip", include_incomplete_annual_2026=True)
model = load_v28_model(ROOT / "model")
games = pd.DataFrame([game], columns=INPUT_COLUMNS)
_, _, evaluations, _ = analyze_games(games, matches, model, 1000.0, 0.01, 5)
engine_ids = {identificador_registro(row) for row in evaluations.itertuples(index=False)}
assert {record["ID Coleta"] for record in records} == engine_ids

# A análise deve atualizar as mesmas cinco linhas, não acrescentar outras.
enriched = []
for record in records:
    current = dict(record)
    current["Probabilidade ajustada sem margem %"] = 51.23
    current["Observação"] = "Linha enriquecida após a análise."
    enriched.append(current)
assert storage.salvar_cotacoes(secrets, enriched) == 5
assert len(spreadsheet.sheet.rows) == 5
prob_index = spreadsheet.sheet.header.index("Probabilidade ajustada sem margem %")
obs_index = spreadsheet.sheet.header.index("Observação")
assert all(float(row[prob_index]) == 51.23 for row in spreadsheet.sheet.rows)
assert all(row[obs_index] == "Linha enriquecida após a análise." for row in spreadsheet.sheet.rows)

print("TESTE AUTOSAVE DE COTAÇÕES ANTES DA ANÁLISE V28.1.5.12: OK")
