"""Compatibilidade controlada com o núcleo isolado V28.1.2.

O aplicativo principal importa diretamente ``tex_v28_core_2812``. Este arquivo
existe apenas para scripts antigos que ainda usam ``tex_v28_core`` e impede que
dois núcleos diferentes sejam mantidos no mesmo pacote.
"""
from tex_v28_core_2812 import *  # noqa: F401,F403
from tex_v28_core_2812 import __all__
