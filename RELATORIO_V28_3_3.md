# Relatório técnico — Tex Statistics V28.3.3

## Objetivo

Acrescentar, dentro do cartão de cada partida analisada, contexto suficiente para o usuário avaliar a situação esportiva das equipes sem precisar consultar outra tela.

## Informações exibidas

Para cada confronto, antes do resultado do filtro de 2018, a interface mostra:

- classificação do mandante e do visitante na data anterior ao evento;
- pontos, jogos, vitórias, empates, derrotas, gols marcados e gols sofridos;
- sequência dos cinco jogos anteriores do mandante, independentemente do mando;
- sequência dos cinco jogos anteriores do mandante atuando em casa;
- sequência dos cinco jogos anteriores do visitante, independentemente do mando;
- sequência dos cinco jogos anteriores do visitante atuando fora.

As sequências usam os marcadores `V`, `E` e `D`. Um quadro recolhível apresenta data, local, adversário, placar do ponto de vista da equipe e resultado de cada partida.

## Proteção contra vazamento temporal

Somente partidas com data estritamente anterior ao confronto analisado são usadas. Resultados do próprio evento ou de datas posteriores não participam da classificação nem da forma recente.

## Fonte e limitação

As informações são calculadas a partir da mesma base histórica carregada pelo aplicativo. No pacote atual, essa base é predominantemente composta por partidas de liga. A interface informa essa limitação e não apresenta os dados como se incluíssem necessariamente copas, amistosos ou todas as competições oficiais.

## Responsividade

Em telas largas, os dois times aparecem lado a lado. Em telas de celular, os cartões são empilhados automaticamente. Os placares detalhados ficam recolhidos por padrão para evitar uma tela excessivamente longa.

## Compatibilidade

- nenhuma coluna das planilhas foi criada, removida, renomeada ou deslocada;
- nenhum cálculo de probabilidade foi alterado;
- nenhum critério financeiro foi alterado;
- o filtro de 2018 permanece como único portão operacional;
- a importação inteligente de jogos e cotações 1X2 permanece intacta;
- armazenamento continua na API `28.3.1`;
- núcleo preditivo continua na API `28.1.2`;
- módulo do filtro/contexto passa para a API `28.3.3`.

## Testes

Foi adicionado o teste `teste_contexto_classificacao_forma_v28_3_3.py`, que verifica:

- disponibilidade das classificações;
- cinco registros em cada uma das quatro sequências;
- exclusão de qualquer partida na data do evento ou posterior;
- mando correto nos cinco jogos em casa e nos cinco jogos fora;
- resultados limitados a vitória, empate ou derrota;
- montagem em lote por identificador da partida.
