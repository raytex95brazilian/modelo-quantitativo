# Tex Statistics V28.3.10 — Dados insuficientes no início da temporada

## Diagnóstico confirmado da 2. Bundesliga 2026/27

Os jogos de 8 e 9 de agosto de 2026 pertencem, para o motor, à temporada **2026/27** (`Season = 2026`). A base local distribuída no pacote contém a 2. Bundesliga somente até a temporada **2025/26**, cuja última partida é de **17/05/2026**. Portanto, antes desses eventos existem **zero partidas concluídas da temporada 2026/27** na base e não há classificação atual para aplicar a Regra 1 do filtro de 2018.

A V28.3.9 apresentava esses casos como `REPROVADO`, embora a regra não tivesse sido efetivamente avaliada. A V28.3.10 corrige a classificação sem flexibilizar o portão obrigatório:

- `APROVADO`: todas as regras puderam ser verificadas e foram atendidas;
- `REPROVADO`: havia dados suficientes e alguma regra falhou;
- `NÃO AVALIÁVEL`: faltam dados para aplicar uma ou mais regras com segurança.

Jogos `NÃO AVALIÁVEIS` continuam fora das apostas simples e da múltipla. Eles permanecem calculados e salvos para a base histórica.

## Proteção contra forma antiga apresentada como recente

A revisão encontrou outro problema: clubes que passaram temporadas fora das 24 ligas cobertas podiam receber como “últimos cinco jogos” partidas muito antigas. No caso de `Cottbus`, a versão anterior utilizava partidas de abril e maio de **2014**; para `Osnabruck`, partidas de **2024**.

Agora, as Regras 3 e 4 e o quadro de forma recente aceitam somente jogos da temporada atual ou da imediatamente anterior. Quando não existem cinco partidas recentes na base, o campo aparece como `Sem dados` e o evento fica `NÃO AVALIÁVEL`, em vez de usar resultados antigos como se fossem atuais.

## Interface corrigida

- novo contador **Sem dados para avaliar**;
- cartões amarelos para eventos não avaliáveis;
- Regra 1 mostra a temporada buscada e a última data disponível na base;
- regras de forma mostram `Sem dados` quando faltarem cinco jogos recentes;
- reprovados esportivos permanecem separados dos casos sem dados;
- nenhuma posição ou pontuação da temporada anterior é usada como substituta automática.

A atualização da base após partidas concluídas da nova temporada permitirá reconstruir a classificação. Clubes vindos de divisões não cobertas continuarão exigindo histórico recente suficiente na própria base ou uma futura fonte complementar de partidas oficiais.

---

## Correção V28.3.9 — prévia reconhecia, gravação rejeitava

A V28.3.8 já usava o elenco sazonal de 2026/27 durante a pré-visualização. Porém, ao clicar em **GRAVAR PARTIDAS E COTAÇÕES 1X2**, a validação final chamava novamente o reconhecedor sem informar a data da partida. Com isso, clubes promovidos ou rebaixados eram aceitos na prévia e recusados na confirmação.

A V28.3.9 unifica as duas etapas: tanto a prévia quanto a gravação usam a data do jogo e o mesmo catálogo sazonal. Foram reproduzidos e corrigidos os quatro nomes que apareciam no erro: `Heidenheim`, `Wolfsburg`, `Cottbus` e `St Pauli`.

Nenhuma regra do filtro de 2018, cálculo estatístico, decisão financeira, coluna da planilha ou rotina de lotes foi alterada.

---

## Correção V28.3.8 — clubes promovidos, rebaixados e nomes alternativos

A V28.3.7 montava o catálogo de reconhecimento usando apenas a temporada mais recente já presente na base histórica. Isso falhava quando a programação colada pertencia à temporada seguinte e havia clubes recém-promovidos, rebaixados ou apresentados com nomes diferentes dos usados internamente.

Na programação da 2. Bundesliga 2026/27, por exemplo, `Wolfsburg`, `Heidenheim` e `St Pauli` ainda apareciam no catálogo recente da Bundesliga; `Osnabruck`, `Dresden` e `Cottbus` não estavam no recorte mais recente; e nomes como `Hertha Berlin`, `Eintracht Braunschweig` e `Dynamo Dresden` não coincidiam literalmente com `Hertha`, `Braunschweig` e `Dresden`.

A correção acrescenta um catálogo sazonal datado para a 2. Bundesliga 2026/27 e equivalências explícitas de nomenclatura. O catálogo adicional só é aplicado a partidas da temporada 2026/27, evitando alterar a classificação de jogos de temporadas anteriores.

Foram validados os seguintes confrontos do exemplo real:

- Bochum × Hertha Berlin;
- Magdeburg × Eintracht Braunschweig;
- Heidenheim × Osnabruck;
- Darmstadt × Holstein Kiel;
- Karlsruhe × Bielefeld;
- Wolfsburg × Kaiserslautern;
- Energie Cottbus × Hannover;
- Nurnberg × Dynamo Dresden;
- St Pauli × Greuther Fürth.

