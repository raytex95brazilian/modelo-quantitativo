# Relatório técnico — Tex Statistics V28.3.4

## Objetivo

Restaurar na interface principal os indicadores de gols esperados que já eram calculados pelo motor e persistidos na planilha.

## Implementação

Foi criado o componente `render_expected_goals`, chamado dentro do cartão de cada partida aprovada, imediatamente antes da recomendação estatística e financeira.

O componente lê diretamente:

- `LambdaHome`: gols esperados do mandante;
- `LambdaAway`: gols esperados do visitante;
- soma de ambos: gols esperados totais.

A tela identifica os times nos títulos dos cartões e inclui uma nota esclarecendo que os valores são médias probabilísticas do Poisson, não um placar previsto. Caso os valores estejam ausentes, a interface informa a indisponibilidade sem interromper a análise.

## Compatibilidade

Não houve alteração em:

- filtro obrigatório de 2018;
- motor preditivo;
- probabilidades e regras financeiras;
- importação inteligente 1X2;
- colunas e ordem das planilhas;
- salvamento em lote;
- banca e unidade.

A versão da interface passa a ser `V28.3.4`. A API do filtro permanece `28.3.3`.

## Validações

- compilação de todos os módulos Python;
- inicialização do aplicativo sem interface gráfica;
- teste do filtro de 2018;
- teste do importador 1X2;
- teste da conferência numérica do Google Sheets;
- teste específico do componente de gols esperados;
- teste de integridade e manifesto SHA-256 do pacote final.
