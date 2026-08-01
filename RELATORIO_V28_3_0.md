# Relatório técnico — Tex Statistics V28.3.0

## Escopo implementado

A V28.3.0 acrescenta ao aplicativo um fluxo de importação assistida por texto, sem realizar raspagem automática de sites externos.

O usuário copia a listagem visível da casa de apostas e cola no aplicativo. O novo módulo `tex_importador_programacao.py` executa:

1. limpeza de linhas vazias e marcadores `Icon:`;
2. identificação de datas nos formatos `DD/MM`, `DD/MM/AA` e `DD/MM/AAAA`;
3. identificação de horários `HH:MM`;
4. segmentação do texto em partidas;
5. leitura do primeiro mercado Resultado Final 1X2;
6. normalização dos nomes das equipes;
7. inferência da liga entre as 24 competições;
8. geração de pré-visualização editável;
9. validação das cotações e do horário pré-jogo;
10. persistência em lote.

## Inferência de liga e equipe

A resolução utiliza:

- equivalências explícitas para nomes frequentes;
- remoção de acentos e pontuação;
- comparação de versões simplificadas dos nomes;
- similaridade textual;
- validação simultânea do mandante e do visitante na mesma liga;
- margem mínima sobre a segunda melhor liga candidata.

Uma equipe isolada não força uma classificação ambígua. A decisão é feita pelo par do confronto.

## Persistência em lote

Foi criada a função `registrar_eventos_lote` em `tex_v25_storage.py`.

Para múltiplas partidas, ela:

- cria um evento `UPSERT` por partida;
- envia todas as linhas em um único `append_rows`;
- identifica o intervalo devolvido pela API;
- lê todas as linhas com um único `batch_get`;
- compara textos e cotações campo a campo;
- só confirma sucesso após a releitura.

A função `upsert_games_batch` do aplicativo grava em seguida todas as cotações no `catalogo_odds` utilizando o mecanismo de upsert em lote já existente.

## Proteção de dados existentes

Quando uma partida já existe e uma nova importação contém somente 1X2, as cotações complementares previamente digitadas são preservadas. A importação atualiza os campos recebidos e não apaga Mais/Menos de 2,5 ou Ambas Marcam existentes.

## Interface

Foram adicionados:

- abas modernas para cadastro manual e importação;
- caixa ampla para colagem;
- seletor do ano;
- casa de apostas;
- botão de interpretação automática;
- métricas de partidas reconhecidas e pendentes;
- tabela editável de conferência;
- seleção individual das partidas que serão importadas;
- formulário móvel para complementação dos demais mercados;
- confirmação do intervalo exato gravado na planilha.

## Testes executados

- compilação de todos os módulos Python;
- importação do aplicativo sem interface gráfica;
- leitura do modelo de texto fornecido pelo usuário;
- reconhecimento de dez confrontos do Brasileirão no mesmo bloco;
- reconhecimento de `NY City` como `New York City` e da liga `EUA - MLS`;
- reconhecimento de `Manchester City` como `Man City` e da Premier League;
- garantia de que o segundo bloco 1X2 não substitui o Resultado Final;
- gravação de 20 eventos com uma única chamada de escrita e uma única leitura em lote;
- testes anteriores de filtro de 2018, autosave, armazenamento, finanças e controle de quota;
- comparação das listas de colunas da V28.2.1 com a V28.3.0.

## Resultado da compatibilidade

As quatro estruturas comparadas são idênticas à V28.2.1:

- `COLUNAS_COTACOES`: 53/53, ordem idêntica;
- `COLUNAS_ANALISES`: 80/80, ordem idêntica;
- `COLUNAS_EVENTOS_LOTE`: 21/21, ordem idêntica;
- `COLUNAS_LOTE_PENDENTE`: 6/6, ordem idêntica.
