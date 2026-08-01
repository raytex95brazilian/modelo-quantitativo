import hashlib
import json

import tex_v25_storage as storage

EXPECTED = {
    "COLUNAS_COTACOES": (53, "d52f80f16a25664b98a228ce9a5f471625dbe1034e64248523117af70c692b5a"),
    "COLUNAS_ANALISES": (80, "b3a1994b1bdead08084f11e54064357669607388d0d22927ab2b0f048fd5c8b9"),
    "COLUNAS_EVENTOS_LOTE": (21, "f22915ff34b5ba14176c3e8800fceb50ec1c34119debbab84518a5219bcec2c1"),
    "COLUNAS_LOTE_PENDENTE": (6, "0c28185c0952ae78d4178302d3000873815133099ffc54fe790c8d231d7fc84f"),
}

for name, (expected_length, expected_hash) in EXPECTED.items():
    columns = getattr(storage, name)
    digest = hashlib.sha256(
        json.dumps(columns, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert len(columns) == expected_length, (name, len(columns), expected_length)
    assert digest == expected_hash, (name, digest, expected_hash)

print("TESTE DE COMPATIBILIDADE DAS COLUNAS V28.3.0: OK")
