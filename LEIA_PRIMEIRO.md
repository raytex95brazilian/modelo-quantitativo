# Tex Statistics V28.2.0 — Filtro eliminatório de 2018

Esta versão foi construída diretamente sobre a **V28.1.5.12 — Autosave das cotações antes da análise**.

## O que foi preservado

- cadastro das partidas e das cotações;
- campo de banca atual e percentual da unidade;
- motor preditivo V28.1.2 — Estado Isolado;
- probabilidades de resultado final, Mais/Menos de 2,5 gols e Ambas Marcam;
- salvamento imediato do lote e das cotações antes da análise;
- controle financeiro e liquidação das apostas;
- mesma configuração da Planilha Google;
- todas as colunas antigas, na mesma ordem.

## O que foi acrescentado

1. **Filtro eliminatório de 2018**, com lista de verificação por partida.
2. Nenhum jogo reprovado pode aparecer em aposta simples ou múltipla.
3. Probabilidades e cotações de jogos aprovados e reprovados continuam sendo salvas.
4. Apostas simples sem meta mínima semanal e sem complemento com valor esperado negativo.
5. Campo **Sugestão de múltipla**, com apenas um mercado por confronto aprovado.
6. Produto das cotações, probabilidade conjunta aproximada, valor esperado conjunto e retorno potencial.
7. Interface reformulada e responsiva para desktop e celular.
8. Novas colunas anexadas à direita das colunas antigas nas abas existentes.

## Regras do filtro

- **Regra 1:** o visitante deve estar acima do mandante na classificação.
- **Exceção da Regra 1:** se estiver abaixo, deve conseguir ao menos igualar os pontos do mandante com mais três pontos.
- **Regra 2:** se as duas equipes marcaram no último confronto direto válido de pontos corridos, o evento é eliminado.
- **Exceção da Regra 2:** confrontos de competição que não seja de pontos corridos são ignorados, quando a fonte informa o tipo da competição.
- **Regra 3:** o mandante marcou em pelo menos quatro das últimas cinco partidas, sem separar casa e fora.
- **Regra 4:** o visitante marcou em pelo menos quatro das últimas cinco partidas, sem separar casa e fora.
- **Regra 5:** todas as regras anteriores precisam ser atendidas simultaneamente.

## Fluxo operacional

```text
Todos os jogos são cadastrados, calculados e salvos
                         ↓
              Filtro eliminatório de 2018
             ↙                           ↘
      REPROVADO                       APROVADO
salva tudo para a base       segue para análise estatística
não entra em apostas          e análise financeira das odds
                                         ↓
                         simples e sugestão de múltipla
```

## Compatibilidade com a Planilha Google

A versão continua usando as mesmas abas e o mesmo destino configurado nos Secrets.
As colunas antigas de `catalogo_odds` e `historico_analises` permanecem intactas e na mesma ordem.
As informações do filtro, decisão operacional e múltipla são acrescentadas somente **após a última coluna antiga**.

Na primeira gravação, o aplicativo acrescenta os novos cabeçalhos à direita, sem apagar linhas ou cabeçalhos existentes.

## Limitação atual da fonte

A base incluída contém 24 ligas de pontos corridos. As últimas cinco partidas são buscadas em todo o histórico carregado, sem separar mando e atravessando temporadas.
Copas, amistosos e outras competições só serão considerados quando estiverem presentes numa fonte futura. Portanto, a lógica está preparada para a exceção da Regra 2, mas a base atual é essencialmente formada por partidas de liga.

## Instalação

1. Substitua todos os arquivos do deploy pelo conteúdo desta pasta.
2. Preserve ou recoloque os mesmos Secrets do Google Sheets.
3. Confirme que `app.py` está na raiz do repositório.
4. Execute o reinício completo do aplicativo no Streamlit Cloud.
5. Na primeira análise, confira se as novas colunas foram acrescentadas à direita nas abas existentes.
