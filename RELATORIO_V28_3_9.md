# Relatório técnico — Tex Statistics V28.3.9

## Falha reproduzida

A pré-visualização da importação reconhecia clubes da 2. Bundesliga 2026/27 por meio do catálogo sazonal. Na confirmação, `app.py` executava uma segunda validação com `resolve_team_in_league(...)` sem a data da partida. Essa chamada consultava somente o catálogo histórico mais recente e bloqueava os clubes ausentes desse recorte.

## Correção

- `resolve_team_in_league` passou a aceitar `match_date`;
- o overlay sazonal é incorporado automaticamente quando a data é informada;
- a confirmação final converte data e hora antes de validar as equipes;
- a mesma data é enviada ao reconhecedor de mandante e visitante;
- `IMPORTER_API_VERSION` e a interface foram atualizados para `28.3.9`.

## Regressão testada

Foram testados na liga `D2`, com data de agosto de 2026:

- Heidenheim;
- Wolfsburg;
- Cottbus;
- St Pauli.

Todos foram resolvidos com escore igual ou superior a 0,98. Também foi verificado que o overlay de 2026/27 não é aplicado a uma partida de agosto de 2025.

## Escopo preservado

Não houve mudança em filtros, modelos, odds, planilhas, persistência, múltiplas ou apostas individuais.
