import tex_v28_core_2812 as module

assert module.CORE_API_VERSION == "28.1.2"
for name in ("analyze_games", "build_ai_summary", "display_frame", "load_v28_model", "lot_fingerprint", "validate_market_odds"):
    assert hasattr(module, name), name

assert abs(module.validate_market_odds("1X2", [1.99, 3.24, 3.87]) - (1/1.99 + 1/3.24 + 1/3.87)) < 1e-12
try:
    module.validate_market_odds("1X2", [1.99, 4.55, 7.30])
except ValueError:
    pass
else:
    raise AssertionError("Linha contaminada deveria ser bloqueada")

print("V28.1.2: importação e validação de odds aprovadas")
