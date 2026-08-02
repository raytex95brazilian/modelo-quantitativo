# Tex Statistics V28.3.16 — Normalização de nomes localizados

## Falha reproduzida

A casa de apostas forneceu `IFK Gotemburgo`, enquanto o nome canônico da base sueca é `Goteborg`. A V28.3.15 aceitava `IFK Goteborg`, mas não convertia o exônimo português `Gotemburgo`; o escore resultante era insuficiente e a gravação era bloqueada.

## Correção

- `IFK` passou a ser tratado como prefixo institucional;
- exônimos frequentes passaram por equivalência de tokens antes da comparação;
- aliases explícitos agora são consultados também depois da remoção de artigos/prefixos e da conversão de grafias localizadas;
- `IFK Gotemburgo`, `IFK Gothenburg` e `IFK Göteborg` convergem para `Goteborg`;
- o mesmo mecanismo cobre exemplos como `Bayern de Munique`, `Inter de Milão` e `Sporting de Lisboa`;
- pré-visualização e validação final continuam usando o mesmo reconhecedor.

## Escopo preservado

Nenhum cálculo esportivo, financeiro, filtro, coluna de planilha, persistência, modelo ou regra de apostas foi alterado.

## Limite técnico

Nenhum catálogo pode antecipar toda grafia comercial futura. Quando surgir uma forma realmente nova, a interface continua bloqueando a gravação em vez de associar uma equipe errada.
