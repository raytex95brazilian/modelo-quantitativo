# Relatório técnico — Tex Statistics V28.3.6

## Problema corrigido

A função de importação da V28.3.5 começava com o conteúdo integral de `games()` e executava *upsert* das novas partidas sobre essa lista. Consequentemente, uma importação da Liga MX feita após uma importação do Brasileirão preservava os jogos brasileiros no lote ativo e acrescentava os mexicanos. O comportamento era tecnicamente consistente com o código, mas incorreto para o fluxo esperado pelo usuário.

## Solução implementada

Foi criado um modo explícito de destino da importação:

1. **Criar novo lote — substituir apenas o lote exibido** — padrão.
2. **Adicionar ao lote atual** — opção deliberada para lotes combinados.

No modo de substituição:

- a sessão ativa é reconstruída apenas com as partidas importadas;
- a análise anterior é invalidada;
- o snapshot `lote_pendente` passa a conter somente o novo lote;
- o log `entrada_jogos` recebe um evento `CLEAR` seguido dos novos `UPSERTs`;
- `CLEAR` e `UPSERTs` são enviados e conferidos em uma única operação em lote;
- o catálogo de cotações e o histórico de análises não são apagados.

No modo de acréscimo, o comportamento anterior é mantido de forma explícita.

## Preservação de dados

A correção altera somente a composição do **lote ativo**. Nenhuma coluna foi removida, renomeada ou deslocada. As partidas brasileiras já gravadas continuam disponíveis nas planilhas históricas mesmo depois de um novo lote mexicano substituir a lista exibida.

## Testes executados

- substituição de um lote brasileiro por um lote mexicano;
- confirmação de que o lote ativo contém apenas a Liga MX;
- modo alternativo de acréscimo contendo Brasil e México;
- gravação de `CLEAR` + `UPSERT` em uma única chamada;
- reconstrução append-only do lote;
- importação sem interface gráfica;
- persistência de cotações complementares em reimportações do mesmo jogo;
- testes anteriores de erro 503, conferência numérica, filtro de 2018, gols esperados e integridade do pacote.
