import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
import io
import difflib

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Motor TEX STATISTICS PRO 2.15", layout="wide")

# ==========================================
# CHAVE API
# ==========================================
API_KEY = "d9c21f8217e059554c94a263642fc0eb"

# ==========================================
# BANCOS DE DADOS
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

EXCHANGES_BLOQUEADAS = ['smarkets', 'matchbook', 'betfair_ex_uk', 'betfair_ex_au', 'betfair_ex_eu', 'betdaq', 'betfair']

# ==========================================
# FUNÇÕES CORE
# ==========================================
@st.cache_data(ttl=3600)
def extrair_dados(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(response.text))
        
        # Mapeamento inteligente para aceitar tanto formato europeu quanto mundial (EUA, MEX, etc.)
        mapeamento = {}
        if 'HomeTeam' in df.columns: mapeamento['HomeTeam'] = 'Home'
        if 'AwayTeam' in df.columns: mapeamento['AwayTeam'] = 'Away'
        if 'FTHG' in df.columns: mapeamento['FTHG'] = 'HG'
        if 'FTAG' in df.columns: mapeamento['FTAG'] = 'AG'
        
        if mapeamento:
            df = df.rename(columns=mapeamento)
            
        colunas_necessarias = ['Home', 'Away', 'HG', 'AG']
        if not all(col in df.columns for col in colunas_necessarias):
            return pd.DataFrame()
            
        df = df.dropna(subset=colunas_necessarias).tail(800).copy()
        df['Peso'] = np.exp(np.linspace(-2.0, 0, len(df)))
        return df
    except Exception as e:
        return pd.DataFrame()

def extrair_odds_api(api_key, sport_key):
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={api_key}&regions=eu,uk,us&markets=h2h,totals&oddsFormat=decimal"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        else:
            # Exibe o erro real vindo do servidor para diagnóstico imediato
            st.error(f"❌ Erro Detalhado da API: Código {response.status_code}")
            st.error(f"Mensagem do servidor: {response.text}")
            return []
    except Exception as e:
        st.error(f"❌ Erro de rede/Internet: {e}")
        return []

def encontrar_melhor_match(nome_api, lista_csv):
    nome_api = nome_api.lower().replace("fc", "").replace("rj", "").strip()
    matches = difflib.get_close_matches(nome_api, [x.lower() for x in lista_csv], n=1, cutoff=0.5)
    if matches:
        return next(t for t in lista_csv if t.lower() == matches[0])
    return None

def calcular_power_rating(df, t_casa, t_fora):
    media_gf_c = np.average(df['HG'], weights=df['Peso'])
    media_gf_f = np.average(df['AG'], weights=df['Peso'])
    
    df_c = df[df['Home'] == t_casa].copy()
    df_f = df[df['Away'] == t_fora].copy()
    
    min_jogos = 6
    peso_reg = 0.48
    
    gf_m = np.average(df_c['HG'], weights=df_c['Peso']) if len(df_c) >= min_jogos else media_gf_c
    gs_m = np.average(df_c['AG'], weights=df_c['Peso']) if len(df_c) >= min_jogos else media_gf_f
    gf_v = np.average(df_f['AG'], weights=df_f['Peso']) if len(df_f) >= min_jogos else media_gf_f
    gs_v = np.average(df_f['HG'], weights=df_f['Peso']) if len(df_f) >= min_jogos else media_gf_c
    
    gf_m = gf_m * (1 - peso_reg) + media_gf_c * peso_reg
    gs_m = gs_m * (1 - peso_reg) + media_gf_f * peso_reg
    gf_v = gf_v * (1 - peso_reg) + media_gf_f * peso_reg
    gs_v = gs_v * (1 - peso_reg) + media_gf_c * peso_reg
    
    xg_c = gf_m * (gs_v / media_gf_f) if media_gf_f > 0 else gf_m
    xg_f = gf_v * (gs_m / media_gf_c) if media_gf_c > 0 else gf_v
    
    xg_c = max(0.5, min(xg_c, 3.0))
    xg_f = max(0.5, min(xg_f, 3.0))
    
    amostra = len(df_c) + len(df_f)
    return xg_c, xg_f, amostra

def ler_odd(label):
    val = st.sidebar.text_input(label, value="", key=f"manual_{label}")
    if not val: return 1.00
    try: return float(val.replace(',', '.'))
    except: return 1.00

# ==========================================
# INTERFACE
# ==========================================
st.sidebar.markdown("## 🎛️ Painel de Controle")
modo_operacao = st.sidebar.radio("Selecione o Ambiente de Execução:", 
                                ["Modo Manual (Laboratório)", "Modo FULL AUTO (Institucional)"])
st.sidebar.markdown("---")

