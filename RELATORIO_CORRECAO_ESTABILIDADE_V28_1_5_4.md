# Relatório de correção — estabilidade de interação — V28.1.5.4

## Defeito

Na V28.1.5.3, os campos de data, horário, casa de apostas, mercados e cotações estavam fora de `st.form`. O modelo de execução padrão do Streamlit reexecutava o script quando cada widget enviava um novo valor, produzindo piscadas, sensação de recarregamento e risco de perda de rascunho.

## Correção

- `st.fragment` limita a reexecução dos seletores dependentes ao quadro de escolha do confronto.
- A entrada foi dividida em duas etapas: escolha/confirmação do confronto e preenchimento dos dados.
- Todos os campos digitáveis da partida ficam em `st.form` e são enviados somente no botão final.
- Banca, unidade e máximo semanal também ficam em formulário próprio.
- O confronto confirmado é preservado em `st.session_state`.
- O núcleo V28.1.2 e os artefatos do modelo não foram modificados.

## Testes acrescentados

- `teste_estabilidade_formularios.py`;
- atualização de `teste_seletores_ligas.py`;
- atualização do teste de integridade e do teste de importação simulada.
