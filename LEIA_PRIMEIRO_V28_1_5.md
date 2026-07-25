# Tex Statistics V28.1.5 — leia primeiro

Este pacote consolida o estado alinhado do Tex Statistics sem alterar o artefato preditivo treinado. A revisão corrige arquitetura, controle de estado, limite semanal, auditoria, armazenamento e liquidação.

## Matriz de versões

As identificações têm funções diferentes:

- **Interface:** V28.1.5 — operação, auditoria e liquidação.
- **API do núcleo:** 28.1.2 — núcleo isolado em `tex_v28_core_2812.py`.
- **Artefato do modelo:** V28.0 — registrado em `model/metadata.json`.

O `app.py` importa diretamente `tex_v28_core_2812.py` e interrompe a execução quando a API encontrada não é exatamente `28.1.2`. O arquivo `tex_v28_core.py` é somente uma ponte de compatibilidade para scripts antigos.

## Implantação

1. Substitua todos os arquivos do repositório pelos arquivos deste pacote.
2. Não misture módulos da V28.1.1, V28.1.3 ou V28.1.4 com esta revisão.
3. Preserve a estrutura das pastas `data/`, `model/` e `backtest/` exatamente como está no pacote.
4. Faça o envio ao GitHub e um novo deploy no Streamlit.
5. Mantenha nos segredos do Streamlit a conta de serviço do Google já utilizada pelo projeto.
6. Confirme que a conta de serviço possui permissão de edição na planilha.

A planilha continua usando as abas:

- `catalogo_odds`;
- `historico_analises`;
- `auditoria_entradas`.

As colunas antigas são preservadas. Colunas novas são acrescentadas à direita por migração não destrutiva.

## Regras operacionais

- O aplicativo é exclusivamente pré-jogo e bloqueia partidas cujo horário já passou.
- A unidade fixa pode variar de 0,1% a 2,0% da banca informada.
- O limite padrão é de **cinco entradas por semana**, mas nunca é uma meta obrigatória.
- O limite semanal desconta apostas já registradas em lotes e sessões anteriores, quando o histórico está sincronizado.
- Uma partida com aposta já registrada não recebe uma segunda entrada automática.
- 1X2 e Mais/Menos 2,5 participam da carteira financeiramente validada.
- Ambas Marcam — Sim/Não permanece visível como análise complementar, sem entrada automática.
- Não há vencimento artificial de cotações, cálculo de fechamento de mercado ou CLV.
- Salvar análises e registrar apostas exigem cliques explícitos.
- A interface apresenta os termos operacionais em português.

## Persistência financeira

A aba `auditoria_entradas` é a fonte persistente recomendada. O arquivo local `data/tex_v28_apostas.csv` é contingência da instalação e pode ser perdido em reinicializações do Streamlit Cloud.

Quando a planilha não pode ser sincronizada, o aplicativo avisa que o limite semanal está usando somente o histórico local. A liquidação é preservada localmente mesmo quando a atualização remota falha, ficando pendente de sincronização posterior.

A banca exibida no painel financeiro é a banca informada pelo usuário. O sistema não soma novamente o lucro histórico a esse valor, evitando dupla contagem.

## Validação antes do deploy

Na raiz do projeto, execute:

```bash
python -m py_compile *.py
python teste_import_v28_1_2.py
python teste_v28.py
python teste_v28_correcao_estado.py
python teste_v28_finance.py
python teste_v28_storage.py
python teste_integridade_pacote.py
python teste_app_sem_interface.py
```

Todos os testes devem terminar com `OK`.

## Limites de interpretação

O sistema reduz inconsistências e aplica filtros conservadores, mas não elimina risco esportivo, risco de mercado, falhas de fonte externa, erro humano ou perdas financeiras. Resultados retrospectivos não garantem resultados futuros.
