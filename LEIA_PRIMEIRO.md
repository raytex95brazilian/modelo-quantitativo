# Tex Statistics V28.1.5.10 — verificação real da planilha

- **Interface:** Tex Statistics V28.1.5.10
- **Motor preditivo:** V28.1.2 — Estado Isolado
- **Casa padrão:** PIXBET, editável

## Antes do deploy

Nos Secrets do Streamlit, informe explicitamente o destino:

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

A V28.1.5.10 não usa mais nenhuma planilha antiga como fallback. Sem destino explícito, o cadastro é bloqueado.

## Teste obrigatório após o deploy

1. Abra o botão **Abrir exatamente a planilha de gravação**.
2. Cadastre somente uma partida de teste.
3. O app deve informar `GRAVADA E RELIDA`, a aba `entrada_jogos`, o número da linha e as cotações conferidas.
4. Abra a linha indicada antes de cadastrar um lote grande.
