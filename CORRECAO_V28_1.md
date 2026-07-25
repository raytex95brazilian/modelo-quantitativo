# Histórico de correções — V28.1.2 a V28.1.5

## Estado isolado

- O aplicativo principal importa exclusivamente `tex_v28_core_2812.py`.
- A execução exige `CORE_API_VERSION = "28.1.2"`.
- `tex_v28_core.py` permanece somente como ponte controlada para scripts antigos.
- O lote é invalidado quando partidas, cotações, banca, unidade, máximo semanal ou histórico registrado mudam.

## Cotações e probabilidades

- Cada partida mantém cotações próprias e o formulário é reiniciado após o salvamento.
- Linhas matematicamente incoerentes são bloqueadas antes da análise.
- A margem salva corresponde à margem total do mercado.
- Probabilidade esportiva, probabilidade do modelo e probabilidade conservadora são distintas.
- Amostras de mandante e visitante são registradas separadamente.
- A configuração operacional é persistida como JSON válido.

## Carteira

- O parâmetro semanal é um máximo de 1 a 5 entradas, com valor padrão de 5.
- Entram apenas mercados validados com amostra suficiente, confiança moderada ou forte e valor esperado conservador não negativo.
- Há no máximo uma seleção por partida.
- Apostas já registradas consomem o limite semanal em lotes e sessões posteriores.
- Partidas já registradas não recebem segunda entrada automática.
- Ambas Marcam permanece complementar e não entra automaticamente.

## Controle financeiro

- Entradas e análises só são gravadas por clique explícito.
- A liquidação valida a compatibilidade entre mercado e seleção.
- Placar negativo, cotação inválida e entrada negativa são bloqueados.
- A atualização remota da liquidação é feita por linha, reduzindo chamadas à API.
- Falha da planilha não elimina a liquidação local.
- O maior recuo é calculado em ordem cronológica.
- A banca informada não recebe o lucro histórico novamente.

## Preferências operacionais preservadas

- não existe validade artificial de cotações;
- não existe CLV ou cálculo de fechamento;
- a interface usa nomenclatura operacional em português;
- o modelo V28.0 e a API 28.1.2 foram preservados.
