# Relatório técnico — Tex Statistics V28.3.11

## Objetivo

Corrigir a resolução da temporada usada para reconstruir a classificação da Regra 1 do filtro de 2018, após auditoria integral das 24 ligas.

## Alteração de código

Foi adicionada uma resolução baseada nos intervalos reais das temporadas presentes na base. A inferência fixa por calendário permanece somente como contingência para partidas futuras ainda não representadas nos arquivos históricos.

A mudança está concentrada em `tex_operacional_core.py`:

- `resolve_season_for_match`;
- `season_label_for_match`;
- cache dos intervalos por liga e temporada;
- distinção entre formato do arquivo-fonte e calendário esportivo da competição.

## Validação

- 111.937 partidas históricas processadas cronologicamente;
- comparação da lógica otimizada com a função real em amostra distribuída pelas 24 ligas;
- 170 casos de regressão conferidos após a correção;
- testes específicos para Liga MX, Argentina, Brasileirão 2020, China 2021, Premier League 2019/20, Serie A 2019/20, La Liga 2019/20 e 2. Bundesliga 2026/27;
- manutenção do estado `NÃO AVALIÁVEL` para temporada futura sem jogos concluídos.

## Impacto

A correção elimina 4.043 falsos `NÃO AVALIÁVEL`, sem flexibilizar nenhuma das quatro regras do filtro.

Nenhuma estrutura de planilha foi alterada.
