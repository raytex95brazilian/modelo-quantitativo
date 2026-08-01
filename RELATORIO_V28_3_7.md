# Relatório técnico — Tex Statistics V28.3.7

## Problema corrigido

O painel superior informava a quantidade de partidas aprovadas no filtro de 2018, mas não apresentava uma lista imediata desses confrontos. Para descobrir quais jogos haviam passado, era necessário percorrer individualmente todos os cartões da seção detalhada.

## Implementação

Foi criada a função `approved_games_summary_table`, que cruza:

- o lote ativo;
- o resultado individual do filtro de 2018;
- a leitura estatística e financeira escolhida para cada partida.

O novo quadro **Resumo dos jogos aprovados** é renderizado imediatamente abaixo dos cinco indicadores gerais. Ele preserva a ordem original do lote e apresenta:

- número do cartão detalhado;
- partida;
- liga;
- data e hora;
- resultado da análise;
- melhor mercado/seleção;
- probabilidade final;
- cotação atual;
- cotação justa;
- valor esperado.

Jogos aprovados sem cotação favorável permanecem na lista com o estado `SEM VALOR AO PREÇO ATUAL`. Portanto, o resumo não se limita às apostas simples.

## Compatibilidade

A alteração é exclusivamente de interface e consolidação visual. Permanecem inalterados:

- filtro obrigatório de 2018;
- motor preditivo;
- Poisson e gols esperados;
- critérios financeiros;
- múltipla e apostas simples;
- importador 1X2;
- separação de lotes;
- armazenamento e colunas das planilhas.

## Testes executados

- compilação de `app.py`;
- importação do aplicativo com Streamlit simulado;
- resumo com aprovados intercalados entre reprovados;
- preservação do número original do cartão;
- inclusão de aprovado com `OPERAR`;
- inclusão de aprovado com `SEM VALOR AO PREÇO ATUAL`;
- cálculo da cotação justa no resumo;
- filtro de 2018;
- importação inteligente 1X2;
- conferência numérica do Google Sheets;
- gols esperados;
- recuperação idempotente após erro 503;
- substituição de lote.
