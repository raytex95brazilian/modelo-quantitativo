# Tex Statistics V28.1.5.7 — decisão fechada na cotação informada

## Identificação

- **Interface:** Tex Statistics V28.1.5.7
- **Motor preditivo:** V28.1.2 — Estado Isolado
- **Modelo:** V28.0
- **Política operacional:** meta semanal de cinco seleções, no máximo uma por partida.

## Regra de uso

A análise é concluída com as cotações digitadas no lote. O aplicativo não cria estado de espera, não pede acompanhamento posterior e não pressupõe que o usuário voltará para atualizar odds.

As decisões visíveis são:

- **OPERAR:** seleção incluída na carteira com a cotação informada;
- **NÃO SELECIONADA:** seleção avaliada, mas não incluída na carteira final;
- **DESCARTAR:** cotação informada não atende ao piso operacional;
- **AMOSTRA INSUFICIENTE:** evidência histórica inadequada;
- **FORA DA FAIXA:** cotação efetiva fora da faixa testada;
- **EXPERIMENTAL:** Ambas Marcam, fora da carteira validada.

Os cálculos internos continuam usando a cotação informada, o desconto operacional de 2%, a probabilidade conservadora e o ranking semanal. Foram removidos da interface e do resumo para IA os estados e indicadores que sugeriam aguardar ou acompanhar uma cotação futura.

## Deploy

Envie todo o conteúdo desta pasta para a raiz do repositório conectado ao Streamlit, preserve os Secrets e execute **Manage app → Reboot app**.
