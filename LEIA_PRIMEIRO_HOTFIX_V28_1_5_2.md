# Tex Statistics V28.1.5.2 — correção dos seletores de ligas

## Erro corrigido

Os seletores de liga, mandante e visitante estavam dentro de um `st.form`.
No Streamlit, a troca de um campo dentro do formulário não executa novamente o
código Python antes do envio. Por isso a liga mudava na tela, mas o catálogo de
equipes continuava sendo o da primeira liga carregada.

## Solução

- liga e equipes foram retiradas do formulário;
- cada mudança de liga atualiza imediatamente o catálogo pelo código correto;
- o visitante é reconstruído quando o mandante muda;
- a tela informa a liga, a temporada e a quantidade de equipes do catálogo ativo;
- a disposição dos campos foi reorganizada para evitar colunas estreitas e rótulos truncados.

## Deploy

Substitua integralmente o conteúdo da raiz do repositório por este pacote e
execute **Reboot app** no Streamlit Cloud. Preserve os Secrets.

## Versões

- Interface: V28.1.5.2.
- Núcleo matemático: API 28.1.2, sem alteração.
- Armazenamento e finanças: API 28.1.5.1, sem alteração.
