# Tex Statistics V28.3.13 — Reconhecimento da Veikkausliiga

## Falha reproduzida

A confirmação da importação bloqueava partidas da Finlândia — Veikkausliiga quando a casa de apostas apresentava nomes geográficos mais extensos do que a nomenclatura canônica da base. Foram reproduzidos os três casos informados:

- `VPS Vaasa` em vez de `VPS`;
- `Ilves Tampere` em vez de `Ilves`;
- `Seinajoen JK` em vez de `SJK`.

O bloqueio de segurança estava correto: o importador exige escore mínimo de reconhecimento e não deve gravar por aproximação insegura. O defeito era a ausência dessas equivalências explícitas.

## Correção

Foram adicionadas equivalências restritas à liga `FIN`, incluindo as grafias recebidas e variantes oficiais frequentes. O reconhecimento agora converte:

- `VPS Vaasa` e `Vaasan Palloseura` → `VPS`;
- `Ilves Tampere` e `Tampereen Ilves` → `Ilves`;
- `Seinajoen JK`, `SJK Seinajoki` e `Seinajoen Jalkapallokerho` → `SJK`.

A pré-visualização e a validação final usam o mesmo resolvedor, portanto os nomes são normalizados antes da gravação e não dependem de edição manual.

## Escopo preservado

Não foram alterados modelos, probabilidades, filtro de 2018, política financeira, mercados, planilhas, persistência, composição do lote ou critérios de aposta. A camada operacional continua na API `28.3.12`; somente o importador e a interface avançaram para `28.3.13`.

## Testes

Foi incluído teste específico cobrindo os três aliases informados, variantes oficiais e inferência conjunta da liga `FIN`. Também foram executados os testes de importação, validação final, carregamento do aplicativo e integridade do pacote.