st.title(f"🚀 Motor TEX STATISTICS PRO 2.15")
st.markdown(f"**Status de Operação:** `{modo_operacao}` | API Monitorada")

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
        with st.spinner("Extraindo e Saneando cotações..."):
            dados_api = extrair_odds_api(API_KEY, LIGAS_API[liga_sel])
        
        if dados_api:
            agora = pd.Timestamp.utcnow()
            jogos_validos = {}
            
            for j in dados_api:
                hora_jogo = pd.to_datetime(j['commence_time'])
                if hora_jogo > agora:
                    horario_br = hora_jogo.tz_convert('America/Sao_Paulo').strftime('%d/%m %H:%M')
                    nome_formatated = f"{j['home_team']} vs {j['away_team']} (Início: {horario_br})"
                    jogos_validos[nome_formatated] = j

            if not jogos_validos:
                st.warning("⚠️ Sem partidas pré-jogo disponíveis nesta liga no momento (Ligas fora de rodada ou em pausa). Teste o 'Modo Manual' para simular.")
                pronto_para_calcular = False
            else:
                jogo_sel = st.selectbox("🎯 Selecione a Partida", list(jogos_validos.keys()))
                jogo_dados = jogos_validos[jogo_sel]

                melhores_odds = {
                    "Vitória Casa": {"odd": 1.01, "casa": "N/A"},
                    "Empate": {"odd": 1.01, "casa": "N/A"},
                    "Vitória Fora": {"odd": 1.01, "casa": "N/A"},
                    "Mais de 2.5 gols": {"odd": 1.01, "casa": "N/A"}
                }

                debug_odds_raw = []

                for bookmaker in jogo_dados.get('bookmakers', []):
                    bk_key = bookmaker.get('key', '').lower()
                    if bk_key in EXCHANGES_BLOQUEADAS:
                        continue 
                        
                    bk_name = bookmaker.get('title', 'Desconhecido')
                    for market in bookmaker.get('markets', []):
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                name = outcome['name']
                                price = float(outcome['price'])
                                debug_odds_raw.append(f"{bk_name} | {name} | @{price}")
                                
                                if name == jogo_dados['home_team'] and 1.05 <= price <= 20.0:
                                    if price > melhores_odds["Vitória Casa"]["odd"]:
                                        melhores_odds["Vitória Casa"] = {"odd": price, "casa": bk_name}
                                elif name == 'Draw' and 1.05 <= price <= 12.0:
                                    if price > melhores_odds["Empate"]["odd"]:
                                        melhores_odds["Empate"] = {"odd": price, "casa": bk_name}
                                elif name == jogo_dados['away_team'] and 1.05 <= price <= 20.0:
                                    if price > melhores_odds["Vitória Fora"]["odd"]:
                                        melhores_odds["Vitória Fora"] = {"odd": price, "casa": bk_name}
                        
                        elif market['key'] == 'totals':
                            for outcome in market['outcomes']:
                                if outcome.get('name') == 'Over' and float(outcome.get('point', 0)) == 2.5:
                                    price = float(outcome['price'])
                                    debug_odds_raw.append(f"{bk_name} | Over 2.5 | @{price}")
                                    if 1.05 <= price <= 6.0:
                                        if price > melhores_odds["Mais de 2.5 gols"]["odd"]:
                                            melhores_odds["Mais de 2.5 gols"] = {"odd": price, "casa": bk_name}

                st.session_state.debug_raw = debug_odds_raw

                h = melhores_odds["Vitória Casa"]["odd"]
                d = melhores_odds["Empate"]["odd"]
                a = melhores_odds["Vitória Fora"]["odd"]

                odd_1X = 1 / ((1 / h) + (1 / d)) if h > 1.01 and d > 1.01 else 1.01
                odd_X2 = 1 / ((1 / a) + (1 / d)) if a > 1.01 and d > 1.01 else 1.01
                odd_DNB_H = h * (1 - (1 / d)) if h > 1.01 and d > 1.01 else 1.01
                odd_DNB_A = a * (1 - (1 / d)) if a > 1.01 and d > 1.01 else 1.01

                st.info("📡 Line Shopping concluído com sucesso.")

                st.markdown("### 🔄 Calibrar Nomes do Banco de Dados")
                c1, c2 = st.columns(2)
                guess_h = encontrar_melhor_match(jogo_dados['home_team'], times_csv) or times_csv[0]
                guess_a = encontrar_melhor_match(jogo_dados['away_team'], times_csv) or times_csv[1]

                t_casa = c1.selectbox("🏠 Mandante (CSV)", times_csv, 
                                    index=times_csv.index(guess_h) if guess_h in times_csv else 0, key="sel_casa_auto")
                t_fora = c2.selectbox("✈️ Visitante (CSV)", times_csv, 
                                    index=times_csv.index(guess_a) if guess_a in times_csv else 1, key="sel_fora_auto")

                odds = {
                    "Vitória Casa": h,
                    "Empate": d,
                    "Vitória Fora": a,
                    "Casa ou Empate": odd_1X,
                    "Fora ou Empate": odd_X2,
                    "Empate Anula Casa": odd_DNB_H,
                    "Empate Anula Fora": odd_DNB_A,
                    "Mais de 2.5 gols": melhores_odds["Mais de 2.5 gols"]["odd"],
                    "Ambos marcam": 1.01
                }

                st.session_state.melhores_odds_info = melhores_odds
                pronto_para_calcular = st.button("CALCULAR MOTOR AUTOMATIZADO")
        else:
            # A mensagem de erro detalhada da API já será exibida acima pelo st.error customizado
            pronto_para_calcular = False

    # ==========================================
    # CÁLCULO E ANÁLISE
    # ==========================================
    if 'pronto_para_calcular' in locals() and pronto_para_calcular:
        xg_c, xg_f, amostra = calcular_power_rating(df, t_casa, t_fora)
        
        amostra_relevante = len(df[df['Home'] == t_casa]) + len(df[df['Away'] == t_fora])
        confianca = min(100, (amostra_relevante / 40) * 100) 
        confianca = max(30, confianca)
        
        if confianca <= 50: st.markdown(f"# 🔴 CONFIANÇA: {confianca:.0f}%")
        elif confianca <= 85: st.markdown(f"# 🟡 CONFIANÇA: {confianca:.0f}%")
        else: st.markdown(f"# 🟢 CONFIANÇA: {confianca:.0f}%")

        st.markdown("### 🛠️ Debug Estatístico")
        media_gf_c = np.average(df['HG'], weights=df['Peso'])
        media_gf_f = np.average(df['AG'], weights=df['Peso'])
        st.write(f"- **Jogos Mapeados:** {t_casa}: `{len(df[df['Home'] == t_casa])}` | {t_fora}: `{len(df[df['Away'] == t_fora])}`")
        st.write(f"⚽ **xG Calculado:** {t_casa} **{xg_c:.2f}** x **{xg_f:.2f}** {t_fora}")

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

        st.write(f"**Probabilidades:** Casa `{prob['Vitória Casa']*100:.1f}%` | Empate `{prob['Empate']*100:.1f}%` | Fora `{prob['Vitória Fora']*100:.1f}%`")
        st.markdown("---")

        resultados_processados = []

        for merc, p in prob.items():
            odd_b = odds.get(merc, 1.00)
            if odd_b <= 1.01 and modo_operacao == "Modo FULL AUTO (Institucional)":
                continue

            if modo_operacao == "Modo FULL AUTO (Institucional)":
                info = st.session_state.get('melhores_odds_info', {}).get(merc, {})
                nome_casa = info.get("casa", "N/A") if isinstance(info, dict) else "N/A"
                texto_casa = f" *(Casa: {nome_casa})*"
            else:
                texto_casa = ""

            margem = (p * odd_b) - 1
            status = margem >= 0.10 and confianca > 50
            
            resultados_processados.append({
                "merc": merc, "prob": p, "odd_mercado": odd_b, "odd_justa": 1/p,
                "ev": margem, "status": status, "texto_casa": texto_casa
            })

        resultados_processados.sort(key=lambda x: x['ev'], reverse=True)

        sugestoes_verde = []
        sugestoes_vermelho = []

        for item in resultados_processados:
            prefixo = "✅ APOSTAR" if item['status'] else "❌ NÃO APOSTAR"
            
            with st.expander(f"{prefixo} | {item['merc']} ({item['prob']*100:.1f}%) | EV: {item['ev']*100:+.1f}%"):
                st.write(f"Odd justa da Máquina: **{item['odd_justa']:.2f}**")
                st.write(f"Odd do Mercado: **{item['odd_mercado']:.2f}**{item['texto_casa']}")

            stake_txt = f" (4% = R$ {banca_total*0.04:.2f})" if banca_total > 0 else " (4%)"
            
            if item['status']:
                sugestoes_verde.append(f"✅ **{item['merc']}** ({item['prob']*100:.1f}% chance) | EV: {item['ev']*100:+.1f}% {stake_txt}")
            else:
                sugestoes_vermelho.append(f"❌ **{item['merc']}** (EV: {item['ev']*100:+.1f}%)")

        st.markdown("---")
        st.subheader("📋 Resumo Executivo TEX")
        if sugestoes_verde: st.success("SUGESTÕES DE OPERAÇÃO:\n\n" + "\n\n".join(sugestoes_verde))
        if sugestoes_vermelho: st.error("NÃO OPERAR:\n\n" + "\n\n".join(sugestoes_vermelho))
else:
    st.error("❌ Banco de dados da liga selecionada está vazio ou indisponível. Verifique a URL do arquivo CSV.")
