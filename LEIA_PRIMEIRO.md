# Tex Statistics V28.3.0 — Importação inteligente de jogos e cotações 1X2

Esta versão foi construída diretamente sobre a V28.2.1 e preserva o motor, o filtro obrigatório de 2018, a interface principal, a banca, a unidade e a estrutura das planilhas existentes.

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

- interface: `V28.3.0`;
- armazenamento: `28.3.0`;
- importador: `28.3.0`;
- núcleo preditivo: `28.1.2`;
- filtro de 2018: `28.2.0`.
