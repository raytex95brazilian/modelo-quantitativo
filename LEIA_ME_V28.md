# Tex Statistics V28.1.5

Aplicativo Streamlit para análise pré-jogo de futebol em 24 ligas, com retirada da margem do mercado, modelo dinâmico de gols, árvores regularizadas, probabilidade conservadora, carteira limitada, auditoria e liquidação financeira.

## Fluxo de uso

1. Informe banca, unidade fixa e máximo de entradas por semana.
2. Escolha uma partida futura, liga, equipes e casa de apostas.
3. Informe as cotações completas dos mercados desejados.
4. Adicione todas as partidas do lote.
5. Clique em **ANALISAR TODO O LOTE**.
6. Consulte a leitura principal, os mercados avaliados e a carteira validada.
7. Clique em **SALVAR COTAÇÕES E PROBABILIDADES** para registrar a avaliação.
8. Clique em **REGISTRAR ENTRADAS DA CARTEIRA** somente quando a aposta tiver sido efetivamente realizada.
9. Após o jogo, informe o placar no controle financeiro.

## Mercados

- **Resultado final 1X2:** validado para carteira.
- **Mais/Menos 2,5 gols:** validado para carteira.
- **Ambas Marcam — Sim/Não:** análise complementar; não entra automaticamente na carteira por falta de histórico completo de cotações equivalente.

## Filtro conservador

Uma entrada só é autorizada quando:

- o mercado é financeiramente validado;
- a cotação após desconto de 2% está na faixa testada;
- existem ao menos 100 casos semelhantes;
- a confiança é moderada ou forte;
- o valor esperado conservador não é negativo;
- a partida ainda não possui aposta registrada;
- existe espaço no máximo semanal de cinco entradas.

A probabilidade conservadora é o menor valor entre a probabilidade do modelo e o limite inferior estatístico da taxa de acerto dos casos semelhantes.

## Controle de versão

- Interface: V28.1.5.
- API do núcleo isolado: 28.1.2.
- Modelo treinado: V28.0.

Leia `LEIA_PRIMEIRO_V28_1_5.md` antes do deploy e `RELATORIO_AUDITORIA_V28_1_5.md` para o resultado da revisão.
