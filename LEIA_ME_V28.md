# Tex Statistics V28.1.5.7

Interface operacional sobre o motor preditivo V28.1.2 — Estado Isolado.

## Decisão fechada

A cotação é informada manualmente uma única vez. O resultado do lote é final para aqueles valores: **OPERAR**, **NÃO SELECIONADA**, **DESCARTAR**, **AMOSTRA INSUFICIENTE**, **FORA DA FAIXA** ou **EXPERIMENTAL**.

Não existe orientação para aguardar mudança de cotação. Indicadores de cotação futura foram retirados da tela, das tabelas principais e da Análise para IA.

## Carteira semanal

- meta de cinco entradas;
- no máximo uma seleção por partida;
- faixa principal com EV conservador não negativo e unidade cheia;
- complemento até o piso rígido de -15% com meia unidade;
- Ambas Marcam permanece experimental e não entra na carteira validada.

O backtest da política de seleção é o mesmo da V28.1.5.6, pois esta revisão altera a decisão e a comunicação operacional, não os cálculos preditivos nem o ranking histórico.
