# Tex Statistics V28 — metodologia e backtest

## Problema corrigido

A V25 tentava decidir cada mercado por um portão rígido e independente. Isso produziu semanas vazias e uma discrepância entre o relatório histórico e o comportamento do aplicativo. A V28 troca esse desenho por **ranqueamento de carteira**:

1. calcula o mercado sem margem;
2. estima a força esportiva com Poisson dinâmico e pesos temporais;
3. entrega essas informações a um modelo de boosting regularizado;
4. estima a probabilidade de retorno de cada seleção;
5. desconta 2% da odd informada;
6. elimina EV negativo e odds fora de 1,20–3,00;
7. mantém uma seleção por partida;
8. seleciona as quatro melhores por semana, configurável entre três e cinco.

## Fundamentação usada

- Modelo de gols com fatores de ataque, defesa e mando de campo.
- Atualização temporal das forças das equipes, evitando tratar uma temporada inteira como estática.
- Probabilidades de 1X2 e totais derivadas de contagens de gols.
- Boosting regularizado para corrigir erros sistemáticos do mercado e do Poisson sem substituir a informação das odds.
- Avaliação fora da amostra, por temporada, sem usar resultados futuros na previsão.
- Regularização para reduzir sobreajuste.

## Variáveis do modelo

Somente variáveis disponíveis antes do jogo:

- probabilidade sem margem do mercado;
- probabilidade do Poisson dinâmico;
- diferença e razão entre as duas probabilidades;
- odd do mercado;
- transformações logit;
- mês;
- liga, mercado e lado.

Foram deliberadamente excluídas `CalP`, `Rel` e `N` dos modelos anteriores porque poderiam carregar perfis ajustados com períodos posteriores.

## Protocolo walk-forward

- Teste: 2022–2025.
- 2022 treinado em 2018–2021.
- 2023 treinado em 2018–2022.
- 2024 treinado em 2018–2023.
- 2025 treinado em 2018–2024.
- Unidade fixa de uma unidade.
- Uma seleção por jogo.
- Quatro entradas por semana, quando existem preços com EV não negativo.
- Odd efetiva = melhor odd registrada × 0,98.

## Resultado principal

- 893 entradas.
- 225 semanas.
- 3,97 entradas por semana.
- 461 vitórias.
- 51,62% de acerto.
- +103,7482 unidades.
- ROI +11,62%.
- Drawdown máximo 14,094 unidades.
- Maior sequência: 9 derrotas.
- Bootstrap semanal de 95% do ROI: aproximadamente +4,31% a +19,36%.
- Todas as temporadas testadas terminaram positivas.

## Resultado por temporada

| Temporada | Entradas | Acerto | Lucro | ROI |
|---|---:|---:|---:|---:|
| 2022 | 257 | 53,31% | +45,6044 u | +17,74% |
| 2023 | 208 | 54,33% | +35,5496 u | +17,09% |
| 2024 | 202 | 50,00% | +11,3068 u | +5,60% |
| 2025 | 226 | 48,67% | +11,2874 u | +4,99% |

## Teste de preço

O resultado depende de cotações competitivas:

| Protocolo | Entradas | ROI | Drawdown |
|---|---:|---:|---:|
| Melhor preço, menos 2% | 893 | +11,62% | 14,09 u |
| Pinnacle, menos 2% | 812 | +4,36% | 20,72 u |
| Bet365, menos 2% | 686 | +2,85% | 20,06 u |
| Odd média, sem desconto | 884 | +2,27% | 22,90 u |
| Odd média, menos 2% | 860 | −3,06% | 30,81 u |

Por isso, o aplicativo não libera uma seleção apenas porque o jogo parece provável: compara a odd digitada com a odd mínima. O alvo de três a cinco entradas é um **alvo de carteira**, não uma autorização para fabricar apostas com EV negativo.

## Ambas marcam

O aplicativo calcula e exibe Ambas Marcam — Sim/Não, mas não o inclui na carteira principal. A base histórica das 24 ligas não possui odds completas desse mercado para um backtest financeiro equivalente. O status permanece `EXPERIMENTAL` até existir essa evidência.

## Limitações

- Backtest não garante lucro futuro.
- O resultado principal usa melhor preço de fechamento; preço pior degrada o retorno.
- Escalações, suspensões, clima e informações táticas não estão automatizadas.
- O período 2022–2025 já foi usado para desenvolvimento e não deve ser reutilizado como teste final depois de novas alterações.
