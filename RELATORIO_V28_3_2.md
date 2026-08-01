# Relatório técnico — Tex Statistics V28.3.2

## Problema corrigido

A tabela de apostas individuais exibia mercado, seleção, cotação e probabilidades, mas não mostrava o confronto correspondente. Em lotes com várias partidas, uma oportunidade como “Ambas marcam — Sim” ficava sem identificação imediata.

## Implementação

A função de apresentação das avaliações passou a derivar e incluir os campos:

- `Partida`: concatenação segura de `Home` e `Away`;
- `Liga`: origem em `League`;
- `Data`: formatação de `DateParsed` em `dd/mm/aaaa`;
- `Hora`: origem em `Time`, no formato `HH:MM`.

Essas colunas aparecem imediatamente depois de `Situação`, tanto na visualização resumida quanto no detalhamento técnico.

## Compatibilidade

- nenhuma coluna das planilhas foi criada, removida, renomeada ou deslocada;
- nenhuma regra estatística ou financeira foi modificada;
- o filtro de 2018 permanece como único portão operacional;
- o armazenamento continua na API 28.3.1;
- a importação continua na API 28.3.0.

## Testes adicionados

Foi incluída verificação automatizada para confirmar que a tabela retorna, nas primeiras colunas, `Situação`, `Partida`, `Liga`, `Data` e `Hora`, e que o confronto de teste é exibido como `Grêmio x São Paulo`.
