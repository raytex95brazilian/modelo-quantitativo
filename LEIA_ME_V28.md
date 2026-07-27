# Tex Statistics V28.1.5.11

Interface operacional sobre o motor V28.1.2 — Estado Isolado.

## Persistência

Cada partida é gravada na aba `entrada_jogos` antes de entrar no lote da tela. O app relê a linha e confere todas as cotações. Sem confirmação, o formulário não é apagado.

Depois de **Analisar todo o lote**, as linhas de `catalogo_odds` e `historico_analises` também são gravadas com leitura de conferência.

A planilha de destino deve ser declarada explicitamente nos Secrets; não existe fallback silencioso.

## Interface

- formulário em uma etapa;
- seletores corretos por liga;
- campos de cotação vazios;
- casa padrão PIXBET;
- Análise para IA visível na tela;
- decisão fechada com as cotações informadas.
