from __future__ import annotations

import re

import tex_v25_storage as storage


class FakeEventWorksheet:
    def __init__(self):
        self.title = "entrada_jogos"
        self.id = 777
        self.header = list(storage.COLUNAS_EVENTOS_LOTE)
        self.rows: list[list] = []
        self.append_rows_calls = 0
        self.batch_get_calls = 0
        self.col_values_calls = 0

    def append_rows(self, rows, value_input_option=None):
        self.append_rows_calls += 1
        start = len(self.rows) + 2
        self.rows.extend([list(row) for row in rows])
        end = len(self.rows) + 1
        last = storage._letra_coluna(len(self.header))
        return {"updates": {"updatedRange": f"'entrada_jogos'!A{start}:{last}{end}"}}

    def batch_get(self, ranges, value_render_option=None, date_time_render_option=None):
        self.batch_get_calls += 1
        output = []
        for range_name in ranges:
            match = re.fullmatch(r"A(\d+):[A-Z]+(\d+)", range_name)
            assert match and match.group(1) == match.group(2), range_name
            row = int(match.group(1))
            output.append([list(self.rows[row - 2])])
        return output

    def col_values(self, number):
        self.col_values_calls += 1
        return [self.header[number - 1]] + [row[number - 1] for row in self.rows]


sheet = FakeEventWorksheet()
old_config = storage.configuracao_google
old_get = storage._obter_aba_cacheada
old_url = storage.url_planilha_configurada
try:
    storage.configuracao_google = lambda secrets: {
        "configurado": True,
        "spreadsheet_id": "teste-v2830",
        "client_email": "teste@example.com",
        "worksheet_eventos_lote": "entrada_jogos",
    }
    storage._obter_aba_cacheada = lambda secrets, title, columns: sheet
    storage.url_planilha_configurada = lambda secrets: "https://docs.google.com/spreadsheets/d/teste/edit"
    storage._CABECALHOS_ATUAIS[("teste-v2830", "teste@example.com", "entrada_jogos")] = list(storage.COLUNAS_EVENTOS_LOTE)

    games = []
    for index in range(20):
        games.append({
            "ID": f"game-{index}",
            "Data": "2026-08-08",
            "Hora": f"{10 + index // 2:02d}:{(index % 2) * 30:02d}",
            "Código da liga": "BRA",
            "Liga": "Brasileirão Série A",
            "Mandante": f"Casa {index}",
            "Visitante": f"Fora {index}",
            "Casa de apostas": "PIXBET",
            "Odd mandante": 2.10,
            "Odd empate": 3.20,
            "Odd visitante": 3.40,
            "Odd mais de 2,5": None,
            "Odd menos de 2,5": None,
            "Odd ambas marcam — Sim": None,
            "Odd ambas marcam — Não": None,
        })

    result = storage.registrar_eventos_lote({}, games, interface_version="V28.3.0")
    assert result["Eventos confirmados"] == 20, result
    assert result["Verificação"] == "GRAVADO E RELIDO EM LOTE", result
    assert result["Primeira linha"] == 2 and result["Última linha"] == 21, result
    assert sheet.append_rows_calls == 1, sheet.append_rows_calls
    assert sheet.batch_get_calls == 1, sheet.batch_get_calls
    assert sheet.col_values_calls == 0, sheet.col_values_calls
finally:
    storage.configuracao_google = old_config
    storage._obter_aba_cacheada = old_get
    storage.url_planilha_configurada = old_url

print("TESTE DE EVENTOS EM LOTE V28.3.0: OK")
