# Tex Statistics V28.3.11 — Correção de temporadas nas 24 ligas

Esta versão foi construída sobre a V28.3.10 após um backtest cronológico de 111.937 partidas das 24 ligas.

## Problema encontrado

A identificação da temporada usava regras fixas de calendário. Isso produzia falsos `NÃO AVALIÁVEL` quando a temporada real não coincidia com o ano civil ou com o corte fixo de julho.

Os principais casos foram:

- Liga MX: temporadas julho–maio eram tratadas como anuais;
- Argentina histórica: ciclos anteriores a 2021 atravessavam dois anos;
- Brasileirão 2020: encerramento em fevereiro de 2021;
- China 2021: encerramento em janeiro de 2022;
- ligas europeias 2019/20: encerramento excepcional em julho/agosto de 2020.

## Resultado do backtest

- 111.937 partidas auditadas;
- 10.718 não avaliáveis na V28.3.10;
- 6.675 não avaliáveis após a correção;
- 4.043 falsos não avaliáveis eliminados;
- 339 partidas aprovadas estavam sendo ocultadas;
- 13 das 24 ligas foram afetadas pela falha de temporada;
- todas as 24 ligas possuem alguns casos legítimos sem dados, sobretudo no início da temporada.

## O que mudou

A temporada agora é resolvida nesta ordem:

1. intervalo real de datas de cada temporada existente na base;
2. regra de calendário apenas como contingência para datas futuras ainda ausentes;
3. Liga MX tratada como temporada que atravessa dois anos;
4. Argentina tratada como anual somente a partir de 2021;
5. temporadas excepcionalmente prolongadas permanecem no ciclo correto.

## O que não mudou

- filtro de 2018 continua sendo o portão obrigatório;
- partida realmente sem classificação corrente ou sem cinco jogos recentes continua `NÃO AVALIÁVEL`;
- não avaliável não entra em simples nem em múltipla;
- nenhuma coluna da planilha foi removida, renomeada ou deslocada;
- importação, cotações, probabilidades, gols esperados e interface foram preservados.

Consulte `RELATORIO_BACKTEST_V28_3_11.md` para os números completos.
