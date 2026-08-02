# Tex Statistics V28.3.15 — Elencos sazonais e equipes promovidas

## Falha confirmada

A V28.3.14 foi apresentada incorretamente como se reconhecesse todos os clubes atuais das 24 ligas. Na realidade, o catálogo universal era formado principalmente pelos clubes existentes na base histórica desde 2012, acrescido apenas do overlay sazonal da 2. Bundesliga 2026/27.

O `Académico Viseu`, promovido à Primeira Liga 2026/27 após longo período fora da elite, não existia no catálogo histórico `P1` e também não estava em um overlay sazonal. Por isso a confirmação final bloqueava `Academico Viseu`.

## Correção

- importador atualizado para API `28.3.15`;
- incluído o elenco completo da Primeira Liga 2026/27 como overlay sazonal `P1, 2026`;
- incluído o nome canônico `Academico Viseu`;
- incluídas as variantes `Académico de Viseu`, `Académico Viseu FC` e `AC Viseu`;
- incluídas variantes usuais de `Marítimo`;
- pré-visualização e validação final continuam usando a mesma data e o mesmo elenco sazonal;
- clubes sem histórico suficiente podem ser importados, mas permanecem sujeitos ao bloqueio esportivo por dados insuficientes durante a análise.

## Limite declarado

O catálogo histórico não equivale automaticamente ao elenco futuro de todas as ligas. Novos promovidos que nunca apareçam no recorte local precisam constar do overlay da temporada correspondente. Esta versão corrige integralmente a Primeira Liga 2026/27 e deixa essa limitação explicitada, sem repetir a alegação absoluta da V28.3.14.
