from __future__ import annotations

# Cenário extraído do resumo enviado pelo usuário.
# A fórmula é a mesma da V28.1.4:
# probabilidade corrigida = (acertos + 100 * probabilidade original) / (amostra + 100)

cases = [
    ("Santos", 0.718, 955, 0.739, 1.40, True),
    ("Flamengo", 0.707, 955, 0.739, 1.47, True),
    ("Bragantino", 0.624, 133, 0.684, 1.60, True),
    ("Athletico-PR x Internacional — Menos de 2,5", 0.611, 1838, 0.595, 1.61, False),
    ("Vasco x Mirassol — Menos de 2,5", 0.562, 3092, 0.576, 1.74, False),
    ("Cruzeiro", 0.559, 188, 0.532, 1.74, False),
    ("Bahia", 0.472, 192, 0.458, 2.08, False),
    ("Grêmio x Fluminense — Menos de 2,5", 0.528, 3464, 0.517, 1.84, False),
    ("Palmeiras x Atlético-MG — Mais de 2,5", 0.497, 3432, 0.481, 2.00, False),
    ("Remo x Vitória — Menos de 2,5", 0.549, 3464, 0.517, 1.75, False),
]

authorized = []
for name, original, sample, hit_rate, quote, expected_authorized in cases:
    wins = round(sample * hit_rate)
    corrected = (wins + 100 * original) / (sample + 100)
    expected_value = corrected * quote * 0.98 - 1
    is_authorized = expected_value >= 0
    assert is_authorized is expected_authorized, (name, corrected, expected_value)
    if is_authorized:
        authorized.append((name, corrected, expected_value))

assert [item[0] for item in authorized] == ["Santos", "Flamengo", "Bragantino"]
print("Cenário de dez jogos: 3 leituras principais recuperadas pela correção histórica.")
for name, probability, value in authorized:
    print(f"- {name}: probabilidade corrigida {probability:.2%}; valor esperado {value:.2%}")
print("Ambas Marcam é calculado separadamente no app com reconstrução histórica e pode acrescentar ou não novas entradas.")
