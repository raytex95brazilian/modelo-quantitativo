import streamlit as st
import pandas as pd
from scipy.stats import poisson

# Configuração da Página
st.set_page_config(page_title="Sistema Quantitativo", layout="wide")

# ==========================================
# 1. MOTOR (CÁLCULOS E EXTRAÇÃO)
# ==========================================
LIGAS = {
    "Brasileirão Série A": "https://www.football-data.co.uk/new/BRA.csv",
    "Premier League (Inglaterra)": "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
    "La Liga (Espanha)": "https://www.football-data.co.uk/mmz4281/2425/SP1.csv",
    "Bundesliga (Alemanha)": "https://www.football-data.co.uk/mmz4281/2425/D1.csv",
    "Serie A (Itália)": "https://www.football-data.co.uk/mmz4281/2425/I1.csv",
    "Ligue 1 (França)": "https://www.football-data.co.uk/mmz4281/2425/F1.csv",
    "J-League (Japão)": "https://www.football-data.co.uk/new/JPN.csv",
    "Primeira Liga (Portugal)": "https://www.football-data.co.uk/mmz4281/2425/P1.csv"
}

@st.cache_data
def extrair_dados(url):
    df = pd.read_csv(url)
    
    # TRADUTOR DE COLUNAS: Padroniza o modelo europeu para o nosso sistema
    traducao = {
        'HomeTeam': 'Home',
        'AwayTeam': 'Away',
        'FTHG': 'HG',
        'FTAG': 'AG'
    }
    df = df.rename(columns=traducao)
    
    if 'Season' in df.columns:
        df = df[df['Season'] == df['Season'].max()]
    if not ('HC' in df.columns and 'AC' in df.columns):
        df['HC'], df['AC'] = 0.0, 0.0
        
    return df.dropna(subset=['Home', 'Away', 'HG', 'AG'])

def calcular_power_rating(df, t_casa, t_fora):
    # =================================================================
    # MOTOR PURISTA DE POISSON (CÁLCULO ESTRITO CASA vs FORA)
    # =================================================================

    # 1. Médias Globais da Liga
    media_gols_feitos_em_casa = df['HG'].mean()
    media_gols_feitos_fora = df['AG'].mean()
    # Pela simetria do jogo, gols sofridos em casa é a média de gols feitos fora, e vice-versa
    media_gols_sofridos_em_casa = media_gols_feitos_fora  
    media_gols_sofridos_fora = media_gols_feitos_em_casa

    # 2. Desempenho Estrito do Mandante (APENAS JOGANDO EM CASA)
    df_casa = df[df['Home'] == t_casa]
    if not df_casa.empty:
        gols_feitos_mandante = df_casa['HG'].mean()
        gols_sofridos_mandante = df_casa['AG'].mean()
    else:
        # Fallback de segurança se não houver dados (início de temporada)
        gols_feitos_mandante = media_gols_feitos_em_casa
        gols_sofridos_mandante = media_gols_sofridos_em_casa

    # 3. Desempenho Estrito do Visitante (APENAS JOGANDO FORA)
    df_fora = df[df['Away'] == t_fora]
    if not df_fora.empty:
        gols_feitos_visitante = df_fora['AG'].mean()
        gols_sofridos_visitante = df_fora['HG'].mean()
    else:
        # Fallback de segurança
        gols_feitos_visitante = media_gols_feitos_fora
        gols_sofridos_visitante = media_gols_sofridos_fora

    # 4. Cálculo das Forças Isoladas
    forca_atq_casa = gols_feitos_mandante / media_gols_feitos_em_casa
    forca_def_casa = gols_sofridos_mandante / media_gols_sofridos_em_casa

    forca_atq_fora = gols_feitos_visitante / media_gols_feitos_fora
    forca_def_fora = gols_sofridos_visitante / media_gols_sofridos_fora

    # 5. Expectativa de Gols (xG) Final
    xg_c = forca_atq_casa * forca_def_fora * media_gols_feitos_em_casa
    xg_f = forca_atq_fora * forca_def_casa * media_gols_feitos_fora

    return xg_c, xg_f

def calcular_probabilidades(xg_c, xg_f):
    p_c = [poisson.pmf(i, xg_c) for i in range(6)]
    p_f = [poisson.pmf(i, xg_f) for i in range(6)]
    
    m = {"H": 0, "D": 0, "A": 0, "O25": 0, "O35": 0, "BTTS_S": 0}
    for i in range(6):
        for j in range(6):
            p = p_c[i] * p_f[j]
            if i > j: m["H"] += p
            elif i == j: m["D"] += p
            else: m["A"] += p
            if i + j > 2.5: m["O25"] += p
            if i + j > 3.5: m["O35"] += p
            if i > 0 and j > 0: m["BTTS_S"] += p
    return m

def acao_kelly(prob, odd_b):
    if odd_b <= 1: return 0, "Sem cotação"
    margem = (prob * odd_b) - 1
    stake = max(0, margem / (odd_b - 1)) * 100
    if margem > 0.02 and stake > 0.1:
        return margem
