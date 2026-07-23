# Tex Statistics — Operacional Reconstruído

Esta reconstrução substitui o fluxo das versões V25–V27.1.

## Uso

1. Escolha a liga.
2. Escolha mandante e visitante nos seletores.
3. Informe data, horário e casa de apostas.
4. Marque os mercados que deseja analisar e digite as odds.
5. Adicione quantos jogos quiser.
6. Clique em **ANALISAR TODO O LOTE**.

Não há digitação do nome da liga ou das equipes. Não há CSV obrigatório e não há chave de API de odds.

## Mercados

- Resultado final 1X2
- Mais/menos de 2,5 gols
- Ambas marcam — Sim/Não

Cada mercado pode ser ativado ou desativado. Ao ativá-lo, todas as odds daquele mercado precisam ser preenchidas.

## Saídas

- **Entradas com preço:** no máximo uma por partida, apenas quando a odd supera as regras fixas.
- **Leitura principal:** sempre mostra a melhor leitura estatística de cada jogo, mesmo quando a odd não permite entrada.
- **Todos os mercados:** diagnóstico completo de cada seleção.
- **Diagnóstico:** erros de preenchimento ou falta de histórico.

## Diferença essencial em relação à V25

O portão `approved_zones_for_season` não participa da decisão ao vivo. A V25 transformava uma tabela histórica extremamente específica em bloqueio binário, o que gerou uma tela quase sempre vazia e liberou uma única seleção ruim.

Nesta reconstrução:

- o mercado sem margem é a referência principal;
- a calibração empírica histórica ajusta essa referência;
- o modelo Poisson/Dixon-Coles funciona apenas como verificação secundária e não cria sozinho uma entrada;
- cada jogo sempre recebe uma leitura principal;
- leitura estatística e entrada por preço são conceitos separados;
- o tamanho da entrada é fixo, sem Kelly ou progressão.

## Instalação no repositório

Copie os arquivos do patch para a raiz do repositório e aceite substituir os existentes. A pasta `calibration` deve ficar na raiz, ao lado de `app.py`.

Depois faça commit e push no GitHub. O Streamlit utiliza `app.py` como arquivo principal.

## Teste local do núcleo

```bash
python teste_operacional.py
```

O teste verifica as 24 ligas, os seletores de times, os três mercados, o bloqueio de odds acima de 3,00, a unidade fixa e o processamento dos jogos usados na auditoria da V25.
