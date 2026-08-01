# Relatório técnico — Tex Statistics V28.3.1

## Falha observada

O Google Sheets confirmou a gravação, mas devolveu posições e pontos inteiros sem a parte decimal. A aplicação enviava, por exemplo, `17.0` e recebia `17`. A comparação textual da V28.3.0 interpretava os valores equivalentes como divergentes.

## Correção

- `Posição do mandante`, `Posição do visitante`, `Pontos do mandante`, `Pontos do visitante`, temporada, amostras e contagens do filtro passaram a ter comparação numérica.
- Números reais equivalentes também são aceitos quando o tipo muda de `float` para `int`.
- As colunas inteiras recebem padrão visual `0`; odds e probabilidades continuam com `0.00`.
- O aviso principal de salvamento ficou curto; a mensagem integral fica em “Detalhes técnicos do salvamento”.
- O armazenamento passa à API `28.3.1`; o importador 1X2 permanece na API `28.3.0`, sem alteração de comportamento.

## Efeito sobre dados já gravados

A mensagem anterior era um falso negativo de conferência. As linhas de cotações podem já ter sido escritas. Ao repetir na V28.3.1, os IDs determinísticos fazem atualização da mesma linha, sem duplicar a cotação. O histórico de análises só é salvo depois de a conferência das cotações ser aprovada.

## Compatibilidade

Nenhuma coluna foi removida, renomeada ou deslocada. A estrutura das abas permanece idêntica à V28.3.0.
