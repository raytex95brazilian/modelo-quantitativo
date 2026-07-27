# Metodologia e backtest — V28.1.5.9

## Motor

O motor preditivo permanece V28.1.2 — Estado Isolado, combinando mercado sem margem, modelo dinâmico de gols, árvores regularizadas e calibração fora da amostra.

## Política semanal

A política busca cinco seleções por semana, no máximo uma por partida. Seleções com EV conservador não negativo usam uma unidade; complementos admissíveis até -15% usam meia unidade.

## Cotação informada

A decisão é fechada no momento da análise com as odds digitadas pelo usuário. O sistema não orienta acompanhamento posterior, não cria estado de espera e não exibe valores destinados a uma atualização futura.

## Evidência retrospectiva

A revisão V28.1.5.9 não modifica o ranking ou o backtest da política V28.1.5.6. Os arquivos retrospectivos permanecem no diretório `backtest/`. Resultados históricos não garantem desempenho futuro e dependem das cotações efetivamente utilizadas.
