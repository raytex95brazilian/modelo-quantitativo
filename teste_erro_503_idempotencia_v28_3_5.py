from __future__ import annotations

import re

import tex_v25_storage as storage


class Fake503(Exception):
    pass


class Worksheet503AfterCommit:
    def __init__(self):
        self.id = 503
        self.header = list(storage.COLUNAS_EVENTOS_LOTE)
        self.rows: list[list] = []
        self.append_rows_calls = 0
        self.col_values_calls = 0
        self.batch_get_calls = 0

    def append_rows(self, rows, value_input_option=None):
        self.append_rows_calls += 1
        # Simula o caso crítico: o Google grava, mas a resposta chega como 503.
        self.rows.extend([list(row) for row in rows])
        if self.append_rows_calls == 1:
            raise Fake503("APIError: [503]: The service is currently unavailable.")
        start = len(self.rows) - len(rows) + 2
        end = len(self.rows) + 1
        last = storage._letra_coluna(len(self.header))
        return {"updates": {"updatedRange": f"'entrada_jogos'!A{start}:{last}{end}"}}

    def col_values(self, number):
        self.col_values_calls += 1
        return [self.header[number - 1]] + [
            row[number - 1] if number - 1 < len(row) else "" for row in self.rows
        ]

    def batch_get(self, ranges, value_render_option=None, date_time_render_option=None):
        self.batch_get_calls += 1
        output = []
        for range_name in ranges:
            match = re.fullmatch(r"A(\d+):[A-Z]+(\d+)", range_name)
            assert match and match.group(1) == match.group(2), range_name
            row = int(match.group(1))
            output.append([list(self.rows[row - 2])])
        return output


# 1) Leituras/operações idempotentes repetem 503 e depois concluem.
old_sleep = storage.time.sleep
old_jitter = storage.random.uniform
storage.time.sleep = lambda _: None
storage.random.uniform = lambda _a, _b: 0.0
try:
    calls = {"n": 0}

    def transient_then_ok():
        calls["n"] += 1
        if calls["n"] < 3:
            raise Fake503("APIError: [503]: The service is currently unavailable.")
        return "ok"

    assert storage._executar_com_backoff(transient_then_ok, operacao="teste 503") == "ok"
    assert calls["n"] == 3, calls

    # 2) Append que foi aplicado antes do 503 não é repetido nem duplicado.
    sheet = Worksheet503AfterCommit()
    old_config = storage.configuracao_google
    old_get = storage._obter_aba_cacheada
    old_url = storage.url_planilha_configurada
    try:
        storage.configuracao_google = lambda secrets: {
            "configurado": True,
            "spreadsheet_id": "teste-v2835",
            "client_email": "teste@example.com",
            "worksheet_eventos_lote": "entrada_jogos",
        }
        storage._obter_aba_cacheada = lambda secrets, title, columns: sheet
        storage.url_planilha_configurada = lambda secrets: "https://docs.google.com/spreadsheets/d/teste/edit"
        storage._CABECALHOS_ATUAIS[("teste-v2835", "teste@example.com", "entrada_jogos")] = list(
            storage.COLUNAS_EVENTOS_LOTE
        )

        games = [
            {
                "ID": f"game-{index}",
                "Data": "2026-08-08",
                "Hora": f"{16 + index:02d}:00",
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
            }
            for index in range(3)
        ]

        result = storage.registrar_eventos_lote({}, games, interface_version="V28.3.5")
        assert result["Eventos confirmados"] == 3, result
        assert result["Verificação"] == "GRAVADO E RELIDO EM LOTE", result
        assert sheet.append_rows_calls == 1, sheet.append_rows_calls
        assert len(sheet.rows) == 3, len(sheet.rows)
        event_index = sheet.header.index("ID Evento")
        ids = [row[event_index] for row in sheet.rows]
        assert len(ids) == len(set(ids)) == 3, ids
        assert sheet.col_values_calls >= 1, sheet.col_values_calls
        assert sheet.batch_get_calls == 1, sheet.batch_get_calls
    finally:
        storage.configuracao_google = old_config
        storage._obter_aba_cacheada = old_get
        storage.url_planilha_configurada = old_url
finally:
    storage.time.sleep = old_sleep
    storage.random.uniform = old_jitter

print("TESTE DE ERRO 503 E APPEND IDEMPOTENTE V28.3.5: OK")
