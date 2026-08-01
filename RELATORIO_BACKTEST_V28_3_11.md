# Backtest do filtro de 2018 — auditoria das 24 ligas

## Escopo

- Pacote auditado: Tex Statistics V28.3.10.
- Base: 111.937 partidas das 24 ligas, de 02/03/2012 a 20/07/2026.
- Procedimento: cada partida histórica foi tratada como futura; somente dados com data anterior foram usados.
- O avaliador otimizado foi confrontado com a função real `evaluate_lot_2018` em 144 casos distribuídos pelas 24 ligas e reproduziu integralmente status, regras e contagens de histórico.

## Resultado principal

A resposta é **sim**: o problema não estava restrito à 2. Bundesliga.

A V28.3.10 marcou 10.718 partidas como não avaliáveis (9,58%).  
Após corrigir a resolução de temporada, o número caiu para 6.675 (5,96%).

Foram encontrados **4.043 falsos “não avaliáveis”** provocados exclusivamente por temporada calculada incorretamente:

- 339 teriam sido aprovados no filtro;
- 3.704 teriam sido reprovados normalmente;
- 13 das 24 ligas foram afetadas.

## Causas técnicas

1. **Liga MX**: a fonte usa temporadas julho–maio, mas o app a tratava como ano-calendário.  
   Consequência: partidas de janeiro a maio eram associadas à temporada errada.

2. **Argentina histórica**: até 2020/21 a competição atravessava dois anos, mas o app a tratava como anual.

3. **Temporadas excepcionalmente estendidas**:
   - Brasileirão 2020 terminou em fevereiro de 2021;
   - China 2021 terminou em janeiro de 2022;
   - várias ligas europeias 2019/20 terminaram em julho/agosto de 2020.

   O corte fixo por mês reiniciava a classificação antes do encerramento real.

## Efeito por liga mais atingida

| Liga | Falsos não avaliáveis | Aprovadas ocultas |
|---|---:|---:|
| México — Liga MX | 2.279 | 200 |
| Argentina — Primera División | 1.086 | 87 |
| Brasileirão Série A | 112 | 6 |
| Itália — Série A | 98 | 16 |
| Inglaterra — Championship | 77 | 5 |
| Itália — Série B | 70 | 7 |
| Inglaterra — Premier League | 66 | 4 |
| Espanha — Segunda Divisão | 64 | 1 |
| Espanha — La Liga | 57 | 2 |
| Portugal — Primeira Liga | 47 | 4 |
| Turquia — Super Lig | 45 | 6 |
| Grécia — Super League | 30 | 0 |
| China — Super League | 12 | 1 |

## Casos realmente não avaliáveis após a correção

Mesmo com a temporada correta, 6.675 partidas (5,96%) permaneceram sem dados suficientes.

Isso ocorreu por razões legítimas do filtro:

- 3.325 não possuíam classificação corrente para as duas equipes;
- 2.709 não possuíam cinco jogos recentes válidos do mandante;
- 2.806 não possuíam cinco jogos recentes válidos do visitante;
- os motivos se sobrepõem;
- 3.129 ocorreram quando as duas equipes ainda tinham zero partidas anteriores na temporada.

Excluindo a primeira temporada disponível de cada liga — que sofre com o início da própria base — restaram 5.574 não avaliáveis em 104.153 partidas (5,35%).

Todas as 24 ligas apresentaram ao menos alguns casos legítimos, principalmente no começo da temporada e com clubes recém-promovidos ou ausentes da divisão na temporada anterior.

## Resultado esportivo do conjunto aprovado após a correção

Foram aprovadas 11.946 partidas.

- visitante marcou: 71,74%;
- X2: 62,18%;
- vitória do visitante: 34,61%;
- ambas marcaram: 54,09%;
- mais de 2,5 gols: 49,68%.

O padrão permanece coerente com o backtest anterior: o filtro destaca sobretudo visitantes competitivos e com capacidade de marcar; não transforma Mais de 2,5 em mercado universal.

## Correção aplicada na V28.3.11

A nova versão resolve a temporada nesta ordem:

1. usa o intervalo real de datas das temporadas presentes na base;
2. só usa a regra de calendário como contingência para datas futuras ainda ausentes;
3. trata a Liga MX como temporada julho–junho;
4. trata a Argentina como anual apenas a partir de 2021;
5. preserva temporadas excepcionalmente estendidas.

A regra rígida continua igual: uma temporada nova sem resultados anteriores permanece **NÃO AVALIÁVEL**, não aprovada nem reprovada.