Todos passam a ser reconhecidos como **Alemanha - 2. Bundesliga** e recebem os nomes internos esperados pelo motor.

Nenhuma coluna das planilhas, regra do filtro de 2018, cálculo estatístico, cotação ou lógica financeira foi modificada.


## Upgrade V28.3.7 — resumo imediato dos aprovados

Logo abaixo dos cinco indicadores gerais, a tela agora exibe **Resumo dos jogos aprovados**. A tabela reúne todos os confrontos que passaram no filtro obrigatório de 2018, sem exigir que o usuário percorra os cartões de partidas reprovadas.

Para cada aprovado, o resumo mostra:

- número correspondente ao cartão na seção **Análise de cada partida**;
- confronto, liga, data e horário;
- resultado da análise posterior (`OPERAR` ou `SEM VALOR AO PREÇO ATUAL`);
- melhor mercado e seleção;
- probabilidade final;
- cotação atual, cotação justa e valor esperado.

A lista inclui também jogos aprovados que não geraram aposta simples. Assim, o número **Aprovadas no filtro** sempre pode ser conferido diretamente na tabela. Nenhuma regra, cálculo ou coluna de planilha foi alterada.

## Correção V28.3.6 — cada importação pode formar um lote independente

A versão anterior sempre fazia *upsert* sobre o lote ativo. Por isso, ao importar a Liga MX depois do Brasileirão, os jogos mexicanos eram somados aos brasileiros na área **Partidas do lote** e no formulário de complementação manual.

A V28.3.6 acrescenta, antes da colagem, o seletor **Destino desta importação**:

- **Criar novo lote — substituir apenas o lote exibido**: opção padrão e recomendada. A nova importação passa a ser o único lote ativo da tela.
- **Adicionar ao lote atual**: mantém o comportamento cumulativo, mas somente quando escolhido deliberadamente.

Criar um novo lote **não apaga dados históricos**. Permanecem intactos:

- `catalogo_odds`;
- `historico_analises`;
- apostas e liquidações;
- eventos anteriores de `entrada_jogos`;
- cotações complementares já gravadas.

O sistema registra um evento `CLEAR` e os novos `UPSERTs` na mesma escrita em lote. Assim, a restauração após reinício também retorna somente o lote ativo mais recente, sem misturar Brasil e México.


Esta versão foi construída diretamente sobre a V28.3.6 e preserva o motor, o filtro obrigatório de 2018, a interface principal, a banca, a unidade e a estrutura das planilhas existentes.

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

- interface: `V28.3.8`;
- armazenamento: `28.3.6`;
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


## Correção V28.3.4 — gols esperados novamente na tela

O cálculo de gols esperados já permanecia ativo no motor e salvo nas colunas `Gols projetados casa`, `Gols projetados fora` e `Gols projetados total`. Nesta versão, ele volta a aparecer visualmente dentro do cartão de cada partida aprovada.

O quadro **Projeção de gols do modelo** mostra:

- gols esperados do mandante, com o nome do time;
- gols esperados do visitante, com o nome do time;
- soma esperada de gols da partida.

Os valores são apresentados antes da recomendação estatística e financeira. Uma observação na própria tela esclarece que se tratam de médias probabilísticas do modelo de Poisson, e não de previsão de placar exato.

Nenhuma regra do filtro de 2018, probabilidade, cotação, operação, importação ou estrutura de planilha foi modificada.


## Correção V28.3.5 — erro 503 do Google Sheets

A mensagem `APIError: [503]: The service is currently unavailable` significa que o serviço remoto do Google Sheets ficou temporariamente indisponível. Ela não é um erro de cota 429.

A V28.3.4 repetia automaticamente apenas erros 429. Um 503 era encerrado imediatamente, mesmo sendo temporário. A V28.3.5 passa a:

- reconhecer 408, 425, 429, 500, 502, 503 e 504 como falhas temporárias;
- repetir leituras e atualizações idempotentes com espera exponencial curta e jitter;
- tratar `append_rows` de forma idempotente;
- quando um 503 ocorre após o Google possivelmente já ter gravado, procurar os mesmos IDs antes de repetir;
- anexar apenas os registros ainda ausentes, evitando duplicações;
- preservar os campos preenchidos na tela quando a gravação não puder ser confirmada;
- exibir mensagem amigável e deixar o erro técnico em um painel recolhido;
- mostrar o andamento da gravação em lote na interface.

A proteção foi testada com uma simulação específica em que o servidor grava as linhas e, em seguida, devolve 503. O teste confirma que o aplicativo encontra os IDs gravados e não executa um segundo append.

A correção não elimina indisponibilidades reais do Google, mas impede que uma falha temporária isolada seja tratada como definitiva e reduz o risco de linhas duplicadas durante novas tentativas.