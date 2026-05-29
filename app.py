import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
import io

# Configuração da Página
st.set_page_config(page_title="Sistema Quantitativo PRO 2.0", layout="wide")

# ==========================================
# 1. MOTOR (CÁLCULOS E EXTRAÇÃO PRO 2.0)
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

@st.cache_data(ttl=3600)
def extrair_dados(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/csv',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200 or "<html" in response.text[:50].lower():
            st.error("⚠️ O servidor da liga bloqueou o acesso temporariamente.")
            return pd.DataFrame()

        csv_data = io.StringIO(response.text)
        df = pd.read_csv(csv_data)
        
        traducao = {'HomeTeam': 'Home', 'AwayTeam': 'Away', 'FTHG': 'HG', 'FTAG': 'AG'}
        df = df.rename(columns=traducao)
        
        if not all(col in df.columns for col in ['Home', 'Away', 'HG', 'AG']):
            st.error("⚠️ Os dados baixados vieram corrompidos.")
            return pd.DataFrame()
            
        df = df.dropna(subset=['Home', 'Away', 'HG', 'AG'])
        df = df.tail(380).copy() # Janela Deslizante
        
        # O MOTOR 2.0: DECAIMENTO EXPONENCIAL
        # Jogos antigos perdem peso matemático. A fase atual domina o cálculo.
        df['Peso'] = np.exp(np.linspace(-1.5, 0, len(df)))
        
        return df

    except Exception as e:
        st.error(f"⚠️ Falha na conexão: {e}")
        return pd.DataFrame()

def calcular_power_rating(df, t_casa, t_fora):
    # Cálculo usando Média Ponderada (Foco no momento atual)
    media_gols_feitos_em_casa = np.average(df['HG'], weights=df['Peso'])
    media_gols_feitos_fora = np.average(df['AG'], weights=df['Peso'])
    media_gols_sofridos_em_casa = media_gols_feitos_fora  
    media_gols_sofridos_fora = media_gols_feitos_em_casa

    df_casa = df[df['Home'] == t_casa]
    jogos_c = len(df_casa)
    if jogos_c > 0:
        gols_feitos_mandante = np.average(df_casa['HG'], weights=df_casa['Peso'])
        gols_sofridos_mandante = np.average(df_casa['AG'], weights=df_casa['Peso'])
    else:
        gols_feitos_mandante = media_gols_feitos_em_casa
        gols_sofridos_mandante = media_gols_sofridos_em_casa

    df_fora = df[df['Away'] == t_fora]
    jogos_f = len(df_fora)
    if jogos_f > 0:
        gols_feitos_visitante = np.average(df_fora['AG'], weights=df_fora['Peso'])
        gols_sofridos_visitante = np.average(df_fora['HG'], weights=df_fora['Peso'])
    else:
        gols_feitos_visitante = media_gols_feitos_fora
        gols_sofridos_visitante = media_gols_sofridos_fora

    forca_atq_casa = gols_feitos_mandante / media_gols_feitos_em_casa
    forca_def_casa = gols_sofridos_mandante / media_gols_sofridos_em_casa
    forca_atq_fora = gols_feitos_visitante / media_gols_feitos_fora
    forca_def_fora = gols_sofridos_visitante / media_gols_sofridos_em_casa

    xg_c = forca_atq_casa * forca_def_fora * media_gols_feitos_em_casa
    xg_f = forca_atq_fora * forca_def_casa * media_gols_feitos_fora

    return xg_c, xg_f, jogos_c, jogos_f

def calcular_probabilidades(xg_c, xg_f):
    # O MOTOR 2.0: EXPANSÃO DE MATRIZ DE 0 A 10 GOLS
    p_c = [poisson.pmf(i, xg_c) for i in range(11)]
    p_f = [poisson.pmf(i, xg_f) for i in range(11)]
    
    m = {"H": 0, "D": 0, "A": 0, "O25": 0, "O35": 0, "BTTS_S": 0}
    for i in range(11):
        for j in range(11):
            p = p_c[i] * p_f[j]
            if i > j: m["H"] += p
            elif i == j: m["D"] += p
            else: m["A"] += p
            if i + j > 2.5: m["O25"] += p
            if i + j > 3.5: m["O35"] += p
            if i > 0 and j > 0: m["BTTS_S"] += p
            
    m["1X"] = m["H"] + m["D"]
    m["X2"] = m["A"] + m["D"]
    soma_vitorias = m["H"] + m["A"]
    m["DNB_H"] = m["H"] / soma_vitorias if soma_vitorias > 0 else 0
    m["DNB_A"] = m["A"] / soma_vitorias if soma_vitorias > 0 else 0
    
    return m

def acao_kelly(prob, odd_b):
    if odd_b <= 1: return 0, "Sem cotação"
    margem = (prob * odd_b) - 1
    stake = max(0, margem / (odd_b - 1)) * 100
    
    # GUILHOTINA INSTITUCIONAL: Aceita APENAS vantagens >= 10%.
    # Limite MÁXIMO visual de 3% da banca para proteção de capital.
    stake_sugerida = min(stake, 3.00)
    
    if margem >= 0.10 and stake > 0.1:
        return margem * 100, f"✅ APOSTAR: {stake_sugerida:.2f}% DA BANCA"
    return margem * 100, "❌ NÃO APOSTAR"

# ==========================================
# 2. INTERFACE VISUAL (FRONT-END)
# ==========================================
st.title("📈 Motor Quantitativo PRO 2.0")
st.markdown("*Ajustado com Decaimento Exponencial e Matriz Expandida*")
st.markdown("---")

st.sidebar.header("⚙️ Configuração do Jogo")
liga_selecionada = st.sidebar.selectbox("Escolha a Liga", list(LIGAS.keys()))

df = extrair_dados(LIGAS[liga_selecionada])

if df.empty:
    st.warning("Aguardando conexão. Tente novamente.")
else:
    times = sorted(df['Home'].unique())

    c1, c2 = st.columns(2)
    with c1: t_casa = st.selectbox("🏠 Time Mandante", times)
    with c2: t_fora = st.selectbox("✈️ Time Visitante", times)

    st.sidebar.markdown("---")
    st.sidebar.header("📊 Odds da Banca")

    def ler_odd(label):
        valor = st.sidebar.text_input(label, value="1.00")
        try: return float(valor.replace(',', '.'))
        except: return 1.00

    odd_h = ler_odd("Vitória Casa (1)")
    odd_d = ler_odd("Empate (X)")
    odd_a = ler_odd("Vitória Fora (2)")
    odd_1x = ler_odd("Casa ou Empate (1X)")
    odd_x2 = ler_odd("Fora ou Empate (X2)")
    odd_dnb_h = ler_odd("Empate Anula Casa (DNB 1)")
    odd_dnb_a = ler_odd("Empate Anula Fora (DNB 2)")
    odd_o25 = ler_odd("Over 2.5")
    odd_btts = ler_odd("Ambas Marcam (Sim)")

    if st.button("🚀 EXECUTAR ORDEM", use_container_width=True):
        if t_casa == t_fora:
            st.error("Selecione times diferentes.")
        else:
            xg_c, xg_f, jogos_c, jogos_f = calcular_power_rating(df, t_casa, t_fora)
            probs = calcular_probabilidades(xg_c, xg_f)
            
            amostra_total = jogos_c + jogos_f
            confiabilidade = min(100.0, (amostra_total / 38.0) * 100)
            
            st.markdown("### 🎯 Expectativa de Gols Ponderada e Confiabilidade")
            col_x1, col_x2, col_x3 = st.columns(3)
            col_x1.metric(label=f"xG Ajustado {t_casa}", value=f"{xg_c:.2f}")
            col_x2.metric(label=f"xG Ajustado {t_fora}", value=f"{xg_f:.2f}")
            
            status_conf = "Alta 🟢" if confiabilidade >= 70 else "Descartado 🔴"
            col_x3.metric(label="Estabilidade do Time", value=f"{confiabilidade:.1f}%", delta=status_conf, delta_color="off")
            
            if confiabilidade < 70:
                st.error("⚠️ ALERTA DE RISCO: Amostra insuficiente. A ordem técnica é NÃO OPERAR neste jogo.")
            
            st.markdown("### 💼 Matriz de Execução (Guilhotina 10%)")
            mercados = [
                ("Vitória Casa", probs['H'], odd_h),
                ("Empate", probs['D'], odd_d),
                ("Vitória Fora", probs['A'], odd_a),
                ("Casa ou Empate (1X)", probs['1X'], odd_1x),
                ("Fora ou Empate (X2)", probs['X2'], odd_x2),
                ("Empate Anula Casa (DNB)", probs['DNB_H'], odd_dnb_h),
                ("Empate Anula Fora (DNB)", probs['DNB_A'], odd_dnb_a),
                ("Over 2.5", probs['O25'], odd_o25),
                ("Ambas Marcam", probs['BTTS_S'], odd_btts)
            ]
            
            for nome, p, odd_b in mercados:
                if p > 0:
                    odd_j = 1/p
                    with st.expander(f"{nome} - Probabilidade: {p*100:.1f}% | Odd Justa: {odd_j:.2f}", expanded=True):
                        if odd_b > 1.0:
                            margem, acao = acao_kelly(p, odd_b)
                            st.write(f"**Cotação da Banca:** {odd_b:.2f} | **Valor Esperado (+EV):** {margem:+.2f}%")
                            if "APOSTAR" in acao and confiabilidade >= 70: 
                                st.success(acao)
                            else: 
                                st.error("❌ NÃO APOSTAR")
                        else:
                            st.warning("Insira a Odd para auditar.")
