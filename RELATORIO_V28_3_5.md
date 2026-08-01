# Relatório técnico — Tex Statistics V28.3.5

## Ocorrência analisada

A interface exibiu:

```text
APIError: [503]: The service is currently unavailable.
```

Esse retorno comprova uma indisponibilidade temporária do serviço remoto durante aquela tentativa. Não é possível atribuí-lo a quota de escrita; quota é normalmente indicada por HTTP 429.

## Defeito encontrado na V28.3.4

A inspeção de `tex_v25_storage.py` mostrou que `_executar_com_backoff` repetia somente erros classificados por `_erro_de_quota`, isto é, principalmente 429. O código não reconhecia 503, 502, 504, timeouts ou erros temporários equivalentes.

Consequência: um 503 era propagado imediatamente para a interface.

Há uma dificuldade adicional: em operações de append, o servidor pode gravar as linhas e ainda assim devolver 503 ao cliente. Repetir cegamente o mesmo append pode duplicar registros.

## Alterações

1. Classificação de falhas temporárias:
   - 408, 425, 429, 500, 502, 503 e 504;
   - service unavailable, backend error, gateway timeout, timeout e falhas de conexão equivalentes.
2. Backoff exponencial curto com jitter para leituras e escritas idempotentes.
3. Novo append idempotente por ID:
   - mantém os mesmos IDs durante a tentativa;
   - após 503, consulta a coluna de identificadores;
   - considera confirmados os registros encontrados;
   - repete somente os ausentes;
   - evita append duplicado quando a gravação ocorreu antes da falha da resposta.
4. Aplicação ao log `entrada_jogos`, ao catálogo `catalogo_odds` e aos registros append-only de análises/auditoria.
5. Atualizações de snapshot e cabeçalhos passaram a usar retry seguro.
6. Mensagem de interface específica para 503 e detalhes técnicos recolhidos.
7. Indicador visual de progresso durante a importação.

## Teste específico de 503

Foi criado `teste_erro_503_idempotencia_v28_3_5.py` com dois cenários:

- duas respostas 503 seguidas de sucesso em operação idempotente;
- append que grava três linhas e lança 503 depois da gravação.

No segundo cenário, a rotina localiza os três IDs, confirma as linhas e termina com uma única chamada de append. Nenhuma linha é duplicada.

## Compatibilidade

Não foram alteradas colunas, nomes de abas, regras do filtro de 2018, cálculos estatísticos, cotações, importador ou lógica de apostas. A mudança está concentrada na resiliência do armazenamento e na apresentação do erro.

## Limitação da validação

Os testes usam simulações controladas da API. Não foi utilizado o Google Sheets real do usuário nem suas credenciais. Uma indisponibilidade prolongada do Google ainda pode impedir a gravação após todas as tentativas; nesse caso, os dados permanecem preenchidos na interface para nova tentativa.
