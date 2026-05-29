import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
import io

st.set_page_config(page_title="Motor PRO 2.12", layout="wide")

LIGAS = {
    "Brasileirão Série A": "https://www.football-data.co.uk/new/BRA.csv",
    "Premier League": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "La Liga": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Série A Itália": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D1.csv"
}

@st.cache_data(ttl=3600)
def extrair_dados(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(response.text))
        df = df.rename(columns={'HomeTeam': 'Home', 'AwayTeam': 'Away', 'FTHG': 'HG', 'FTAG': 'AG'})
        df = df.dropna(subset=['Home', 'Away', 'HG', 'AG']).tail(1500).copy()
        df['Peso'] = np.exp(np.linspace(-1.2, 0, len(df)))
        return df
    except: return pd.DataFrame()

def calcular_power_rating(df, t_casa, t_fora):
    media_gf_c = np.average(df['HG'], weights=df['Peso'])
    media_gf_f = np.average(df['AG'], weights=df['Peso'])
    df_c, df_f = df[df['Home'] == t_casa], df[df['Away'] == t_fora]
    amostra = len(df_c) + len(df_f)
    
    gf_m = np.average(df_c['HG'], weights=df_c['Peso']) if len(df_c) > 0 else media_gf_c
    gs_m = np.average(df_c['AG'], weights=df_c['Peso']) if len(df_c) > 0 else media_gf_f
    gf_v = np.average(df_f['AG'], weights=df_f['Peso']) if len(df_f) > 0 else media_gf_f
    gs_v = np.average(df_f['HG'], weights=df_f['Peso']) if len(df_f) > 0 else media_gf_c

    xg_c = (gf_m / media_gf_c) * (gs_v / media_gf_f) * media_gf_c
    xg_f = (gf_v / media_gf_f) * (gs_m / media_gf_c) * media_gf_f
    return xg_c, xg_f, amostra

# ==========================================
# INTERFACE
# ==========================================
st.title("🚀 Motor Quantitativo PRO 2.12")
liga_sel = st.sidebar.selectbox("Liga", list(LIGAS.keys()))
banca_total = st.sidebar.number_input("Banca Total (R$)", value=0.0, step=100.0)
df = extrair_dados(LIGAS[liga_sel])

if not df.empty:
    times = sorted(df['Home'].unique())
    c1, c2 = st.columns(2)
    t_casa = c1.selectbox("🏠 Mandante", times)
    t_fora = c2.selectbox("✈️ Visitante", times)

    st.sidebar.subheader("Odds da Corretora")
    odds = {
        "Casa": float(st.sidebar.text_input("Vitória Casa", "2.00").replace(',', '.')),
        "Empate": float(st.sidebar.text_input("Empate", "3.30").replace(',', '.')),
        "Fora": float(st.sidebar.text_input("Vitória Fora", "3.80").replace(',', '.')),
        "Casa ou Empate": float(st.sidebar.text_input("Casa ou Empate", "1.25").replace(',', '.')),
        "Fora ou Empate": float(st.sidebar.text_input("Fora ou Empate", "1.80").replace(',', '.')),
        "Casa ou Anula": float(st.sidebar.text_input("Casa ou Anula", "1.45").replace(',', '.')),
        "Fora ou Anula": float(st.sidebar.text_input("Fora ou Anula", "2.70").replace(',', '.')),
        "Mais de 2.5 gols": float(st.sidebar.text_input("Mais de 2.5 gols", "1.90").replace(',', '.')),
        "Ambos marcam": float(st.sidebar.text_input("Ambos marcam", "1.85").replace(',', '.'))
    }

    if st.button("CALCULAR MOTOR"):
        xg_c, xg_f, amostra = calcular_power_rating(df, t_casa, t_fora)
        confianca = min(100, (amostra / 38) * 100)
        
        if confianca <= 50: st.markdown(f"# 🔴 CONFIANÇA: {confianca:.0f}%")
        elif confianca <= 85: st.markdown(f"# 🟡 CONFIANÇA: {confianca:.0f}%")
        else: st.markdown(f"# 🟢 CONFIANÇA: {confianca:.0f}%")

        p_c = [poisson.pmf(i, xg_c) for i in range(11)]
        p_f = [poisson.pmf(i, xg_f) for i in range(11)]
        
        prob = {
            "Casa": sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i > j),
            "Empate": sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i == j),
            "Fora": sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i < j)
        }
        prob["Casa ou Empate"] = prob["Casa"] + prob["Empate"]
        prob["Fora ou Empate"] = prob["Fora"] + prob["Empate"]
        prob["Casa ou Anula"] = prob["Casa"] / (prob["Casa"] + prob["Fora"]) if (prob["Casa"] + prob["Fora"]) > 0 else 0
        prob["Fora ou Anula"] = prob["Fora"] / (prob["Casa"] + prob["Fora"]) if (prob["Casa"] + prob["Fora"]) > 0 else 0
        prob["Mais de 2.5 gols"] = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i + j > 2.5)
        prob["Ambos marcam"] = (1 - p_c[0]) * (1 - p_f[0])

        apostar, nao_apostar = [], []

        for merc, p in prob.items():
            odd_b = odds[merc]
            margem = (p * odd_b) - 1
            
            # Lógica da Stake Condicional
            if banca_total > 0:
                valor_stake = banca_total * 0.04
                msg_stake = f"| APOSTAR 4% (R$ {valor_stake:.2f})"
            else:
                msg_stake = "| APOSTAR 4%"
            
            if margem >= 0.10 and confianca > 50:
                apostar.append(f"✅ **{merc}** ({p*100:.1f}% chance) {msg_stake}")
            else:
                nao_apostar.append(f"❌ **{merc}** (EV: {margem*100:.1f}%)")

        st.markdown("---")
        st.subheader("📋 Resumo Executivo")
        if apostar: st.success("SUGESTÕES DE OPERAÇÃO:\n\n" + "\n\n".join(apostar))
        if nao_apostar: st.warning("NÃO OPERAR (Risco elevado ou sem valor): \n\n" + "\n\n".join(nao_apostar))
