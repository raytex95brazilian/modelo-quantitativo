# Relatório de auditoria — Tex Statistics V28.1.5

## Escopo

Foram revisados a interface Streamlit, o núcleo esportivo isolado, o núcleo operacional, a integração Google Sheets, a camada financeira, o modelo, os perfis de confiabilidade, a base histórica, os arquivos retrospectivos e os testes automatizados.

## Correções consolidadas

1. importação exclusiva do núcleo `tex_v28_core_2812.py`;
2. exigência rígida de `CORE_API_VERSION = "28.1.2"`;
3. preservação do artefato treinado V28.0;
4. limite semanal padrão corrigido para cinco entradas;
5. limite semanal tratado como máximo, sem preenchimento artificial;
6. fingerprint incluindo lote, cotações, banca, unidade, máximo semanal e histórico registrado;
7. bloqueio de segunda entrada automática na mesma partida;
8. Ambas Marcam mantido na análise complementar;
9. ausência de vencimento artificial de cotações, fechamento de mercado e CLV;
10. separação das amostras de mandante e visitante;
11. distinção entre probabilidade esportiva, probabilidade do modelo e probabilidade conservadora;
12. margem total do mercado corrigida nos registros, em vez de margem parcial por seleção;
13. configuração operacional salva como JSON válido;
14. identificador determinístico comum a cotação, análise e aposta;
15. deduplicação entre sessões por identificadores persistentes;
16. migração não destrutiva dos cabeçalhos da planilha;
17. liquidação com validação de mercado, seleção, placar, cotação e entrada;
18. atualização da liquidação remota em uma única operação de linha, reduzindo consumo da API;
19. preservação local da liquidação quando a planilha está indisponível;
20. cálculo do maior recuo em ordem cronológica;
21. remoção da dupla contagem da banca informada;
22. verificação de integridade da base, modelo, arquivos compactados e ausência de chave privada.

## Testes executados

```text
TESTE DE IMPORTAÇÃO V28.1.2 ISOLADA: OK
TESTE V28 OK
TESTE V28.1.5 — ESTADO, ISOLAMENTO, COTAÇÕES E LIMITE SEMANAL: OK
TESTE FINANCEIRO V28: OK
TESTE DE ARMAZENAMENTO, MIGRAÇÃO E LIQUIDAÇÃO EM LOTE: OK
TESTE DE INTEGRIDADE DO PACOTE V28.1.5: OK
```

A compilação de todos os arquivos Python também foi concluída sem erro.

## Verificação retrospectiva da camada conservadora

Com máximo de cinco entradas semanais, a reaplicação retrospectiva da camada conservadora produziu:

- 1.059 entradas;
- 221 semanas;
- média de 4,79 entradas por semana;
- 588 vitórias;
- 55,52% de acerto;
- +134,5910 unidades;
- retorno sobre entradas de +12,71%;
- maior recuo de 24,4098 unidades.

Esse cálculo reaproveita previsões fora da amostra e perfis agregados do mesmo período. Portanto, é uma verificação operacional retrospectiva, não um novo teste final independente.

## Limitação do ambiente de auditoria

Os módulos puros, arquivos, modelo, base, armazenamento simulado e testes foram executados. A inicialização real do servidor Streamlit não pôde ser executada neste ambiente porque o pacote `streamlit` não estava disponível no repositório de instalação da sessão. O `app.py` foi validado por compilação e análise sintática, mas o teste visual final deve ser feito após o deploy.

## Riscos residuais

- indisponibilidade ou alteração das fontes externas;
- erro de digitação de cotações ou placares;
- mudança estrutural do mercado após o período histórico;
- diferença entre preço histórico e preço realmente disponível;
- histórico local incompleto quando a planilha não está sincronizada;
- reinicialização do sistema de arquivos do Streamlit Cloud;
- risco financeiro inerente a apostas esportivas.

## Veredito

O pacote está coerente com o estado funcional alinhado: núcleo isolado V28.1.2, modelo V28.0 preservado, máximo de cinco entradas semanais, uma seleção por partida, mercados validados separados da análise complementar, persistência auditável e liquidação financeira. Nenhuma auditoria séria pode garantir ausência absoluta de falhas ou rentabilidade futura.
