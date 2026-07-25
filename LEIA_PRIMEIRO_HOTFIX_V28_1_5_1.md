# Tex Statistics V28.1.5.1 — Hotfix de Deploy

Este pacote corrige o erro de `ImportError` causado por deploy parcial ou mistura entre um `app.py` novo e módulos antigos.

## Substituição obrigatória

Substitua **todos os arquivos e pastas da raiz do repositório** pelo conteúdo deste diretório, principalmente:

- `app.py`
- `tex_v25_storage.py`
- `tex_v28_finance.py`
- `tex_v28_core_2812.py`
- `tex_operacional_core.py`
- `tex_v25_core.py`
- `requirements.txt`
- `data/`
- `model/`

Não envie a pasta externa nem apenas o ZIP. O `app.py` deve ficar diretamente na raiz do GitHub.

Após o commit, use **Manage app > Reboot app** no Streamlit Cloud. Os Secrets do Google Sheets não devem ser apagados.

O núcleo matemático continua sendo `CORE_API_VERSION = 28.1.2`.
