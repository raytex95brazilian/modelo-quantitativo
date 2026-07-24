"""Recalcula o backtest walk-forward V28 a partir das previsões OOS congeladas."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'backtest'/'V28_OOS_PREDICTIONS.csv.gz'
OUT=ROOT/'backtest'/'V28_RECALCULADO.csv'

def select_portfolio(frame: pd.DataFrame, target: int=4) -> pd.DataFrame:
    data=frame.copy()
    data['EffectiveOdd']=data['BestOdd']*0.98
    data['EV']=data['Pred']*data['EffectiveOdd']-1
    data=data[data['EffectiveOdd'].between(1.20,3.00)&data['EV'].ge(0)].copy()
    data=data.sort_values(['MatchID','EV'],ascending=[True,False]).drop_duplicates('MatchID')
    selected=(data.sort_values(['WeekID','EV'],ascending=[True,False])
              .groupby('WeekID',group_keys=False).head(target)
              .sort_values(['Date','MatchID']).copy())
    selected['Profit']=np.where(selected['Win'].eq(1),selected['EffectiveOdd']-1,-1)
    return selected

def main() -> None:
    frame=pd.read_csv(SOURCE,low_memory=False)
    selected=select_portfolio(frame)
    selected.to_csv(OUT,index=False)
    equity=selected['Profit'].cumsum()
    drawdown=(equity.cummax().clip(lower=0)-equity).max()
    print(f"Entradas: {len(selected)}")
    print(f"Semanas: {selected['WeekID'].nunique()}")
    print(f"Média/semana: {selected.groupby('WeekID').size().mean():.4f}")
    print(f"Acerto: {selected['Win'].mean():.4%}")
    print(f"Lucro: {selected['Profit'].sum():.4f} unidades")
    print(f"ROI: {selected['Profit'].mean():.4%}")
    print(f"Drawdown máximo: {drawdown:.4f} unidades")
    print(selected.groupby('Season').agg(Entradas=('Win','size'),Acerto=('Win','mean'),Lucro=('Profit','sum'),ROI=('Profit','mean')))

if __name__=='__main__':
    main()
