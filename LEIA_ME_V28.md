# Tex Statistics V28

Aplicativo Streamlit com 24 ligas e seletores de times. O usuário informa apenas data, horário, casa e odds.

## Instalação no repositório

Copie todos os arquivos do patch para a raiz, preservando as pastas `model/` e `data/`. Faça commit e push. O modelo é executado por um interpretador puro em Python; o deploy não depende do pacote binário LightGBM.

## Fluxo

1. Escolha liga, mandante e visitante.
2. Informe odds 1X2, mais/menos 2,5 e Ambas Marcam.
3. Adicione todas as partidas disponíveis da semana.
4. Defina alvo de 3, 4 ou 5 entradas.
5. Clique em **ANALISAR TODO O LOTE**.
6. A aba **Carteira V28** mostra as entradas ranqueadas.
7. **SALVAR COTAÇÕES E PROBABILIDADES** grava a análise na planilha Google já configurada.

A V28 não usa Kelly nem progressão. Cada entrada usa unidade fixa.
