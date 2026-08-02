# Tex Statistics V28.3.17 — reconhecimento da Süper Lig 2026/27

## Ocorrência reproduzida

A V28.3.16 bloqueava a confirmação de partidas com os nomes comerciais:

- `Çorum FK`;
- `Amed SK`;
- `Göztepe İzmir`.

O catálogo universal era formado pelo histórico das primeiras divisões. Çorum FK e Amed SK não possuíam ocorrência anterior na Süper Lig dentro da base local, enquanto `Göztepe İzmir` não coincidia com o nome canônico histórico `Goztep`.

## Correção

- incluídos `Amed SK` e `Corum FK` como candidatos sazonais da liga `T1` em 2026/27;
- incluídas variantes de Amed, Çorum e Göztepe usadas por casas de apostas;
- mantido `Goztep` como nome canônico histórico para preservar a ligação com os dados existentes;
- mantidos inalterados o motor V28.1.2, o filtro de 2018, a política financeira, o armazenamento e as colunas das planilhas.

## Resultado esperado

- `Çorum FK` → `Corum FK`;
- `Amed SK` → `Amed SK`;
- `Göztepe İzmir` → `Goztep`.

Clubes sem histórico de primeira divisão podem ser importados, mas a análise continuará declarando dados insuficientes quando não houver amostra esportiva mínima. Nenhum histórico é inventado.

## Contingência para futuros promovidos

A interface recebeu uma opção explícita e desmarcada por padrão para aceitar um clube novo ausente do histórico. O usuário deve selecionar a liga, conferir os nomes e marcar a autorização. O nome é transliterado de forma conservadora e salvo sem qualquer histórico inventado. Esse recurso evita nova alteração de código quando surgir um promovido legítimo ainda ausente do catálogo, mantendo o bloqueio seguro como comportamento padrão.
