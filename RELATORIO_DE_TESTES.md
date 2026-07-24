# Relatório de testes — V28.1.4

## Verificações executadas

### Sintaxe

Passaram pela compilação de sintaxe:

- `app.py`;
- `tex_v28_core_2814.py`;
- `teste_v28_1_4.py`;
- `teste_smoke_app_v28_1_4.py`;
- `teste_cenario_10_jogos.py`.

### Núcleo ampliado

O teste isolado confirmou:

- sete seleções avaliadas por partida;
- correção da probabilidade pelo histórico;
- autorização com valor esperado não negativo;
- no máximo uma seleção por partida;
- Ambas Marcam participando da seleção;
- reconstrução temporal usando apenas partidas anteriores;
- nomes de apresentação em português.

### Cenário dos dez jogos

A fórmula recuperou:

- Santos: probabilidade corrigida de 73,73% e valor esperado de +1,15%;
- Flamengo: probabilidade corrigida de 73,62% e valor esperado de +6,06%;
- Bragantino: probabilidade corrigida de 65,84% e valor esperado de +3,23%.

As demais leituras principais continuaram negativas.

### Inicialização da interface

A interface percorreu o fluxo inicial com dependências simuladas sem erro de nome ou atributo.

## O que não foi possível certificar neste ambiente

O repositório completo e os arquivos do modelo não estão presentes no pacote-base. Por isso, continuam pendentes:

- execução do aplicativo com a base real completa;
- medição do tempo da primeira reconstrução de Ambas Marcam;
- teste histórico completo da nova regra;
- confirmação da média semanal em toda a base;
- confirmação do retorno financeiro da nova regra.
