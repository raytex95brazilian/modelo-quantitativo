# Relatório de correção — V28.1.5.12

## Defeito confirmado

A V28.1.5.11 gravava imediatamente o jogo bruto em `entrada_jogos`, mas as linhas da aba `catalogo_odds` só eram criadas depois do clique em **ANALISAR TODO O LOTE**. Isso não atendia ao requisito de que todas as cotações digitadas fossem persistidas imediatamente.

## Correção

- criação imediata de uma linha em `catalogo_odds` para cada seleção digitada;
- cálculo pré-análise da probabilidade implícita, margem total do mercado e probabilidade sem margem;
- IDs pré-análise idênticos aos IDs produzidos pelo motor V28.1.2;
- atualização por `ID Coleta` depois da análise, sem duplicar linhas;
- gravação e releitura obrigatórias antes da limpeza do formulário;
- ID de partida determinístico para tornar tentativas repetidas idempotentes;
- migração automática dos lotes já existentes em `entrada_jogos` para `catalogo_odds`;
- manutenção da restauração do lote pelo log append-only;
- casa de apostas padrão `PIXBET`, editável.

## Sequência transacional

1. grava e relê `entrada_jogos`;
2. grava/atualiza e relê todas as cotações em `catalogo_odds`;
3. altera o lote da sessão;
4. atualiza o snapshot redundante;
5. limpa o formulário e executa o rerun.

Se a segunda etapa falhar, o jogo já permanece preservado em `entrada_jogos`, o formulário não é limpo e o usuário recebe o erro para repetir a sincronização.

## Validação automatizada

Foi acrescentado `teste_autosave_cotacoes_antes_analise.py`, que comprova:

- cinco cotações salvas antes da análise para um jogo com 1X2 e Mais/Menos 2,5;
- identidade entre os IDs pré-análise e os IDs do motor;
- enriquecimento posterior das mesmas linhas;
- ausência de duplicação.

O núcleo preditivo V28.1.2 e os artefatos do modelo não foram alterados.
