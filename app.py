import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
import io

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Motor TEX STATISTICS PRO 2.15", layout="wide")

# ==========================================
# BANCOS DE DADOS E API
# ==========================================
LIGAS_CSV = {
    "Brasileirão Série A": "https://www.football-data.co.uk/new/BRA.csv",
    "Argentina - Primera Division": "https://www.football-data.co.uk/new/ARG.csv",
    "EUA - MLS": "https://www.football-data.co.uk/new/USA.csv",
    "México - Liga MX": "https://www.football-data.co.uk/new/MEX.csv",
    "Japão - J1 League": "https://www.football-data.co.uk/new/JPN.csv",
    "China - Super League": "https://www.football-data.co.uk/new/CHN.csv",
    "Suécia - Allsvenskan": "https://www.football-data.co.uk/new/SWE.csv",
    "Noruega - Eliteserien": "https://www.football-data.co.uk/new/NOR.csv",
    "Finlândia - Veikkausliiga": "https://www.football-data.co.uk/new/FIN.csv",
    "Irlanda - Premier Division": "https://www.football-data.co.uk/new/IRL.csv",
    "Inglaterra - Premier League": "https://www.football-data.co.uk/mmz4281/2526/E0.csv",
    "Inglaterra - Championship": "https://www.football-data.co.uk/mmz4281/2526/E1.csv",
    "Espanha - La Liga": "https://www.football-data.co.uk/mmz4281/2526/SP1.csv",
    "Espanha - Segunda Divisão": "https://www.football-data.co.uk/mmz4281/2526/SP2.csv",
    "Itália - Série A": "https://www.football-data.co.uk/mmz4281/2526/I1.csv",
    "Itália - Série B": "https://www.football-data.co.uk/mmz4281/2526/I2.csv",
    "Alemanha - Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D1.csv",
    "Alemanha - 2. Bundesliga": "https://www.football-data.co.uk/mmz4281/2526/D2.csv",
    "França - Ligue 1": "https://www.football-data.co.uk/mmz4281/2526/F1.csv",
    "Portugal - Primeira Liga": "https://www.football-data.co.uk/mmz4281/2526/P1.csv",
    "Holanda - Eredivisie": "https://www.football-data.co.uk/mmz4281/2526/N1.csv",
    "Bélgica - Pro League": "https://www.football-data.co.uk/mmz4281/2526/B1.csv",
    "Turquia - Super Lig": "https://www.football-data.co.uk/mmz4281/2526/T1.csv",
    "Grécia - Super League": "https://www.football-data.co.uk/mmz4281/2526/G1.csv"
}

LIGAS_API = {
    "Brasileirão Série A": "soccer_brazil_campeonato",
    "Argentina - Primera Division": "soccer_argentina_primera_division",
    "EUA - MLS": "soccer_usa_mls",
    "México - Liga MX": "soccer_mexico_ligamx",
    "Japão - J1 League": "soccer_japan_j_league",
    "China - Super League": "soccer_china_superleague",
    "Suécia - Allsvenskan": "soccer_sweden_allsvenskan",
    "Noruega - Eliteserien": "soccer_norway_eliteserien",
    "Finlândia - Veikkausliiga": "soccer_finland_veikkausliiga",
    "Irlanda - Premier Division": "soccer_ireland_premier_division",
    "Inglaterra - Premier League": "soccer_epl",
    "Inglaterra - Championship": "soccer_efl_champ",
    "Espanha - La Liga": "soccer_spain_la_liga",
    "Espanha - Segunda Divisão": "soccer_spain_segunda_division",
    "Itália - Série A": "soccer_italy_serie_a",
    "Itália - Série B": "soccer_italy_serie_b",
    "Alemanha - Bundesliga": "soccer_germany_bundesliga",
    "Alemanha - 2. Bundesliga": "soccer_germany_bundesliga2",
    "França - Ligue 1": "soccer_france_ligue_one",
    "Portugal - Primeira Liga": "soccer_portugal_primeira_liga",
    "Holanda - Eredivisie": "soccer_netherlands_eredivisie",
    "Bélgica - Pro League": "soccer_belgium_first_div",
    "Turquia - Super Lig": "soccer_turkey_super_league",
    "Grécia - Super League": "soccer_greece_super_league"
}

# ==========================================
# FUNÇÕES CORE
# ==========================================
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

@st.cache_data(ttl=10800)
def extrair_odds_api(api_key, sport_key):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h,totals,btts&oddsFormat=decimal"
        response = requests.get(url, timeout=15)
        if response.status_code == 200: return response.json()
        return []
    except: return []

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

