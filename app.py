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
    "França - Ligue 1": "
