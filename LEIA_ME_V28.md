# Tex Statistics V28.1.5.5

Aplicativo Streamlit para análise pré-jogo de futebol em 24 ligas, com mercado sem margem, modelo dinâmico de gols, árvores regularizadas, probabilidade conservadora, carteira limitada, auditoria e liquidação financeira.

## Entrada de partidas

A inclusão funciona em uma única tela:

1. selecione liga, mandante e visitante;
2. informe data, horário e casa de apostas;
3. marque os mercados desejados e digite as cotações;
4. clique em **ADICIONAR OU ATUALIZAR PARTIDA**.

Não existe etapa intermediária de confirmação. Liga e equipes são atualizadas em um fragmento independente; os campos de data, horário, casa e cotações permanecem dentro de um formulário estável.

Todos os campos de entrada manual começam vazios. Após salvar uma partida, a próxima inclusão também abre vazia para impedir reaproveitamento acidental de dados.

## Análise para IA

Depois de analisar o lote, o texto completo aparece diretamente na seção **Análise para IA**. O bloco possui ícone de copiar. O download é opcional.

## Mercados

- **Resultado final 1X2:** validado para carteira.
- **Mais/Menos 2,5 gols:** validado para carteira.
- **Ambas Marcam — Sim/Não:** análise complementar; não entra automaticamente na carteira por falta de histórico completo de cotações equivalente.

## Regra operacional

Uma entrada só é autorizada quando o mercado é validado, a cotação supera o preço mínimo conservador, a amostra é suficiente, a estabilidade é aceitável e existe espaço no máximo semanal de cinco entradas. O máximo não é uma obrigação de preencher apostas.

## Controle de versão

- Interface: **V28.1.5.5**.
- Motor preditivo: **V28.1.2 — Estado Isolado**.
- Modelo treinado: **V28.0**.

Consulte `METODOLOGIA_E_BACKTEST_V28.md` para a metodologia e `RELATORIO_CORRECAO_USABILIDADE_V28_1_5_5.md` para esta revisão.
