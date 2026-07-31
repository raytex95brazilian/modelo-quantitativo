# Relatório técnico — Tex Statistics V28.2.0

## Objetivo

Integrar o método objetivo utilizado em 2018 ao aplicativo atual sem perder a base histórica, a persistência pré-análise, o controle de banca ou o motor estatístico existente.

## Decisão de arquitetura

O filtro de 2018 é o único portão de elegibilidade esportiva. O motor estatístico continua calculando todos os jogos para que jogos ruins e reprovados também alimentem a base. O resultado do filtro controla somente o uso operacional.

## Estados possíveis

### Reprovado no filtro de 2018

- cálculos e cotações salvos;
- motivo de cada regra registrado;
- proibido em aposta simples;
- proibido na sugestão de múltipla.

### Aprovado no filtro de 2018

- evento apto;
- segue obrigatoriamente para probabilidades e análise das cotações;
- pode gerar uma aposta simples quando houver preço favorável;
- pode fornecer um componente para a múltipla.

## Apostas simples

Não há meta mínima semanal. Para cada partida aprovada, o aplicativo escolhe como simples o mercado de maior valor esperado conservador entre as cotações favoráveis. Não há complemento com valor esperado negativo.

## Sugestão de múltipla

Para cada partida aprovada, o aplicativo considera apenas mercados cujo preço seja favorável no cenário conservador. Entre eles, escolhe o de maior probabilidade conservadora. Cada partida contribui com no máximo um mercado.

A tela mostra:

- confrontos e mercados;
- probabilidades individuais;
- cotações individuais;
- produto das cotações;
- probabilidade conjunta aproximada;
- valor esperado conjunto;
- retorno potencial para uma unidade da banca.

## Persistência

As colunas antigas não foram movidas, renomeadas ou removidas. Novas colunas foram anexadas ao final de `COLUNAS_COTACOES` e `COLUNAS_ANALISES`.

Dados acrescentados incluem:

- status final do filtro;
- resultado e detalhe de cada regra;
- contagem de gols nas últimas cinco partidas;
- último confronto direto considerado;
- elegibilidade operacional;
- decisão estatística e financeira;
- mercado escolhido para simples;
- inclusão na múltipla;
- fator e probabilidade conjunta da múltipla.

## Interface

A interface recebeu:

- cabeçalho moderno;
- botões maiores e responsivos;
- cartões visuais de aprovação e reprovação;
- tabela de lista de verificação;
- cartão próprio da sugestão de múltipla;
- ajustes para telas menores que 768 pixels;
- barra lateral automática no celular.

## Módulos novos

- `tex_filtro_2018.py`: aplicação auditável das regras.
- `tex_operacao_filtrada.py`: portão operacional, apostas simples e múltipla.

## Testes executados

- compilação de todos os arquivos Python;
- teste do filtro com partida real aprovada;
- teste da exceção da Regra 2 com confronto de copa seguido por confronto de liga;
- teste de bloqueio absoluto de jogos reprovados;
- teste de escolha distinta para simples e múltipla;
- teste de preservação das colunas antigas como prefixo;
- teste do aplicativo sem interface gráfica;
- testes antigos de armazenamento, autosave, restauração, liquidação e confirmação da planilha.
