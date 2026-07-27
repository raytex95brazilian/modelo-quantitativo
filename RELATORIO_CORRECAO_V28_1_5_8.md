# Relatório de correção — Tex Statistics V28.1.5.8

## Defeito corrigido

A lista de partidas existia somente em `st.session_state`. Qualquer perda de sessão, reinicialização do processo, atualização do deploy ou falha que recriasse a sessão podia devolver uma lista vazia. Além disso, a gravação histórica dependia de o usuário analisar o lote e clicar posteriormente em um botão de salvamento.

## Alterações

- autosave imediato do lote bruto ao adicionar, atualizar ou remover uma partida;
- criação automática da aba Google `lote_pendente`;
- snapshot completo com horário, quantidade, versão e JSON do lote;
- backup local atômico em `data/tex_v28_lote_pendente.json` durante a execução;
- restauração automática do snapshot mais recente após nova sessão ou reboot;
- persistência de lote vazio somente após confirmação explícita de exclusão;
- remoção do botão de limpeza direta e perigosa;
- backup CSV disponível em qualquer momento;
- salvamento automático das cotações e probabilidades ao concluir a análise;
- botão manual convertido em tentativa de repetição/confirmação;
- casa de apostas padrão definida como `PIXBET`, permanecendo editável;
- versões de armazenamento e finanças elevadas para `28.1.5.8`.

## Limitações honestas

O backup local do Streamlit Cloud não é permanente entre todas as substituições de instância. A persistência durável depende da Planilha Google conectada. Quando o Google falha, o aplicativo mantém o lote na sessão e no arquivo local e exibe um aviso explícito; não afirma que houve salvamento remoto.

Dados que já haviam desaparecido antes desta versão e nunca foram gravados em nenhuma aba ou arquivo não podem ser reconstruídos pelo aplicativo.

## Testes

- compilação integral dos módulos Python;
- importação do app sem interface gráfica;
- salvamento e restauração do lote em Google Sheets simulado;
- restauração após remoção completa de `session_state`;
- atualização e limpeza confirmada do snapshot;
- catálogo das 24 ligas;
- núcleo V28.1.2 e modelo;
- armazenamento, liquidação e finanças;
- análise e geração dos registros históricos.
