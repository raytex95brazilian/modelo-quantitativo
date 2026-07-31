# Relatório técnico — Tex Statistics V28.2.1

## 1. Configuração automática

O formulário lateral de confirmação foi removido. Os campos de banca e unidade usam estado de sessão e uma função de atualização automática. Quando algum valor muda, a análise anterior é invalidada para impedir que resultados calculados com outra banca permaneçam na tela.

## 2. Cotação justa

A cotação justa é calculada por:

`cotação justa = 1 / probabilidade final`

Ela é exibida separadamente da cotação mínima para operar. A cotação mínima pode ser superior à justa porque incorpora as regras conservadoras e o desconto operacional.

## 3. Simplificação visual

A tabela resumida foi reduzida aos campos usados para decisão. Os dados técnicos não foram apagados: continuam salvos na planilha e disponíveis em uma seção recolhida.

## 4. Gravação em lote

A rotina de atualização de `catalogo_odds` foi substituída pela implementação de controle de quota da V28.1.5.13, preservando todas as colunas acrescentadas na V28.2.0. Em produção, o pacote exige `gspread>=6.0` e usa `batch_update`.

## 5. Compatibilidade

Foram comparadas as listas de colunas da V28.2.0 e V28.2.1:

- `COLUNAS_COTACOES`: idênticas;
- `COLUNAS_ANALISES`: idênticas;
- `COLUNAS_LOTE_PENDENTE`: idênticas.

## 6. Testes executados

- compilação dos módulos;
- importação do aplicativo sem interface gráfica;
- filtro de 2018 e portão operacional;
- estabilidade dos formulários;
- autosave de cotações;
- confirmação de destino da planilha;
- gravação em lote e controle de quota;
- compatibilidade integral das colunas antigas.
