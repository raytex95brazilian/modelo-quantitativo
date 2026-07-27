# Relatório de correção — Tex Statistics V28.1.5.11

## Falha observada

Após a análise, o Google Sheets confirmou o append em `catalogo_odds`, mas a leitura de conferência devolveu valores como `02.01` e `31.12` na coluna **Cotação**, embora as odds enviadas fossem `3.44` e `1.80`.

## Causa

A coluna **Cotação** da planilha herdou formatação de data de uma estrutura anterior. O Google armazenou os números corretamente, porém a API de leitura retornava o valor visual formatado como data. Assim, `3.44` aparecia como `02.01` e `1.80` como `31.12`, fazendo a conferência acusar uma divergência falsa.

## Correções

- A leitura pós-gravação agora usa `UNFORMATTED_VALUE`, comparando o valor bruto armazenado.
- Colunas de odds, probabilidades e valores financeiros são reformatadas como número (`0.00`) quando a aba é aberta.
- A leitura de linhas de confirmação, histórico e restauração ignora máscaras visuais de data.
- Os dados já gravados como números seriais não são apagados; ao aplicar o formato numérico, voltam a aparecer como odds.
- Foi acrescentado teste que simula uma planilha exibindo `3.44` como `02.01` e confirma que o app lê `3.44`.
- O reenvio consulta somente a coluna de IDs e ignora registros já existentes, evitando duplicar linhas anexadas antes de uma falsa falha de conferência.

## Versões

- Interface: V28.1.5.11
- Armazenamento: 28.1.5.11
- Motor preditivo: V28.1.2 — Estado Isolado

O motor preditivo e o backtest não foram alterados.