def ler_odd(label):
    val = st.sidebar.text_input(label, value="", key=f"manual_{label}")
    if not val: return 1.00
    try: return float(val.replace(',', '.'))
    except: return 1.00

# ==========================================
# ESTRUTURA VISUAL E INTERRUPTOR
# ==========================================
st.sidebar.markdown("## 🎛️ Painel de Controlo Mestre")
modo_operacao = st.sidebar.radio("Selecione o Ambiente de Execução:", ["Modo Manual (Laboratório)", "Modo FULL AUTO (Institucional)"])
st.sidebar.markdown("---")

st.title(f"🚀 Motor TEX STATISTICS PRO 2.15")
st.markdown(f"**Status de Operação:** `{modo_operacao}`")

liga_sel = st.sidebar.selectbox("Liga Operacional", list(LIGAS_CSV.keys()))
banca_total = st.sidebar.number_input("Banca Total (R$)", value=0.0, step=100.0)

df = extrair_dados(LIGAS_CSV[liga_sel])

if not df.empty:
    times_csv = sorted(df['Home'].unique())

    # ==========================================
    # LÓGICA MODO MANUAL
    # ==========================================
    if modo_operacao == "Modo Manual (Laboratório)":
        c1, c2 = st.columns(2)
        t_casa = c1.selectbox("🏠 Mandante", times_csv, key="sel_casa_manual")
        t_fora = c2.selectbox("✈️ Visitante", times_csv, key="sel_fora_manual")

        st.sidebar.subheader("Odds da Corretora (Digitação)")
        odds = {
            "Vitória Casa": ler_odd("Vitória Casa"),
            "Empate": ler_odd("Empate"),
            "Vitória Fora": ler_odd("Vitória Fora"),
            "Casa ou Empate": ler_odd("Casa ou Empate"),
            "Fora ou Empate": ler_odd("Fora ou Empate"),
            "Empate Anula Casa": ler_odd("Empate Anula Casa"),
            "Empate Anula Fora": ler_odd("Empate Anula Fora"),
            "Mais de 2.5 gols": ler_odd("Mais de 2.5 gols"),
            "Ambos marcam": ler_odd("Ambos marcam")
        }

        pronto_para_calcular = st.button("CALCULAR MOTOR MANUAL")

    # ==========================================
    # LÓGICA MODO AUTOMÁTICO
    # ==========================================
    else:
        st.sidebar.subheader("Conexão Global API")
        api_key = st.sidebar.text_input("Chave The-Odds-API", type="password")
        
        if not api_key:
            st.warning("👈 Insira a sua chave da The-Odds-API no menu lateral para ativar a varredura global.")
            st.stop()
            
        dados_api = extrair_odds_api(api_key, LIGAS_API[liga_sel])
        
        if dados_api:
            jogos_disponiveis = {f"{j['home_team']} vs {j['away_team']}": j for j in dados_api}
            jogo_sel = st.selectbox("🎯 Selecione a Partida (Radar Mundial)", list(jogos_disponiveis.keys()))
            jogo_dados = jogos_disponiveis[jogo_sel]

            odd_H, odd_D, odd_A, odd_O25, odd_BTTS = 1.01, 1.01, 1.01, 1.01, 1.01
            for bookmaker in jogo_dados.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == jogo_dados['home_team']: odd_H = max(odd_H, outcome['price'])
                            elif outcome['name'] == 'Draw': odd_D = max(odd_D, outcome['price'])
                            elif outcome['name'] == jogo_dados['away_team']: odd_A = max(odd_A, outcome['price'])
                    elif market['key'] == 'totals':
                        for outcome in market['outcomes']:
                            if outcome['name'] == 'Over' and outcome.get('point') == 2.5: odd_O25 = max(odd_O25, outcome['price'])
                    elif market['key'] == 'btts':
                        for outcome in market['outcomes']:
                            if outcome['name'] == 'Yes': odd_BTTS = max(odd_BTTS, outcome['price'])

            odd_1X = 1 / ((1 / odd_H) + (1 / odd_D)) if odd_H > 1.01 and odd_D > 1.01 else 1.01
            odd_X2 = 1 / ((1 / odd_A) + (1 / odd_D)) if odd_A > 1.01 and odd_D > 1.01 else 1.01
            odd_DNB_H = odd_H * (1 - (1 / odd_D)) if odd_H > 1.01 and odd_D > 1.01 else 1.01
            odd_DNB_A = odd_A * (1 - (1 / odd_D)) if odd_A > 1.01 and odd_D > 1.01 else 1.01

            st.info("📡 Line Shopping concluído: Cotações maximizadas em memória.")

            st.markdown("### 🔄 Calibrar Nomes do Banco de Dados")
            c1, c2 = st.columns(2)
            guess_h = next((t for t in times_csv if str(jogo_dados['home_team'])[:4] in t), times_csv[0])
            guess_a = next((t for t in times_csv if str(jogo_dados['away_team'])[:4] in t), times_csv[1])
            t_casa = c1.selectbox("🏠 Mandante (CSV)", times_csv, index=times_csv.index(guess_h) if guess_h in times_csv else 0, key="sel_casa_auto")
            t_fora = c2.selectbox("✈️ Visitante (CSV)", times_csv, index=times_csv.index(guess_a) if guess_a in times_csv else 1, key="sel_fora_auto")

            odds = {
                "Vitória Casa": odd_H,
                "Empate": odd_D,
                "Vitória Fora": odd_A,
                "Casa ou Empate": odd_1X,
                "Fora ou Empate": odd_X2,
                "Empate Anula Casa": odd_DNB_H,
                "Empate Anula Fora": odd_DNB_A,
                "Mais de 2.5 gols": odd_O25,
                "Ambos marcam": odd_BTTS
            }

            pronto_para_calcular = st.button("CALCULAR MOTOR AUTOMATIZADO")
        else:
            st.warning("Nenhuma partida encontrada na API para esta liga neste exato momento.")
            pronto_para_calcular = False

    # ==========================================
    # MOTOR DE CÁLCULO E RENDERIZAÇÃO (COMUM AOS DOIS)
    # ==========================================
    if pronto_para_calcular:
        xg_c, xg_f, amostra = calcular_power_rating(df, t_casa, t_fora)
        confianca = min(100, (amostra / 38) * 100)
        
        if confianca <= 50: st.markdown(f"# 🔴 CONFIANÇA: {confianca:.0f}%")
        elif confianca <= 85: st.markdown(f"# 🟡 CONFIANÇA: {confianca:.0f}%")
        else: st.markdown(f"# 🟢 CONFIANÇA: {confianca:.0f}%")

        p_c = [poisson.pmf(i, xg_c) for i in range(11)]
        p_f = [poisson.pmf(i, xg_f) for i in range(11)]
        
        prob = {
            "Vitória Casa": sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i > j),
            "Empate": sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i == j),
            "Vitória Fora": sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i < j)
        }
        prob["Casa ou Empate"] = prob["Vitória Casa"] + prob["Empate"]
        prob["Fora ou Empate"] = prob["Vitória Fora"] + prob["Empate"]
        prob["Empate Anula Casa"] = prob["Vitória Casa"] / (prob["Vitória Casa"] + prob["Vitória Fora"]) if (prob["Vitória Casa"] + prob["Vitória Fora"]) > 0 else 0
        prob["Empate Anula Fora"] = prob["Vitória Fora"] / (prob["Vitória Casa"] + prob["Vitória Fora"]) if (prob["Vitória Casa"] + prob["Vitória Fora"]) > 0 else 0
        prob["Mais de 2.5 gols"] = sum(p_c[i] * p_f[j] for i in range(11) for j in range(11) if i + j > 2.5)
        prob["Ambos marcam"] = (1 - p_c[0]) * (1 - p_f[0])

        st.subheader(f"📊 Análise Detalhada ({modo_operacao})")
        sugestoes_verde = []
        sugestoes_vermelho = []

        for merc, p in prob.items():
            odd_b = odds.get(merc, 1.00)
            if odd_b <= 1.01 and modo_operacao == "Modo FULL AUTO (Institucional)": continue 
            
            margem = (p * odd_b) - 1
            status = margem >= 0.10 and confianca > 50
            
            prefixo = "✅ APOSTAR" if status else "❌ NÃO APOSTAR"
            
            with st.expander(f"{prefixo} | {merc} ({p*100:.1f}%)"):
                st.write(f"Odd justa da Máquina: **{1/p:.2f}** | Odd do Mercado: **{odd_b:.2f}**")
                st.write(f"Valor Esperado (EV): **{margem*100:+.1f}%**")
            
            stake_txt = f" (4% = R$ {banca_total*0.04:.2f})" if banca_total > 0 else " (4%)"
            
            if status:
                sugestoes_verde.append(f"✅ **{merc}** ({p*100:.1f}% chance){stake_txt}")
            else:
                sugestoes_vermelho.append(f"❌ **{merc}** (EV: {margem*100:+.1f}%)")

        st.markdown("---")
        st.subheader("📋 Resumo Executivo TEX")
        if sugestoes_verde: st.success("SUGESTÕES DE OPERAÇÃO:\n\n" + "\n\n".join(sugestoes_verde))
        if sugestoes_vermelho: st.error("NÃO OPERAR (Risco elevado ou sem valor): \n\n" + "\n\n".join(sugestoes_vermelho))
