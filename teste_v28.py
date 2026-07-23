from pathlib import Path
import pandas as pd
from tex_v25_core import normalize_zip
from tex_v28_core import INPUT_COLUMNS, analyze_games, load_v28_model

ROOT=Path(__file__).resolve().parent
matches=normalize_zip(ROOT/'data'/'TEX_V22_DADOS_24_LIGAS.zip',include_incomplete_annual_2026=True)
model=load_v28_model(ROOT/'model')
rows=[
 {'ID':'a1','Data':'2026-07-23','Hora':'19:30','Código da liga':'BRA','Liga':'Brasileirão Série A','Mandante':'Corinthians','Visitante':'Remo','Casa de apostas':'Pixbet','Odd mandante':1.49,'Odd empate':4.01,'Odd visitante':6.70,'Odd mais de 2,5':1.95,'Odd menos de 2,5':1.81,'Odd ambas marcam — Sim':2.08,'Odd ambas marcam — Não':1.68},
 {'ID':'a2','Data':'2026-07-23','Hora':'19:30','Código da liga':'BRA','Liga':'Brasileirão Série A','Mandante':'Botafogo RJ','Visitante':'Vitoria','Casa de apostas':'Pixbet','Odd mandante':1.78,'Odd empate':3.66,'Odd visitante':4.81,'Odd mais de 2,5':1.78,'Odd menos de 2,5':1.99,'Odd ambas marcam — Sim':1.77,'Odd ambas marcam — Não':2.02},
 {'ID':'a3','Data':'2026-07-25','Hora':'19:30','Código da liga':'BRA','Liga':'Brasileirão Série A','Mandante':'Santos','Visitante':'Chapecoense-SC','Casa de apostas':'Pixbet','Odd mandante':1.40,'Odd empate':4.55,'Odd visitante':7.30,'Odd mais de 2,5':1.66,'Odd menos de 2,5':2.14,'Odd ambas marcam — Sim':1.87,'Odd ambas marcam — Não':1.89},
]
games=pd.DataFrame(rows,columns=INPUT_COLUMNS)
entries,readings,evaluations,diagnostics=analyze_games(games,matches,model,1000,.01,4)
assert len(readings)==3
assert len(evaluations)==21
assert (evaluations['Market']=='BTTS').sum()==6
assert evaluations[evaluations['Market']=='BTTS']['Status'].eq('EXPERIMENTAL').all()
assert entries['MatchID'].nunique()==len(entries)
assert entries['ExpectedValue'].ge(0).all()
print('TESTE V28 OK')
print(entries[['Home','Away','Selection','Odd','DecisionProbability','ExpectedValue','Status']].to_string(index=False))
