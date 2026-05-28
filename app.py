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
    if 'Season' in df.columns:
        df = df[df['Season'] == df['Season'].max()]
    if not ('HC' in df.columns and 'AC' in df.columns):
        df['HC'], df['AC'] = 0.0, 0.0
    return df.dropna(subset=['Home', 'Away', 'HG', 'AG'])

def calcular_power_rating(df, t_casa, t_fora):
    m_hg, m_ag = df['HG'].mean(), df['AG'].mean()
    j_c, j_f = df[df['Home'] == t_casa], df[df['Away'] == t_fora]
    
    atq_c = j_c['HG'].mean() / m_hg
    def_f = j_f['HG'].mean() / m_hg
    atq_f = j_f['AG'].mean() / m_ag
    def_c = j_c['AG'].mean() / m_ag
    
    return atq_c * def_f * m_hg, atq_f * def_c * m_ag

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
        return margem * 100, f"✅ APOSTAR: {stake:.2f}% DA BANCA"
    return margem * 100, "❌ NÃO APOSTAR"

# ==========================================
# 2. INTERFACE VISUAL (FRONT-END)
# ==========================================
st.title("📈 Motor Quantitativo de Alavancagem")
st.markdown("---")

st.sidebar.header("⚙️ Configuração do Jogo")
liga_selecionada = st.sidebar.selectbox("Escolha a Liga", list(LIGAS.keys()))

df = extrair_dados(LIGAS[liga_selecionada])
times = sorted(df['Home'].unique())

c1, c2 = st.columns(2)
with c1: t_casa = st.selectbox("🏠 Time Mandante", times)
with c2: t_fora = st.selectbox("✈️ Time Visitante", times)

st.sidebar.markdown("---")
st.sidebar.header("📊 Odds da Banca (Opcional)")

def ler_odd(label):
    valor = st.sidebar.text_input(label, value="1.00")
    try:
        return float(valor.replace(',', '.'))
    except:
        return 1.00

odd_h = ler_odd("Vitória Casa (1)")
odd_d = ler_odd("Empate (X)")
odd_a = ler_odd("Vitória Fora (2)")
odd_o25 = ler_odd("Over 2.5")
odd_btts = ler_odd("Ambas Marcam (Sim)")

if st.button("🚀 EXECUTAR ANÁLISE", use_container_width=True):
    if t_casa == t_fora:
        st.error("Selecione times diferentes para análise.")
    else:
        xg_c, xg_f = calcular_power_rating(df, t_casa, t_fora)
        probs = calcular_probabilidades(xg_c, xg_f)
        
        st.markdown("### 🎯 Expectativa de Gols (xG)")
        col_x1, col_x2 = st.columns(2)
        col_x1.metric(label=f"xG {t_casa}", value=f"{xg_c:.2f}")
        col_x2.metric(label=f"xG {t_fora}", value=f"{xg_f:.2f}")
        
        st.markdown("### 💼 Veredito dos Mercados")
        mercados = [
            ("Vitória Casa", probs['H'], odd_h),
            ("Empate", probs['D'], odd_d),
            ("Vitória Fora", probs['A'], odd_a),
            ("Over 2.5", probs['O25'], odd_o25),
            ("Ambas Marcam", probs['BTTS_S'], odd_btts)
        ]
        
        for nome, p, odd_b in mercados:
            odd_j = 1/p
            with st.expander(f"{nome} - Probabilidade: {p*100:.1f}% | Odd Justa: {odd_j:.2f}", expanded=True):
                if odd_b > 1.0:
                    margem, acao = acao_kelly(p, odd_b)
                    st.write(f"**Cotação da Banca:** {odd_b:.2f} | **Valor Esperado (+EV):** {margem:+.2f}%")
                    if "APOSTAR" in acao: st.success(acao)
                    else: st.error(acao)
                else:
                    st.warning("Insira a Odd da banca no menu lateral para calcular a Stake.")