# Relatório de correção — V28.1.5.7

## Problema confirmado

A V28.1.5.6 não continha literalmente o estado `AGUARDAR PREÇO`, mas ainda mantinha estados e indicadores equivalentes: `PREÇO FORTE`, `ELEGÍVEL PARA META`, `RESERVA`, cotação mínima e diferença para equilíbrio. Isso sugeria que o usuário deveria acompanhar odds futuras, embora o fluxo real seja de digitação manual única.

## Correção

- remoção dos estados de acompanhamento de cotação;
- decisão final baseada exclusivamente nos valores informados no lote;
- estados finais: `OPERAR`, `NÃO SELECIONADA`, `DESCARTAR`, `AMOSTRA INSUFICIENTE`, `FORA DA FAIXA` e `EXPERIMENTAL`;
- remoção de cotação mínima, diferença para admissibilidade e equilíbrio individual da interface e da Análise para IA;
- manutenção de cotação informada, cotação após desconto de 2% e EV conservador;
- manutenção integral do motor preditivo V28.1.2, modelo V28.0 e política de ranking da V28.1.5.6.

## Comportamento esperado

Depois de clicar em analisar, o lote não apresenta pedido de espera ou acompanhamento. Cada seleção recebe uma decisão fechada para as cotações digitadas naquele momento.
