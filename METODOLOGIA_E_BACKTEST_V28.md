# Tex Statistics V28 — metodologia e avaliações retrospectivas

## Arquitetura do motor

Para cada seleção, o sistema:

1. valida se todas as cotações do mercado pertencem à mesma linha e têm margem implícita plausível;
2. remove proporcionalmente a margem do mercado;
3. estima probabilidades esportivas com um modelo dinâmico de gols, forças de ataque e defesa, mando e ponderação temporal;
4. combina as variáveis pré-jogo em um modelo de árvores regularizadas executado por inferência pura em Python;
5. localiza casos semelhantes nas previsões fora da amostra;
6. calcula um limite inferior de Wilson unilateral para a taxa de acerto desses casos;
7. define a probabilidade conservadora como o menor valor entre a probabilidade do modelo e esse limite inferior;
8. aplica desconto operacional de 2% à cotação informada;
9. exige valor esperado conservador não negativo, amostra suficiente e estabilidade aceitável;
10. mantém no máximo uma seleção por partida e respeita o máximo semanal restante.

## Variáveis do modelo treinado

O artefato V28.0 usa apenas informações disponíveis antes da partida:

- probabilidade de mercado sem margem;
- probabilidade esportiva bruta;
- diferença, módulo da diferença e razão entre probabilidades;
- cotação;
- transformações logarítmicas das probabilidades;
- mês;
- liga, mercado e seleção codificados.

Os perfis de confiabilidade não entram como variáveis do modelo treinado. Eles são usados posteriormente como camada operacional conservadora.

## Avaliação progressiva original

O modelo foi avaliado por temporadas:

- 2022 treinado em 2018–2021;
- 2023 treinado em 2018–2022;
- 2024 treinado em 2018–2023;
- 2025 treinado em 2018–2024.

Protocolo original: unidade fixa, uma seleção por jogo, até quatro entradas por semana, melhor preço disponível com desconto de 2%.

Resultado registrado no pacote original:

- 893 entradas;
- 225 semanas;
- 3,97 entradas por semana;
- 461 vitórias;
- 51,62% de acerto;
- +103,7482 unidades;
- retorno sobre entradas de +11,62%;
- maior recuo de 14,094 unidades.

### Sensibilidade ao preço do protocolo original

| Protocolo | Entradas | Retorno sobre entradas | Maior recuo |
|---|---:|---:|---:|
| Melhor preço, menos 2% | 893 | +11,62% | 14,09 u |
| Pinnacle, menos 2% | 812 | +4,36% | 20,72 u |
| Bet365, menos 2% | 686 | +2,85% | 20,06 u |
| Cotação média, sem desconto | 884 | +2,27% | 22,90 u |
| Cotação média, menos 2% | 860 | −3,06% | 30,81 u |

Essa sensibilidade demonstra que preço competitivo é parte essencial do método.

## Recalculo operacional do filtro conservador V28.1.5

O arquivo `backtest_v28_conservador.py` reaplica a camada conservadora às previsões fora da amostra já existentes, com máximo de cinco entradas semanais. O resultado armazenado em `backtest/V28_1_5_FILTRO_CONSERVADOR_RESUMO.json` é:

- 1.059 entradas;
- 221 semanas;
- média de 4,79 entradas por semana;
- 588 vitórias;
- 55,52% de acerto;
- +134,5910 unidades;
- retorno sobre entradas de +12,71%;
- maior recuo de 24,4098 unidades.

| Temporada | Entradas | Acerto | Lucro | Retorno sobre entradas |
|---|---:|---:|---:|---:|
| 2022 | 306 | 54,58% | +43,1936 u | +14,12% |
| 2023 | 240 | 59,58% | +38,3494 u | +15,98% |
| 2024 | 244 | 56,15% | +37,2306 u | +15,26% |
| 2025 | 269 | 52,42% | +15,8174 u | +5,88% |

### Advertência metodológica

Esse recalculo é uma verificação operacional retrospectiva, não um novo teste final independente. Os perfis de confiabilidade agregam previsões fora da amostra de 2022–2025; por isso, o mesmo período não deve ser apresentado como validação inédita da camada conservadora. Uma validação final adequada exige dados futuros ainda não usados para ajustar ou escolher o filtro.

## Ambas Marcam

O sistema calcula Ambas Marcam — Sim/Não como sinal complementar, usando mercado e probabilidade esportiva. Esse mercado não participa da carteira automática porque a base das 24 ligas não contém histórico completo de cotações para uma avaliação financeira equivalente à de 1X2 e Mais/Menos 2,5.

## Limitações

- Nenhuma probabilidade garante o resultado de uma partida.
- Resultados retrospectivos podem não se repetir.
- Cotações piores reduzem ou eliminam a vantagem estimada.
- Escalações, lesões, suspensões, clima e informações táticas não são automatizados.
- A fonte externa pode ficar indisponível; nesse caso, o aplicativo usa a base local.
- A carteira só respeita apostas históricas que estejam presentes no controle financeiro sincronizado.
- O arquivo local do Streamlit não deve ser tratado como armazenamento permanente.
