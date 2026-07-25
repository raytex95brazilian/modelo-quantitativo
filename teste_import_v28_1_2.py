import tex_v28_core as compat
import tex_v28_core_2812 as core

assert core.CORE_API_VERSION == "28.1.2"
assert compat.CORE_API_VERSION == core.CORE_API_VERSION
assert compat.MODEL_VERSION == core.MODEL_VERSION
for name in (
    "analyze_games", "build_ai_summary", "display_frame", "load_v28_model",
    "lot_fingerprint", "validate_market_odds",
):
    assert hasattr(core, name), name
    assert hasattr(compat, name), name
    assert name in core.__all__, name
print("TESTE DE IMPORTAÇÃO V28.1.2 ISOLADA: OK")
