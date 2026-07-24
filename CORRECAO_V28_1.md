# CORREÇÃO V28.1 — ESTADO DO LOTE E ISOLAMENTO DAS ODDS

## Erro confirmado

A V28 mantinha os resultados da última análise no `session_state` mesmo depois que uma partida era adicionada ou atualizada. Assim, a tabela do lote podia exibir odds corrigidas enquanto o resumo para IA continuava mostrando as odds usadas na análise anterior.

O formulário também preservava os valores dos campos entre partidas, aumentando o risco de reaproveitamento acidental de odds.

## Correções

- Toda inclusão, atualização, remoção ou limpeza do lote invalida imediatamente resultados, carteira e resumo anteriores.
- Cada análise recebe um hash SHA-256 de todo o lote, incluindo todas as odds. Resultados só permanecem válidos enquanto o hash for idêntico.
- Os campos do formulário recebem chaves novas e são reiniciados após cada partida salva.
- Cada partida é armazenada como cópia independente do dicionário de entrada.
- Linhas de mercado matematicamente incoerentes são bloqueadas antes de salvar e novamente antes de analisar.
- 1X2 aceita soma implícita entre 98% e 130%; mercados de duas vias entre 98% e 122%.
- Mercado experimental não pode mais ultrapassar mercado validado na leitura principal.

## Regressão reproduzida

Linha real Athletico-PR x Internacional: 1,99 / 3,24 / 3,87.

- soma implícita: 106,96%; aceita;
- probabilidade sem margem do Athletico-PR: 46,98%.

Linha misturada observada no resumo antigo: 1,99 / 4,55 / 7,30.

- soma implícita: 85,93%; bloqueada como `ODDS INCONSISTENTES`.

## Testes executados

- compilação de `app.py` e `tex_v28_core.py`;
- teste original da V28;
- alteração de uma única odd muda o hash do lote;
- três partidas consecutivas mantêm odds isoladas por `InputID`;
- normalização da linha real do Athletico-PR;
- bloqueio da linha misturada;
- leitura principal nunca usa `EXPERIMENTAL` quando existe mercado validado.

Com as odds reais do lote apresentado, a entrada falsa no Athletico-PR desaparece.
