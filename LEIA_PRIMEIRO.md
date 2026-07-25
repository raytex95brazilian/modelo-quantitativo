# Tex Statistics V28.1.5.4 — estabilidade dos formulários

Este hotfix corrige a reexecução visível do aplicativo a cada campo preenchido.

## O que mudou

1. A configuração operacional da barra lateral foi colocada em formulário e só é aplicada pelo botão **APLICAR CONFIGURAÇÃO**.
2. Liga, mandante e visitante ficam em um fragmento independente. Alterar esses seletores atualiza apenas o quadro de confronto.
3. Depois da confirmação do confronto, data, horário, casa de apostas, mercados e cotações são preenchidos em um único formulário.
4. Digitar ou sair de um campo de cotação não reexecuta o app e não apaga valores.
5. Para mudar liga ou equipes, use **ALTERAR CONFRONTO** antes de enviar a partida.

## Versões

- Interface: Tex Statistics V28.1.5.4
- Motor preditivo: V28.1.2 — Estado Isolado
- API do núcleo: 28.1.2

Substitua todo o conteúdo da raiz do repositório pelo conteúdo desta pasta e execute **Reboot app** no Streamlit Cloud.
