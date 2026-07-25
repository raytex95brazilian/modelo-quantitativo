# Relatório de correção de usabilidade — V28.1.5.5

## Problemas corrigidos

1. O fluxo em duas etapas exigia confirmar o confronto antes de informar as cotações.
2. Campos numéricos eram inicializados em `0,00`, obrigando o usuário a apagar valores.
3. A casa de apostas era preenchida automaticamente.
4. Liga e equipes precisavam continuar reativas sem provocar perda dos campos já digitados.
5. O texto para uso em IA ficava pouco evidente e associado ao download.

## Solução

- A interface agora mostra confronto, data, horário, casa e mercados na mesma etapa visual.
- Liga, mandante e visitante permanecem em `st.fragment` e atualizam somente esse trecho.
- Data, horário, casa e cotações permanecem em `st.form`, evitando rerun durante a digitação.
- Selectboxes usam `index=None`; data, horário e cotações usam `value=None`; a casa usa string vazia.
- A seção **Análise para IA** é exibida diretamente com bloco copiável; o download é apenas opcional.
- Validações impedem envio sem confronto, data, horário ou cotações exigidas pelos mercados marcados.

## Preservação do motor

Nenhuma alteração foi feita no motor preditivo V28.1.2, no modelo LightGBM ou nos artefatos do backtest.
