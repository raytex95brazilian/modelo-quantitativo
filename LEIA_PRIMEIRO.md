# Tex Statistics V28.3.3 — Classificação e forma recente

Esta versão foi construída diretamente sobre a V28.3.2 e preserva o motor, o filtro obrigatório de 2018, a interface principal, a banca, a unidade e a estrutura das planilhas existentes.

## Novo modo de cadastro

Na seção **1. Adicionar partidas**, existem duas abas:

1. **Cadastro manual** — mantém o formulário anterior.
2. **Colar jogos e cotações 1X2** — recebe o texto copiado da listagem principal da casa de apostas.

O importador reconhece automaticamente:

- data;
- horário;
- mandante;
- visitante;
- cotação da vitória do mandante;
- cotação do empate;
- cotação da vitória do visitante;
- liga e nomes internos das equipes.

O ano é informado uma única vez no topo da importação quando a listagem contém apenas dia e mês.

## Detecção automática da liga

A liga é determinada pelas duas equipes em conjunto e comparada com o catálogo das 24 competições do aplicativo.

Exemplos:

- `Flamengo` + `São Paulo SP` → `Brasileirão Série A`;
- `NY City` + `Inter Miami` → `EUA - MLS`;
- `Manchester City` + `Arsenal` → `Inglaterra - Premier League`.

O sistema também normaliza nomes como:

- `Clube Do Remo` → `Remo`;
- `Atlético MG` → `Atletico-MG`;
- `Vasco da Gama` → `Vasco`;
- `Athletico Paranaense` → `Athletico-PR`;
- `SC Internacional` → `Internacional`.

Quando a identificação não tiver segurança suficiente, a linha é marcada como **REVISAR** e não é selecionada automaticamente para gravação.

## Segurança da leitura

O importador lê somente o primeiro bloco inequívoco de **Resultado Final 1X2**. Ele ignora deliberadamente:

- o segundo bloco de mandante/empate/visitante;
- mercados de primeiro tempo;
- handicaps;
- números de quantidade de mercados;
- Mais/Menos de gols;
- Ambas Marcam;
- mercados de jogadores.

Isso impede que números copiados sem seus cabeçalhos visuais sejam gravados na coluna errada.

## Complementação manual dos outros mercados

Depois da importação, abra **Completar Mais/Menos de 2,5 e Ambas Marcam em lote**.

Cada partida possui campos para:

- Mais de 2,5;
- Menos de 2,5;
- Ambas Marcam — Sim;
- Ambas Marcam — Não.

O formulário é vertical, adequado ao celular, e salva todas as alterações de uma só vez.

## Gravação e quota do Google Sheets

Uma rodada inteira é gravada usando:

- uma inclusão em lote na aba `entrada_jogos`;
- uma atualização/inclusão agrupada na aba `catalogo_odds`;
- uma conferência em lote das linhas gravadas;
- uma atualização do snapshot do lote.

Não é executada uma solicitação separada por partida ou por cotação.

## Compatibilidade das planilhas

As estruturas da V28.2.1 foram preservadas integralmente:

- `catalogo_odds`: 53 colunas, mesma ordem;
- `historico_analises`: 80 colunas, mesma ordem;
- `entrada_jogos`: 21 colunas, mesma ordem;
- `lote_pendente`: 6 colunas, mesma ordem.

Nenhuma coluna antiga foi removida, renomeada ou deslocada.

## Regra operacional

A importação automática não altera o portão do sistema:

- todos os jogos e cotações são armazenados;
- o filtro de 2018 continua sendo o único portão operacional;
- jogos reprovados permanecem na base, mas não entram em apostas simples nem na múltipla;
- jogos aprovados seguem para análise estatística e financeira.

## Implantação

Substitua todo o conteúdo do projeto pelo conteúdo deste pacote. Não misture `app.py` ou `tex_v25_storage.py` com arquivos de versões anteriores.

Versões esperadas:

- interface: `V28.3.3`;
- armazenamento: `28.3.1`;
- importador: `28.3.0`;
- núcleo preditivo: `28.1.2`;
- filtro de 2018 e contexto esportivo: `28.3.3`.


## Correção V28.3.1 — conferência numérica do Google Sheets

A API do Google Sheets pode devolver um inteiro sem a parte decimal mesmo quando o aplicativo enviou um número de ponto flutuante. Por exemplo, uma posição enviada como `17.0` retorna como `17`. A V28.3.0 interpretava isso incorretamente como divergência e exibia falha, embora a linha já tivesse sido gravada.

A V28.3.1:

- compara numericamente temporada, posições, pontos e amostras;
- aceita `17.0` e `17` como o mesmo valor;
- mantém comparação rígida para nomes, IDs, datas e textos;
- usa formato inteiro nas colunas de posição, pontos e amostras;
- apresenta uma mensagem curta na tela e deixa detalhes técnicos recolhidos.

Ao repetir o salvamento, os IDs determinísticos atualizam as mesmas linhas de cotações, sem criar duplicatas.


## Correção V28.3.2 — identificação da partida nas apostas individuais

A tabela **Apostas individuais** passa a exibir, antes do mercado e das cotações:

- partida (`Mandante x Visitante`);
- liga;
- data;
- horário.

Assim, uma indicação como `Ambas marcam — Sim` não aparece mais isolada. O usuário consegue identificar imediatamente a qual confronto a oportunidade pertence. A mesma identificação também está disponível no quadro técnico detalhado.

Esta correção altera apenas a apresentação e a versão registrada da interface. O motor estatístico, o filtro de 2018, as regras financeiras, a importação 1X2 e as colunas das planilhas permanecem inalterados.


## Upgrade V28.3.3 — classificação e forma recente

Dentro do cartão de cada partida, antes do resultado do filtro, o aplicativo agora apresenta:

- posição e pontos dos dois times na data do evento;
- campanha resumida: jogos, vitórias, empates, derrotas e gols;
- últimos cinco jogos do mandante, independentemente do mando;
- últimos cinco jogos do mandante em casa;
- últimos cinco jogos do visitante, independentemente do mando;
- últimos cinco jogos do visitante fora.

A forma é resumida por marcadores `V`, `E` e `D`. O botão **Ver os placares dos jogos recentes** abre as quatro listas completas com data, local, adversário e placar.

Somente partidas anteriores ao confronto analisado são usadas. Os dados vêm da base histórica carregada pelo aplicativo, que atualmente é predominantemente formada por jogos de liga.

A alteração é apenas de contexto e interface. As colunas existentes das planilhas e as regras estatísticas, financeiras e operacionais não foram modificadas.
