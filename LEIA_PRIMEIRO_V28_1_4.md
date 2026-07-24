# Tex Statistics V28.1.4 — Análise Ampliada

Esta versão parte da V28.1.2 e altera somente a seleção das entradas e a apresentação dos resultados.

Ela **não inclui** validade artificial de cotações, comparação com cotação de fechamento, painel financeiro ou automatização de cotações.

## Objetivo

Aumentar o volume de entradas sem preencher a semana com apostas de valor esperado negativo.

O limite padrão passa a ser de **cinco entradas por semana**, mas continua existindo no máximo uma seleção por partida. Se somente três seleções forem aprovadas, o aplicativo mostrará três.

## O que mudou

### 1. Sete seleções concorrem em cada partida

- vitória do mandante;
- empate;
- vitória do visitante;
- mais de 2,5 gols;
- menos de 2,5 gols;
- ambas marcam — Sim;
- ambas marcam — Não.

O mercado Ambas Marcam deixou de ser apenas informativo. Ele pode ser autorizado quando houver histórico suficiente e a cotação apresentar valor esperado não negativo.

### 2. Correção pelo acerto histórico

A probabilidade original continua sendo produzida pelo motor existente. Depois, ela é corrigida com o resultado observado em previsões históricas semelhantes.

Fórmula usada:

```text
Probabilidade corrigida =
(acertos históricos + 100 × probabilidade original)
÷
(amostra histórica + 100)
```

O número 100 funciona como proteção contra amostras pequenas: o histórico precisa ter volume para alterar de forma relevante a probabilidade original.

A correção só é usada quando existem pelo menos 40 casos históricos semelhantes e a confiança é moderada ou forte.

### 3. Ambas Marcam com reconstrução temporal

Para Ambas Marcam, o aplicativo reconstrói previsões históricas usando somente partidas anteriores à data de cada jogo.

Ele então mede:

- quantidade de casos semelhantes;
- percentual de acerto;
- diferença entre previsão e resultado observado;
- estabilidade histórica.

Na primeira análise de uma liga, essa reconstrução pode demorar mais. O resultado fica guardado em memória durante a execução do aplicativo.

### 4. Nova ordem de seleção

Dentro de cada partida, as seleções são ordenadas por:

1. maior valor esperado corrigido;
2. maior estabilidade histórica;
3. maior quantidade de casos históricos;
4. maior probabilidade corrigida.

Somente a melhor seleção da partida pode entrar na lista semanal.

### 5. Interface em português

A apresentação usa:

- cotação;
- probabilidade original;
- probabilidade corrigida pelo histórico;
- acerto histórico;
- casos históricos semelhantes;
- estabilidade histórica;
- valor esperado;
- autorizada;
- alternativa;
- aguardar cotação;
- descartada.

Os nomes internos antigos permanecem somente nas chaves técnicas necessárias para compatibilidade com os arquivos já existentes do projeto.

## Resultado no lote de dez jogos enviado

Usando os dados visíveis no resumo enviado, a correção histórica recupera três leituras principais:

- Flamengo para vencer;
- Santos para vencer;
- Bragantino para vencer.

O lote anterior tinha apenas Flamengo autorizado.

As seleções de Ambas Marcam são recalculadas dentro do aplicativo usando o histórico completo da liga. Por isso, elas podem acrescentar novas entradas, mas não é possível determinar isso apenas com o resumo em texto.

## Instalação

1. Substitua o `app.py` da raiz pelo arquivo deste pacote.
2. Adicione `tex_v28_core_2814.py` à raiz do repositório.
3. Mantenha os arquivos já existentes:
   - `tex_v25_core.py`;
   - `tex_operacional_core.py`;
   - `tex_v25_storage.py`;
   - pasta `model`;
   - pasta `data`.
4. Apague a pasta `__pycache__`, caso exista.
5. Envie os arquivos no mesmo envio ao repositório.
6. Reinicie o aplicativo.

## Limitação importante

A versão foi validada com testes isolados e com o cenário de dez jogos enviado. O pacote parcial não contém a pasta `model`, a base completa nem todos os módulos do repositório; portanto, não foi possível executar aqui um teste histórico completo de toda a estratégia.

A meta de cinco entradas por semana é uma meta de volume, não uma garantia. O aplicativo não autoriza entradas negativas apenas para atingir essa quantidade.
