# Tex Statistics V28.1.2 — correção de módulo desencontrado

Esta correção usa um módulo com nome novo: `tex_v28_core_2812.py`.

O nome novo impede que o Streamlit reutilize ou importe uma revisão antiga de `tex_v28_core.py`.

## Substituição

1. Copie `app.py` para a raiz, substituindo o atual.
2. Adicione `tex_v28_core_2812.py` na raiz.
3. Remova a pasta `__pycache__` do repositório e não a envie novamente.
4. Faça commit e push dos dois arquivos.
5. Reinicie o app no Streamlit Cloud.

O arquivo antigo `tex_v28_core.py` pode permanecer, mas a V28.1.2 não o importa.
