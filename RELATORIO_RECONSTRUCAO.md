# Relatório da reconstrução operacional

## Problema corrigido

A V25 usava zonas históricas como portão binário. Na operação real isso produziu dois problemas simultâneos: quase todas as análises foram bloqueadas e a única seleção liberada não demonstrou qualidade operacional. As versões seguintes mantiveram a mesma autoridade decisória e ainda regrediram o fluxo para tabelas, APIs externas ou mercados removidos.

## Arquitetura nova

A reconstrução mantém apenas componentes úteis da base anterior:

- histórico das 24 ligas;
- cálculo pré-jogo sem vazamento temporal;
- estimativas Poisson/Dixon-Coles;
- armazenamento Google já configurado.

A decisão ao vivo não chama `approved_zones_for_season` nem `evaluate_live_market` da V25.

O processo agora é:

1. normalizar as odds do mercado sem margem;
2. consultar calibração empírica treinada em 2018–2023;
3. usar o modelo esportivo como ajuste limitado, nunca como criador isolado de valor;
4. calcular probabilidade operacional, preço mínimo e margem;
5. classificar cada seleção como `OPERAR`, `OBSERVAR` ou `DESCARTAR`;
6. mostrar sempre uma leitura principal por partida;
7. permitir no máximo uma entrada por partida e aplicar unidade fixa.

## Calibração

Foram criados perfis globais e por liga para:

- 1X2: mandante, empate e visitante;
- mais/menos de 2,5 gols;
- ambas marcam — Sim/Não.

Os perfis esportivos foram ajustados com partidas de 2018–2023 e auditados em 2024–2025. O Brier calibrado foi menor que o Brier bruto em todas as sete seleções avaliadas. Isso melhora a interpretação probabilística, mas não constitui promessa de lucro.

Mercados 1X2 e gols também possuem calibração histórica das probabilidades sem margem. Para ambas marcam, a base de 24 ligas não contém odds históricas completas; por isso a odd atual permanece como âncora e a probabilidade esportiva recebe peso limitado.

## Regras operacionais fixas

- odd máxima: 3,00;
- unidade fixa padrão: 1% da banca;
- máximo padrão: quatro entradas no lote;
- uma seleção por partida;
- 1X2: probabilidade mínima 50% e margem estimada mínima 2%;
- gols: probabilidade mínima 55% e margem mínima 4%;
- ambas marcam: probabilidade mínima 52% e margem mínima 4%;
- exigência de amostra e estabilidade;
- contradição extrema entre modelo e mercado impede entrada.

As regras de gols são mais severas porque o histórico operacional real fornecido mostrou concentração de prejuízo nesse mercado. Os 53 resultados foram usados como diagnóstico de risco, não como conjunto de treinamento.

## Testes executados

- compilação de todos os módulos Python;
- 24 ligas carregadas;
- times separados por liga e temporada mais recente;
- Brasileirão 2026 com 20 clubes no seletor;
- resultado final, gols e ambas marcam presentes;
- três jogos reais processados, totalizando 21 seleções;
- uma leitura principal por jogo mesmo sem preço operacional;
- seleção Bragantino x Coritiba — Mais de 2,5, liberada pela V25, bloqueada nesta reconstrução;
- nenhuma odd acima de 3,00 classificada como `OPERAR`;
- unidade fixa confirmada;
- teste de preço favorável confirmou que o motor consegue gerar `OPERAR` sem o portão da V25.

## Limite honesto

O histórico disponível não sustenta a afirmação de que qualquer versão produzirá renda regular. O aplicativo é uma ferramenta operacional de seleção, comparação de preço, registro e auditoria. Ele não força entradas quando a cotação não cobre o risco e não esconde a melhor leitura quando nenhuma entrada é autorizada.
