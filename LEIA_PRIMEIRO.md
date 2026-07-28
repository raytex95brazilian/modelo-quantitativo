# Tex Statistics V28.1.5.12 — autosave real antes da análise

- **Interface:** Tex Statistics V28.1.5.12
- **Motor preditivo:** V28.1.2 — Estado Isolado
- **Casa padrão:** PIXBET, editável

## Comportamento corrigido

Ao clicar em **ADICIONAR OU ATUALIZAR PARTIDA**, o app agora confirma duas gravações antes de limpar o formulário:

1. uma linha `UPSERT` na aba `entrada_jogos`, contendo o jogo e todas as odds;
2. uma linha por seleção na aba `catalogo_odds`, contendo as cotações digitadas, ainda antes da análise.

Ao clicar posteriormente em **ANALISAR TODO O LOTE**, as linhas já existentes em `catalogo_odds` são atualizadas pelo mesmo `ID Coleta` com probabilidades, margem, classificação e contexto. Não são criadas duplicatas.

Lotes restaurados de versões anteriores são migrados automaticamente: suas odds são inseridas/atualizadas em `catalogo_odds` ao abrir esta versão, sem exigir uma nova análise.

## Secrets

```toml
[google_sheets]
spreadsheet_id = "COLE_AQUI_O_ID_DA_PLANILHA"
worksheet_eventos_lote = "entrada_jogos"
worksheet_lote_pendente = "lote_pendente"
worksheet_catalogo = "catalogo_odds"
worksheet_historico = "historico_analises"
worksheet_auditoria = "auditoria_entradas"
```

Também é aceito `spreadsheet_url` no lugar de `spreadsheet_id`.

## Teste após o deploy

1. Cadastre uma única partida.
2. Antes de clicar em analisar, abra `entrada_jogos` e `catalogo_odds`.
3. Confirme o jogo em `entrada_jogos` e todas as seleções/cotações em `catalogo_odds`.
4. Atualize a página do app e confirme que o lote permanece.
5. Só então cadastre um lote grande.
