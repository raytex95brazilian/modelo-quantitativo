# Relatório técnico — Tex Statistics V28.3.8

## Problema reproduzido

A pré-visualização da importação marcava vários jogos da 2. Bundesliga como `REVISAR`, mesmo quando o par de equipes pertencia claramente à competição. O diagnóstico foi reproduzido sobre a V28.3.7.

## Causa real

O importador comparava os nomes recebidos com `latest_team_catalog`, catálogo formado pela temporada mais recente disponível na base local. Para a temporada 2026/27, esse catálogo ainda refletia a composição anterior da liga.

Havia duas classes de falha:

1. **Mudança de divisão:** Wolfsburg, Heidenheim e St Pauli estavam no catálogo recente da Bundesliga; Osnabruck, Dresden e Cottbus não apareciam no elenco mais recente da D2.
2. **Variação de nome:** `Hertha Berlin`, `Eintracht Braunschweig`, `Dynamo Dresden`, `Energie Cottbus` e `Greuther Fürth` não coincidiam integralmente com os nomes canônicos da base.

O limiar de segurança exigia escore mínimo de 0,72 para ambos os clubes. Exemplos reproduzidos antes da correção:

- Hertha Berlin → Hertha: 0,63;
- Eintracht Braunschweig → Braunschweig: 0,71;
- Dynamo Dresden → Dresden: 0,67;
- Wolfsburg na D2: 0,53;
- St Pauli na D2: 0,38.

## Implementação

- `IMPORTER_API_VERSION` atualizado para `28.3.8`;
- adicionado overlay sazonal `(D2, 2026)` com os 18 clubes da 2. Bundesliga 2026/27;
- o overlay é selecionado pela data da partida;
- partidas de temporadas anteriores continuam usando o catálogo histórico normal;
- adicionadas equivalências explícitas para nomes oficiais e nomes usados por casas de apostas;
- `resolve_team_in_league` passou a aceitar candidatos sazonais adicionais sem alterar o catálogo dos seletores manuais;
- `resolve_imported_matches` passou a enviar a data da partida ao reconhecedor.

## Testes executados

- compilação de todos os módulos;
- importador 1X2 anterior;
- nove confrontos reais da 2. Bundesliga 2026/27;
- controle temporal: o overlay de 2026 não é aplicado a 2025;
- compatibilidade integral das colunas;
- substituição e persistência de lotes;
- tratamento idempotente do erro 503;
- carregamento do aplicativo sem interface gráfica.

## Compatibilidade

Não houve alteração nas listas de colunas de `catalogo_odds`, `historico_analises`, `entrada_jogos` ou `lote_pendente`. O filtro de 2018, o motor V28.1.2, as probabilidades, a camada financeira, os gols esperados e o Google Sheets permanecem inalterados.
