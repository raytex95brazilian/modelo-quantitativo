# Tex Statistics V28.3.14 — Catálogo universal das 24 ligas

## Problema resolvido

A validação anterior usava principalmente o elenco da temporada mais recente de cada liga. Isso podia bloquear:

- clubes promovidos ou rebaixados;
- equipes que retornavam à divisão após algumas temporadas;
- nomes históricos ainda válidos;
- denominações comerciais usadas por casas de apostas;
- siglas, nomes oficiais extensos e variações com cidade, estado, prefixo ou sufixo institucional.

O erro da Veikkausliiga foi apenas uma manifestação desse problema estrutural.

## Implementação

A V28.3.14 cria três catálogos complementares:

1. **catálogo recente**, mantido para os seletores manuais;
2. **catálogo universal**, com todas as equipes observadas em todas as temporadas das 24 ligas;
3. **catálogo por temporada**, usado para priorizar o elenco correspondente à data da partida.

Na base local auditada, o catálogo universal contém:

- 24 ligas;
- 888 vínculos liga/equipe;
- 783 nomes canônicos distintos;
- 163 aliases explícitos para casos não dedutíveis apenas por normalização.

O arquivo `CATALOGO_UNIVERSAL_EQUIPES_24_LIGAS.csv` permite auditar cada nome canônico, suas formas normalizadas, siglas calculadas, aliases explícitos e temporadas observadas.

## Reconhecimento de nomes

A resolução passa a combinar, nesta ordem:

- alias explícito;
- igualdade canônica normalizada;
- equivalência de abreviações frequentes;
- remoção controlada de prefixos e sufixos institucionais;
- preservação de qualificadores geográficos necessários para distinguir clubes, como `GO` e `MG`;
- reconhecimento de siglas e acrônimos;
- comparação por tokens e contenção;
- similaridade textual;
- prioridade para o elenco da temporada da partida;
- validação simultânea do mandante e do visitante na mesma liga;
- bloqueio quando dois candidatos permanecem empatados sem margem segura.

## Correção da validação final

A prévia e o clique final de gravação agora consultam o mesmo catálogo universal. Assim, uma equipe reconhecida na prévia não volta a ser rejeitada apenas por não constar no recorte mais recente da liga.

## Cobertura

O teste `teste_catalogo_universal_24_ligas_v28_3_14.py` verifica:

- presença das 24 ligas;
- inclusão de todos os 888 vínculos liga/equipe da base local;
- correspondência de todos os nomes canônicos;
- variações institucionais sem ambiguidade;
- pelo menos um caso comercial ou oficial por liga;
- os nomes `VPS Vaasa`, `Ilves Tampere` e `Seinajoen JK`;
- compatibilidade com os catálogos recente e sazonal.

O pacote contém 30 arquivos de teste. Todos foram executados antes da geração final.

## Escopo preservado

Não foram alterados:

- motor preditivo V28.1.2;
- filtro de 2018;
- política financeira;
- cálculo de probabilidades;
- mercados;
- estrutura das planilhas;
- armazenamento;
- composição das apostas simples ou múltiplas.

A alteração está restrita ao catálogo de equipes, reconhecimento de aliases, inferência de liga e validação da importação.
