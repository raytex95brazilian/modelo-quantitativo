from __future__ import annotations

import re
import tex_v25_storage as storage


class FakeEventWorksheet:
    def __init__(self):
        self.title = "entrada_jogos"
        self.id = 778
        self.header = list(storage.COLUNAS_EVENTOS_LOTE)
        self.rows: list[list] = []
        self.append_rows_calls = 0
        self.batch_get_calls = 0

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
        return [self.header[number - 1]] + [row[number - 1] for row in self.rows]


sheet = FakeEventWorksheet()
old_config = storage.configuracao_google
old_get = storage._obter_aba_cacheada
old_url = storage.url_planilha_configurada
try:
    storage.configuracao_google = lambda secrets: {
        "configurado": True,
        "spreadsheet_id": "teste-v2836",
        "client_email": "teste@example.com",
        "worksheet_eventos_lote": "entrada_jogos",
    }
    storage._obter_aba_cacheada = lambda secrets, title, columns: sheet
    storage.url_planilha_configurada = lambda secrets: "https://docs.google.com/spreadsheets/d/teste/edit"
    storage._CABECALHOS_ATUAIS[("teste-v2836", "teste@example.com", "entrada_jogos")] = list(storage.COLUNAS_EVENTOS_LOTE)

    games = [{
        "ID": "mex-1",
        "Data": "2026-08-15",
        "Hora": "20:00",
        "Código da liga": "MEX",
        "Liga": "México - Liga MX",
        "Mandante": "Atlante",
        "Visitante": "Toluca",
        "Casa de apostas": "PIXBET",
        "Odd mandante": 5.10,
        "Odd empate": 3.62,
        "Odd visitante": 1.48,
        "Odd mais de 2,5": None,
        "Odd menos de 2,5": None,
        "Odd ambas marcam — Sim": None,
        "Odd ambas marcam — Não": None,
    }]

    result = storage.registrar_eventos_lote(
        {}, games, interface_version="V28.3.7", substituir_lote=True
    )
    assert result["Eventos confirmados"] == 2, result
    assert result["Partidas confirmadas"] == 1, result
    assert result["Lote substituído"] is True, result
    type_index = sheet.header.index("Tipo de evento")
    assert sheet.rows[0][type_index] == "CLEAR", sheet.rows[0]
    assert sheet.rows[1][type_index] == "UPSERT", sheet.rows[1]
    assert sheet.append_rows_calls == 1
    assert sheet.batch_get_calls == 1
finally:
    storage.configuracao_google = old_config
    storage._obter_aba_cacheada = old_get
    storage.url_planilha_configurada = old_url

print("TESTE DE SUBSTITUIÇÃO DE LOTE V28.3.7: OK")
