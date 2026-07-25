# Relatório de correção — seletores das 24 ligas — V28.1.5.2

## Falha observada

Ao selecionar uma liga diferente do Brasileirão, o nome da liga mudava na tela,
mas os seletores de mandante e visitante continuavam exibindo clubes brasileiros.

## Causa raiz

Liga, mandante e visitante estavam dentro de `st.form`. O Streamlit não executa
o script novamente quando um widget interno do formulário muda; ele só envia os
novos valores quando o botão de submissão é pressionado. Assim, o navegador
mostrava a nova liga, enquanto o Python ainda usava o catálogo calculado para a
liga anterior.

## Evidência da base

A base local foi verificada diretamente:

- Brasileirão 2026: 20 equipes brasileiras;
- Liga MX 2026: 18 equipes, incluindo Club America, Tigres UANL, Toluca e Monterrey;
- todas as 24 ligas possuem catálogo não vazio.

Portanto, não havia contaminação na base histórica; a falha era exclusivamente
na atualização reativa da interface.

## Correções

- remoção dos seletores dependentes de `st.form`;
- reconstrução imediata das equipes ao mudar a liga;
- chave do mandante vinculada ao código da liga;
- chave do visitante vinculada ao código e ao mandante;
- indicação visível do catálogo ativo, temporada e quantidade de equipes;
- reorganização responsiva: data, horário e liga na primeira linha; mandante e
  visitante na segunda; mercados em linhas próprias.

## Validação

- 24 catálogos carregados e não vazios;
- Liga MX contém clubes mexicanos e não contém Athletico-PR;
- Brasileirão contém Athletico-PR e não contém Club America;
- compilação do app concluída;
- testes de núcleo, estado, finanças, armazenamento, integridade e importação do
  app passaram.

## Versões

- Interface: V28.1.5.2;
- núcleo preditivo: API 28.1.2, sem alteração;
- armazenamento: API 28.1.5.1, sem alteração;
- finanças: API 28.1.5.1, sem alteração.
