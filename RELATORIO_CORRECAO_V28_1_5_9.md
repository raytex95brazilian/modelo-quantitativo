# Relatório de correção — Tex Statistics V28.1.5.9

## Defeito corrigido

As versões anteriores mantinham o lote principalmente no `st.session_state` e, na V28.1.5.8, aceitavam a partida mesmo quando o autosave remoto falhava. O snapshot em uma única célula também podia ser sobrescrito e não fornecia trilha de auditoria.

## Persistência durável

- Nova aba `entrada_jogos`, em formato append-only.
- Cada inclusão ou alteração gera uma linha `UPSERT` antes de o formulário ser limpo.
- Cada remoção gera uma linha `DELETE` antes de desaparecer da tela.
- A limpeza total gera uma linha `CLEAR` e continua exigindo confirmação.
- O lote é reconstruído pelo histórico de eventos após refresh, rerun, queda de sessão ou reboot.
- A aba antiga `lote_pendente` permanece apenas como cópia-resumo redundante.
- Se o Google estiver configurado e não confirmar o append, a partida não é aceita, o app não executa `rerun` e os campos permanecem preenchidos para nova tentativa.
- Antes de analisar, o lote da tela é comparado com o lote reconstruído da planilha; divergências bloqueiam a análise.
- A casa de apostas padrão continua sendo `PIXBET`, editável.
- Após a análise, cotações e probabilidades continuam sendo gravadas automaticamente nas abas históricas.

## Limitação de recuperação

Partidas que desapareceram em versões antigas e nunca foram gravadas em nenhuma aba ou arquivo não podem ser reconstruídas pelo pacote. A V28.1.5.9 impede a repetição desse cenário para novas inclusões quando o Google Sheets está conectado.
