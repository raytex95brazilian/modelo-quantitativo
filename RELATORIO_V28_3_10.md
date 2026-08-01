# Relatório técnico — Tex Statistics V28.3.10

## Problema reproduzido

Foram reproduzidos os nove confrontos mostrados pelo usuário para a 2. Bundesliga em 08 e 09/08/2026. Todos retornavam `Filter2018Rule1Basis = DADOS INSUFICIENTES`.

A inspeção da base `data/TEX_V22_DADOS_24_LIGAS.zip` confirmou:

- maior temporada disponível para o código `D2`: `2025` (2025/26);
- última partida disponível: `17/05/2026`;
- temporada calculada para partidas em agosto de 2026: `2026` (2026/27);
- partidas concluídas da temporada 2026/27 antes dos eventos: `0`;
- classificação reconstruída para a temporada 2026/27: tabela vazia.

Logo, a ausência de posição e pontos não era causada pelo reconhecimento dos clubes. O importador já os reconhecia; faltavam resultados da temporada corrente para formar a classificação exigida pela Regra 1.

## Correções

### 1. Estado `NÃO AVALIÁVEL`

O filtro agora distingue falta de dados de reprovação esportiva. `Filter2018Approved` permanece `False`, mantendo o bloqueio absoluto de simples e múltipla, mas `Filter2018Status` passa a ser `NÃO AVALIÁVEL` quando a classificação atual ou a forma recente não puderem ser verificadas.

### 2. Diagnóstico detalhado da classificação

`standings_context` passou a informar:

- temporada e rótulo da temporada;
- quantidade de partidas anteriores da temporada;
- última data disponível da liga;
- código e texto do motivo da indisponibilidade.

Para o lote reproduzido, a Regra 1 informa explicitamente que não há partida concluída de 2026/27 e que a última partida da base é de 17/05/2026.

### 3. Proteção da forma recente

O índice histórico agora guarda a temporada de cada partida. As Regras 3 e 4 usam somente a temporada atual ou a imediatamente anterior. Isso elimina o uso indevido de partidas antigas:

- `Cottbus`: cinco partidas de 2014 eram tratadas como forma recente;
- `Osnabruck`: cinco partidas de 2024 eram tratadas como forma recente.

Na V28.3.10 esses clubes ficam com histórico recente insuficiente até que existam cinco partidas válidas na base.

### 4. Interface e saída operacional

- contador separado para não avaliáveis;
- cartão amarelo e mensagem específica;
- checklist usa `Sem dados`, não `Reprovada`, quando a regra não pôde ser calculada;
- `tex_operacao_filtrada.py` produz `NÃO AVALIÁVEL — DADOS INSUFICIENTES` e mantém o evento fora da carteira;
- nenhuma coluna das planilhas foi criada, removida, renomeada ou deslocada.

## Testes executados

- `teste_dados_insuficientes_inicio_temporada_v28_3_10.py`;
- `teste_v28_2_0_filtro_2018.py`;
- `teste_app_sem_interface.py`;
- testes de reconhecimento e validação sazonal da 2. Bundesliga;
- compilação dos módulos alterados;
- teste de integridade do pacote após regeneração do manifesto.

O teste novo confirma também que um caso histórico com dados completos continua sendo aprovado normalmente e que um evento não avaliável jamais entra em simples ou múltipla.
