# Metodologia operacional — V28.3.15

## Motor

O motor preditivo permanece V28.1.2 — Estado Isolado, combinando mercado sem margem, modelo dinâmico de gols, árvores regularizadas e calibração fora da amostra.

## Portão esportivo

O filtro de 2018 é o único portão de elegibilidade. Jogos reprovados ou não avaliáveis continuam calculados e salvos, mas são proibidos em apostas simples e múltiplas.

## Política financeira

Não existe meta mínima de seleções. Uma partida aprovada pode gerar no máximo uma aposta individual: o mercado informado com maior valor esperado final não negativo. Nenhum mercado com valor esperado negativo é usado para completar quantidade.

A múltipla recebe, por partida aprovada, no máximo um mercado: o de maior probabilidade final entre as opções com cotação financeiramente favorável. Ela só é formada com pelo menos dois confrontos.

## Ambas marcam

O motor identifica que a base histórica não possui odds completas desse mercado. Essa limitação permanece visível na amostra e na confiança. Ainda assim, Ambas Marcam é um mercado operacionalmente elegível quando a cotação foi informada, o jogo passou no filtro de 2018 e o valor esperado final não é negativo.

## Evidência retrospectiva

Os artefatos antigos de meta semanal permanecem no pacote somente para auditoria histórica e não controlam a V28.3.15. Resultados passados não garantem desempenho futuro.
