# Relatório de correção — Tex Statistics V28.1.5.12

## Defeitos confirmados na V28.1.5.9

1. O cadastro da partida gravava as cotações somente na aba técnica `entrada_jogos`. As abas históricas `catalogo_odds` e `historico_analises` continuavam sendo preenchidas apenas depois de **Analisar todo o lote**.
2. Quando `spreadsheet_id` não estava presente ou era lido com outra chave, o armazenamento usava silenciosamente um ID antigo embutido no código. Assim, o app podia informar sucesso enquanto o usuário conferia outra planilha.
3. O código considerava o retorno do `append_rows` suficiente. Não relia a linha para confirmar ID da partida, confronto e cotações.

## Correções da V28.1.5.12

- Removido o fallback silencioso para a planilha antiga.
- `spreadsheet_id` ou `spreadsheet_url` tornou-se obrigatório nos Secrets.
- A interface exibe o final do ID da planilha, a aba de destino e um botão que abre exatamente o destino configurado.
- Ao adicionar uma partida, o app grava na aba `entrada_jogos`, relê a linha e compara:
  - ID do evento e da partida;
  - data, hora, liga e confronto;
  - casa de apostas;
  - todas as cotações digitadas.
- O formulário só é limpo e o rerun só ocorre depois de a leitura pós-gravação passar.
- A confirmação mostra aba, número da linha, ID do evento e cotações lidas de volta.
- Se a planilha estiver errada, inacessível ou devolver valores divergentes, a partida não é aceita e os campos permanecem preenchidos.
- O salvamento de `catalogo_odds` e `historico_analises`, após a análise, também passou a reler e conferir o intervalo gravado.
- Casa de apostas padrão: `PIXBET`, editável.

## Limitação de validação

Os testes automatizados simulam respostas, intervalos e divergências da API do Google Sheets. Este ambiente não possui acesso às credenciais privadas nem à planilha real do usuário; por isso, a gravação ao vivo precisa ser confirmada após o deploy com uma única partida de teste.
