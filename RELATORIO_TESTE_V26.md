# Relatório de teste — Tex Statistics v.26 Operacional

## Verificações executadas

- Compilação sintática de todos os módulos: **aprovada**.
- Recuperação de cotações corrompidas por formatação de data: **aprovada**.
  - `31.12` + probabilidade implícita de 55,5556% → odd 1,80.
  - `1.1` + probabilidade implícita de 46,7290% → odd 2,14.
- Reprodução da carteira posterior da V25: **aprovada**.
  - 547 seleções.
  - 341 vitórias.
  - lucro de +33,8264 unidades.
  - ROI de +6,18%.
- Processamento dos 11 jogos atuais fornecidos: **aprovado**.
  - 11 partidas processadas sem erro.
  - 55 mercados avaliados.
  - 1 seleção operacional: Bragantino x Coritiba — Mais de 2,5 gols, odd 1,86.

## Interpretação

A V26 transforma a regra congelada em carteira semanal e não inventa entradas para aumentar volume. Nos mesmos 11 jogos do Brasileirão, o resultado permanece uma entrada. O volume histórico de 3,28 entradas por semana ativa foi obtido com cobertura das 24 ligas, não somente com uma rodada brasileira.

## Limite do teste local

O ambiente de construção não possui o executável Streamlit instalado, portanto a interface web não pôde ser iniciada aqui. A lógica, os arquivos, os imports do núcleo e os testes de carteira foram executados. O `requirements.txt` inclui Streamlit para a execução no repositório/Streamlit Cloud.
