# Tex Statistics V28.2.1 — Interface limpa, cotação justa e gravação em lote

Esta versão corrige três pontos da V28.2.0 sem alterar a estrutura histórica da Planilha Google.

## Alterações visíveis

- Removido o botão **APLICAR CONFIGURAÇÃO**.
- Banca e unidade são aplicadas automaticamente quando o valor é alterado.
- A **Cotação justa** voltou ao painel principal e às tabelas resumidas.
- A tabela principal agora mostra apenas os dados decisórios:
  - situação;
  - mercado e seleção;
  - cotação atual;
  - cotação justa;
  - cotação mínima para operar;
  - probabilidade final;
  - valor esperado final;
  - decisão financeira e motivo.
- Probabilidades auxiliares, calibração, amostras e divergências continuam disponíveis em **Cálculos técnicos**, recolhidos por padrão.

## Correção do erro 429 do Google Sheets

O salvamento das cotações foi alterado para gravação em lote:

- linhas existentes são atualizadas em uma única chamada `batch_update`;
- linhas novas são adicionadas em uma única chamada `append_rows`;
- a conferência é feita em lote;
- erros temporários de quota recebem novas tentativas com espera progressiva.

Isso elimina o comportamento anterior que podia executar uma solicitação de escrita para cada mercado e ultrapassar o limite de gravações por minuto.

## Compatibilidade da planilha

As listas de colunas de `catalogo_odds`, `historico_analises` e `lote_pendente` são exatamente as mesmas da V28.2.0. Nenhuma coluna antiga foi removida, renomeada ou reposicionada.

## Regra operacional preservada

O filtro de 2018 continua sendo o único portão operacional. Jogos reprovados continuam calculados e salvos para formar a base histórica, mas não aparecem em apostas simples nem na sugestão de múltipla.
