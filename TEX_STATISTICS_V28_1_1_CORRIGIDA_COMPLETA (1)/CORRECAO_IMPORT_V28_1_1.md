# Correção V28.1.1 — sincronização de imports

O erro ocorria quando `app.py` e `tex_v28_core.py` eram publicados em revisões diferentes.
A aplicação fazia uma importação rígida de vários símbolos e o Streamlit encerrava antes de abrir a tela.

Correções:

- `app.py` importa os módulos completos e valida a versão da API interna.
- `tex_v28_core.py` declara `CORE_API_VERSION = "28.1.1"`.
- o patch inclui juntos todos os núcleos dependentes para impedir mistura de versões.
- em eventual deploy parcial, a tela mostra quais arquivos estão desencontrados em vez de um ImportError genérico.

Substituir todos os arquivos do patch na raiz do repositório, incluindo a pasta `model`.
