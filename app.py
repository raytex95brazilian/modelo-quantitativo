import os
import io
import json
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.stats import poisson

# ============================================================
# TEX STATISTICS PRO 15.14 — HÍBRIDO
# Coração da versão 2.14 + visual em blocos + banca dinâmica + auditoria
# Tela em português brasileiro, sem termos técnicos desnecessários
# ============================================================

st.set_page_config(page_title="TEX STATISTICS — Claro Total", layout="wide")

# ============================================================
# ESTILO VISUAL — melhor para celular
# ============================================================
st.markdown(
    """
    <style>
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Space+Grotesk:wght@600;700&display=swap");

    :root {
        color-scheme: light;
        --bg: #f6f7fb;
        --bg-soft: #eef2f7;
        --card: #ffffff;
        --card-soft: #f9fafb;
        --text: #111827;
        --muted: #64748b;
        --line: #e5e7eb;
        --line-strong: #d1d5db;
        --accent: #0f766e;
        --accent-soft: #ccfbf1;
        --accent-line: #99f6e4;
        --verde: #059669;
        --amarelo: #d97706;
        --azul: #2563eb;
        --vermelho: #dc2626;
        --shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
        --shadow-soft: 0 8px 22px rgba(15, 23, 42, 0.055);
    }

    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, var(--bg) 0%, var(--bg-soft) 100%) !important;
        color: var(--text) !important;
        font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif !important;
    }

    [data-testid="stHeader"] {
        background: rgba(246, 247, 251, 0.88) !important;
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(229, 231, 235, 0.9);
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 2.2rem;
        max-width: 1180px;
    }

    .block-container,
    .block-container h1,
    .block-container h2,
    .block-container h3,
    .block-container h4,
    .block-container h5,
    .block-container h6,
    .block-container p,
    .block-container label,
    .block-container span,
    .block-container div,
    [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"] {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    [data-testid="stSidebar"],
    [data-testid="stSidebarContent"] {
        background: #ffffff !important;
        color: var(--text) !important;
        border-right: 1px solid var(--line);
        box-shadow: 6px 0 28px rgba(15, 23, 42, 0.035);
    }

    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] small,
    [data-testid="stSidebar"] strong,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        opacity: 1 !important;
    }

    [data-testid="stCaptionContainer"],
    .stCaption,
    .mini,
    .help {
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
    }

    .hero {
        position: relative;
        overflow: hidden;
        background: #ffffff !important;
        color: var(--text) !important;
        border-radius: 24px;
        padding: 24px 22px 20px 22px;
        box-shadow: var(--shadow);
        margin-bottom: 16px;
        border: 1px solid var(--line);
    }

    .hero::before {
        content: "";
        position: absolute;
        width: 6px;
        height: 70%;
        border-radius: 999px;
        background: var(--accent);
        top: 15%;
        left: 0;
    }

    .hero::after {
        content: "";
        position: absolute;
        width: 220px;
        height: 220px;
        border-radius: 999px;
        background: radial-gradient(circle, rgba(15, 118, 110, 0.09) 0%, transparent 70%);
        top: -95px;
        right: -85px;
    }

    .hero * {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        position: relative;
        z-index: 1;
    }

    .hero-topo {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 10px;
    }

    .hero-selo {
        display: inline-block;
        padding: 7px 11px;
        border-radius: 999px;
        background: #f8fafc;
        border: 1px solid var(--line);
        color: #334155 !important;
        -webkit-text-fill-color: #334155 !important;
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.25px;
        text-transform: uppercase;
    }

    .hero-titulo {
        font-family: "Space Grotesk", "Inter", "Segoe UI", sans-serif;
        font-size: 2.18rem;
        font-weight: 700;
        margin: 4px 0 6px 0;
        letter-spacing: -0.8px;
        line-height: 1.05;
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    .hero-sub {
        font-size: 0.98rem;
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
        line-height: 1.58;
        max-width: 900px;
        font-weight: 500;
    }

    .hero-chip-wrap {
        margin-top: 14px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    .hero-chip {
        display: inline-block;
        padding: 8px 11px;
        border-radius: 999px;
        background: #ecfdf5;
        border: 1px solid #bbf7d0;
        color: #166534 !important;
        -webkit-text-fill-color: #166534 !important;
        font-size: 0.8rem;
        font-weight: 800;
    }

    .painel-resumo {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 0 0 16px 0;
    }

    .resumo-card,
    div[data-testid="stMetric"],
    .caixa-info,
    .card-aposta,
    [data-testid="stExpander"],
    [data-testid="stDataFrame"] {
        background: #ffffff !important;
        border: 1px solid var(--line) !important;
        box-shadow: var(--shadow-soft) !important;
    }

    .resumo-card {
        border-radius: 18px;
        padding: 14px 16px;
    }

    .resumo-label {
        font-size: 0.77rem;
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.25px;
    }

    .resumo-valor {
        font-size: 1rem;
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        font-weight: 850;
        margin-top: 4px;
        line-height: 1.25;
    }

    div[data-testid="stMetric"] {
        border-radius: 18px;
        padding: 12px 13px;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.36rem;
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        font-weight: 850;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricDelta"] {
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
        font-weight: 750;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        padding: 5px 0 12px 0;
        flex-wrap: wrap;
    }

    .stTabs [data-baseweb="tab"] {
        background: #ffffff !important;
        border: 1px solid var(--line) !important;
        border-radius: 999px;
        padding: 9px 15px;
        height: auto;
        box-shadow: none;
        font-weight: 800;
        color: #334155 !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--accent-soft) !important;
        border-color: var(--accent-line) !important;
        color: #115e59 !important;
    }

    .stTabs [aria-selected="true"] * {
        color: #115e59 !important;
        -webkit-text-fill-color: #115e59 !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 14px !important;
        border: 1px solid #0f172a !important;
        background: #0f172a !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 850 !important;
        padding: 0.62rem 1rem !important;
        box-shadow: 0 10px 22px rgba(15, 23, 42, 0.14) !important;
        transition: all 0.15s ease-in-out;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 14px 26px rgba(15, 23, 42, 0.18) !important;
    }

    .stButton > button[kind="secondary"],
    .stDownloadButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        border: 1px solid var(--line-strong) !important;
        box-shadow: none !important;
    }

    input,
    textarea,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="base-input"],
    [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        border-color: var(--line-strong) !important;
        border-radius: 14px !important;
        caret-color: var(--text) !important;
    }

    input::placeholder,
    textarea::placeholder {
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
        opacity: 1 !important;
    }

    [data-baseweb="popover"],
    [data-baseweb="menu"],
    [role="listbox"] {
        background: #ffffff !important;
        color: var(--text) !important;
    }

    [data-baseweb="popover"] *,
    [data-baseweb="menu"] *,
    [role="listbox"] * {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    .stTextInput > div > div,
    .stNumberInput > div > div,
    .stDateInput > div > div,
    .stSelectbox > div > div {
        border-radius: 14px !important;
    }

    .caixa-info {
        border-radius: 18px;
        padding: 14px 16px;
        margin: 8px 0 16px 0;
    }

    .caixa-info strong {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    .caixa-info p,
    .caixa-info div,
    .caixa-info span {
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
    }

    .card-aposta {
        position: relative;
        border-radius: 20px;
        padding: 18px 18px 14px 18px;
        margin: 14px 0;
        color: var(--text) !important;
        overflow: hidden;
    }

    .card-aposta::after {
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        width: 96px;
        height: 96px;
        background: radial-gradient(circle, rgba(15, 118, 110, 0.07) 0%, transparent 70%);
    }

    .card-aposta div,
    .card-aposta span,
    .card-aposta p,
    .card-aposta b,
    .card-aposta strong {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
        position: relative;
        z-index: 1;
    }

    .card-forte { border-left: 8px solid var(--verde) !important; }
    .card-boa { border-left: 8px solid var(--amarelo) !important; }
    .card-leve { border-left: 8px solid var(--azul) !important; }
    .card-nao { border-left: 8px solid var(--vermelho) !important; }

    .titulo-card {
        font-size: 1.04rem;
        font-weight: 850;
        margin-bottom: 8px;
        letter-spacing: -0.15px;
    }

    .mercado-card {
        font-size: 1.28rem;
        font-weight: 900;
        margin-bottom: 12px;
        letter-spacing: -0.25px;
    }

    .linha-info {
        font-size: 0.95rem;
        line-height: 1.68;
    }

    .mini {
        font-size: 0.84rem;
        color: var(--muted) !important;
        -webkit-text-fill-color: var(--muted) !important;
    }

    .ok {
        color: var(--verde) !important;
        -webkit-text-fill-color: var(--verde) !important;
        font-weight: 900;
    }

    .warn {
        color: var(--amarelo) !important;
        -webkit-text-fill-color: var(--amarelo) !important;
        font-weight: 900;
    }

    .bad {
        color: var(--vermelho) !important;
        -webkit-text-fill-color: var(--vermelho) !important;
        font-weight: 900;
    }

    .blue {
        color: var(--azul) !important;
        -webkit-text-fill-color: var(--azul) !important;
        font-weight: 900;
    }

    .etiqueta {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: #f8fafc;
        border: 1px solid var(--line);
        color: #334155 !important;
        -webkit-text-fill-color: #334155 !important;
        font-size: 0.8rem;
        font-weight: 800;
        margin-right: 6px;
        margin-bottom: 6px;
    }

    [data-testid="stExpander"] {
        border-radius: 18px;
        overflow: hidden;
    }

    .stAlert {
        border-radius: 16px !important;
        border: 1px solid var(--line) !important;
        box-shadow: var(--shadow-soft) !important;
        background: #ffffff !important;
        color: var(--text) !important;
    }

    .stAlert * {
        color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important;
    }

    [data-testid="stDataFrame"] {
        border-radius: 18px;
        overflow: hidden;
    }

    hr {
        border-color: var(--line) !important;
    }

    a {
        color: #0f766e !important;
        -webkit-text-fill-color: #0f766e !important;
        font-weight: 700;
    }

    @media (max-width: 900px) {
        .painel-resumo {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.85rem;
            padding-right: 0.85rem;
        }

        .hero {
            border-radius: 20px;
            padding: 20px 17px 16px 17px;
        }

        .hero-titulo {
            font-size: 1.54rem;
            letter-spacing: -0.35px;
        }

        .hero-sub {
            font-size: 0.92rem;
        }

        .hero-chip {
            font-size: 0.77rem;
            padding: 7px 10px;
        }

        .painel-resumo {
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .resumo-card {
            padding: 12px;
        }

        .resumo-valor {
            font-size: 0.94rem;
        }

        .titulo-card {
            font-size: 0.98rem;
        }

        .mercado-card {
            font-size: 1.12rem;
        }

        .linha-info {
            font-size: 0.91rem;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.12rem;
        }
    }


    /* =========================================================
       FORÇA TEMA CLARO EM TODOS OS CAMPOS DO STREAMLIT/BASEWEB
       Corrige caixas que ficam escuras no celular ou navegador
       em modo noturno: selectbox, text_input, number_input,
       text_area, multiselect, dropdown aberto, calendário, radio,
       checkbox e estados de foco/hover.
       ========================================================= */

    html {
        color-scheme: light !important;
        background: #f6f7fb !important;
    }

    body,
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    [data-testid="stVerticalBlock"],
    [data-testid="stForm"],
    [data-testid="stFormSubmitButton"] {
        background-color: #f6f7fb !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    /* Labels e textos comuns */
    label,
    p,
    span,
    small,
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stWidgetLabel"],
    .stMarkdown,
    .stCaption {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    .stCaption,
    [data-testid="stCaptionContainer"],
    .mini,
    .help,
    small {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
    }

    /* Inputs fechados: texto, número, senha, área de texto */
    .stTextInput,
    .stNumberInput,
    .stTextArea,
    .stDateInput,
    .stSelectbox,
    .stMultiSelect {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    .stTextInput > div,
    .stNumberInput > div,
    .stTextArea > div,
    .stDateInput > div,
    .stSelectbox > div,
    .stMultiSelect > div {
        background: transparent !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    input,
    textarea,
    input:focus,
    textarea:focus,
    input:active,
    textarea:active,
    [data-baseweb="input"],
    [data-baseweb="input"] > div,
    [data-baseweb="input"] input,
    [data-baseweb="textarea"],
    [data-baseweb="textarea"] > div,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="base-input"],
    [data-baseweb="base-input"] input,
    [data-baseweb="base-input"] textarea {
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
        border-color: #cbd5e1 !important;
        box-shadow: none !important;
        outline: none !important;
    }

    input::placeholder,
    textarea::placeholder,
    [data-baseweb="input"] input::placeholder,
    [data-baseweb="textarea"] textarea::placeholder {
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
        opacity: 1 !important;
    }

    input:-webkit-autofill,
    input:-webkit-autofill:hover,
    input:-webkit-autofill:focus,
    textarea:-webkit-autofill,
    textarea:-webkit-autofill:hover,
    textarea:-webkit-autofill:focus {
        -webkit-box-shadow: 0 0 0 1000px #ffffff inset !important;
        -webkit-text-fill-color: #111827 !important;
        caret-color: #111827 !important;
        transition: background-color 9999s ease-in-out 0s !important;
    }

    /* Selectbox e multiselect fechados */
    [data-baseweb="select"],
    [data-baseweb="select"] > div,
    [data-baseweb="select"] div,
    [data-baseweb="select"] input,
    [data-baseweb="select"] span {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: #cbd5e1 !important;
    }

    [data-baseweb="select"] svg,
    [data-testid="stSelectbox"] svg,
    [data-testid="stMultiSelect"] svg {
        fill: #334155 !important;
        color: #334155 !important;
    }

    [data-baseweb="tag"],
    [data-baseweb="tag"] span {
        background-color: #ecfdf5 !important;
        color: #065f46 !important;
        -webkit-text-fill-color: #065f46 !important;
    }

    /* Dropdown aberto: este é o trecho que corrige a caixa escura */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"],
    [data-baseweb="menu"] ul,
    [data-baseweb="menu"] li,
    [role="listbox"],
    [role="listbox"] ul,
    [role="listbox"] li,
    ul[role="listbox"],
    li[role="option"],
    div[role="option"],
    [data-baseweb="option"] {
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: #e5e7eb !important;
    }

    [data-baseweb="popover"] *,
    [data-baseweb="menu"] *,
    [role="listbox"] *,
    [role="option"] * {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    [role="option"]:hover,
    [role="option"][aria-selected="true"],
    [data-baseweb="menu"] li:hover,
    [data-baseweb="menu"] li[aria-selected="true"] {
        background: #f1f5f9 !important;
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    /* Menu suspenso, tooltips e caixas flutuantes */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] div,
    div[data-baseweb="tooltip"],
    div[data-baseweb="tooltip"] div {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: #e5e7eb !important;
    }

    /* Calendário do date_input */
    [data-baseweb="calendar"],
    [data-baseweb="calendar"] *,
    [data-baseweb="datepicker"],
    [data-baseweb="datepicker"] * {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    /* Radio e checkbox */
    .stRadio,
    .stCheckbox,
    .stRadio *,
    .stCheckbox * {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    [data-baseweb="radio"] div,
    [data-baseweb="checkbox"] div {
        background-color: #ffffff !important;
        color: #111827 !important;
        border-color: #cbd5e1 !important;
    }

    /* Slider */
    .stSlider,
    .stSlider *,
    [data-baseweb="slider"],
    [data-baseweb="slider"] * {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    /* Number input: botões de + e - */
    .stNumberInput button,
    [data-testid="stNumberInput"] button,
    button[aria-label="Increment"],
    button[aria-label="Decrement"] {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: #cbd5e1 !important;
        box-shadow: none !important;
    }

    .stNumberInput button svg,
    [data-testid="stNumberInput"] button svg,
    button[aria-label="Increment"] svg,
    button[aria-label="Decrement"] svg {
        fill: #111827 !important;
        color: #111827 !important;
    }

    /* Expanders e cards internos */
    [data-testid="stExpander"],
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] div {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    /* Tabelas/Dataframes */
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    [data-testid="stDataFrame"] *,
    [data-testid="stTable"] * {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    /* Sidebar totalmente clara */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarContent"] > div {
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }

    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="select"] div,
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] [data-baseweb="input"] div,
    [data-testid="stSidebar"] [data-baseweb="base-input"] {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: #cbd5e1 !important;
    }

    /* Evita que o navegador/tema escuro pinte componentes nativos */
    select,
    option,
    optgroup {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
    }


    /* =========================================================
       BOTÕES 100% CLAROS — INCLUSIVE TYPE="PRIMARY"
       Remove qualquer fundo escuro do botão ANALISAR e de todos
       os outros botões do Streamlit, em todos os estados.
       ========================================================= */

    .stButton > button,
    .stDownloadButton > button,
    .stFormSubmitButton > button,
    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button,
    div[data-testid="stFormSubmitButton"] button,
    button[kind="primary"],
    button[kind="secondary"],
    button[kind="tertiary"],
    button[data-testid="baseButton-primary"],
    button[data-testid="baseButton-secondary"],
    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-tertiary"] {
        background: #ffffff !important;
        background-color: #ffffff !important;
        background-image: none !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 14px !important;
        box-shadow: none !important;
        text-shadow: none !important;
        font-weight: 850 !important;
        outline: none !important;
    }

    .stButton > button:hover,
    .stButton > button:focus,
    .stButton > button:active,
    .stDownloadButton > button:hover,
    .stDownloadButton > button:focus,
    .stDownloadButton > button:active,
    .stFormSubmitButton > button:hover,
    .stFormSubmitButton > button:focus,
    .stFormSubmitButton > button:active,
    div[data-testid="stButton"] button:hover,
    div[data-testid="stButton"] button:focus,
    div[data-testid="stButton"] button:active,
    div[data-testid="stDownloadButton"] button:hover,
    div[data-testid="stDownloadButton"] button:focus,
    div[data-testid="stDownloadButton"] button:active,
    div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stFormSubmitButton"] button:focus,
    div[data-testid="stFormSubmitButton"] button:active,
    button[kind="primary"]:hover,
    button[kind="primary"]:focus,
    button[kind="primary"]:active,
    button[kind="secondary"]:hover,
    button[kind="secondary"]:focus,
    button[kind="secondary"]:active,
    button[kind="tertiary"]:hover,
    button[kind="tertiary"]:focus,
    button[kind="tertiary"]:active,
    button[data-testid="baseButton-primary"]:hover,
    button[data-testid="baseButton-primary"]:focus,
    button[data-testid="baseButton-primary"]:active,
    [data-testid="stBaseButton-primary"]:hover,
    [data-testid="stBaseButton-primary"]:focus,
    [data-testid="stBaseButton-primary"]:active {
        background: #f8fafc !important;
        background-color: #f8fafc !important;
        background-image: none !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border: 1px solid #94a3b8 !important;
        box-shadow: 0 0 0 3px rgba(148, 163, 184, 0.18) !important;
        transform: none !important;
        text-shadow: none !important;
        outline: none !important;
    }

    .stButton > button *,
    .stDownloadButton > button *,
    .stFormSubmitButton > button *,
    div[data-testid="stButton"] button *,
    div[data-testid="stDownloadButton"] button *,
    div[data-testid="stFormSubmitButton"] button *,
    button[kind="primary"] *,
    button[kind="secondary"] *,
    button[kind="tertiary"] *,
    [data-testid="stBaseButton-primary"] *,
    [data-testid="stBaseButton-secondary"] *,
    [data-testid="stBaseButton-tertiary"] * {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        fill: #111827 !important;
        stroke: #111827 !important;
        text-shadow: none !important;
    }

    .stButton > button:disabled,
    .stDownloadButton > button:disabled,
    .stFormSubmitButton > button:disabled,
    button:disabled,
    button[disabled] {
        background: #f1f5f9 !important;
        background-color: #f1f5f9 !important;
        background-image: none !important;
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        border-color: #e2e8f0 !important;
        opacity: 1 !important;
        box-shadow: none !important;
    }

    .stButton > button:disabled *,
    .stDownloadButton > button:disabled *,
    .stFormSubmitButton > button:disabled *,
    button:disabled *,
    button[disabled] * {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        fill: #64748b !important;
        stroke: #64748b !important;
    }

    /* Botões pequenos internos de widgets também ficam claros */
    button,
    button:hover,
    button:focus,
    button:active {
        color-scheme: light !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)
# ============================================================
# DADOS
# ============================================================

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
    "Grécia - Super League": "https://www.football-data.co.uk/mmz4281/2526/G1.csv",
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
    "Grécia - Super League": "soccer_greece_super_league",
}
MERCADOS = [
    "Vitória Casa",
    "Empate",
    "Vitória Fora",
    "Casa ou Empate",
    "Fora ou Empate",
    "Empate Anula Casa",
    "Empate Anula Fora",
    "Mais de 2.5 gols",
    "Menos de 2.5 gols",
    "Ambos marcam - Sim",
    "Ambos marcam - Não",
]

ARQUIVO_AUDITORIA = "logs/auditoria_tex_pro_15.csv"
ARQUIVO_AUDITORIA_XLSX = "logs/auditoria_tex_pro_15.xlsx"
ARQUIVO_CATALOGO_ODDS = "logs/catalogo_odds_tex_pro_15.csv"
ARQUIVO_CATALOGO_ODDS_XLSX = "logs/catalogo_odds_tex_pro_15.xlsx"

# Google Sheets — armazenamento persistente do catálogo de odds e da auditoria.
# Configure em .streamlit/secrets.toml:
#
# [google_sheets]
# spreadsheet_id = "ID_DA_PLANILHA_GOOGLE"
# worksheet_catalogo = "catalogo_odds"
# worksheet_auditoria = "auditoria_entradas"
#
# [gcp_service_account]
# type = "service_account"
# project_id = "..."
# private_key_id = "..."
# private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
# client_email = "...@...iam.gserviceaccount.com"
# client_id = "..."
# auth_uri = "https://accounts.google.com/o/oauth2/auth"
# token_uri = "https://oauth2.googleapis.com/token"
# auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
# client_x509_cert_url = "..."
# universe_domain = "googleapis.com"
GOOGLE_SHEETS_WORKSHEET_PADRAO = "catalogo_odds"
GOOGLE_SHEETS_WORKSHEET_AUDITORIA_PADRAO = "auditoria_entradas"

# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def dinheiro(valor: float) -> str:
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def porcentagem(valor: float, casas: int = 1) -> str:
    try:
        return f"{float(valor) * 100:.{casas}f}%".replace(".", ",")
    except Exception:
        return "0,0%"


def numero(valor: float, casas: int = 2) -> str:
    try:
        return f"{float(valor):.{casas}f}".replace(".", ",")
    except Exception:
        return "0,00"


def texto_para_float(txt: str) -> Optional[float]:
    if txt is None:
        return None
    txt = str(txt).strip().replace("R$", "").replace(" ", "")
    if not txt:
        return None
    try:
        # aceita 1,85 e 1.85
        if "," in txt and "." in txt:
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", ".")
        valor = float(txt)
        if not np.isfinite(valor):
            return None
        return valor
    except Exception:
        return None


def odd_valida(odd: Optional[float]) -> bool:
    return odd is not None and odd > 1.01 and np.isfinite(odd)


@st.cache_data(ttl=3600, show_spinner=False)
def extrair_dados(url: str, jogos_historicos: int = 500, peso_inicial: float = -2.60) -> pd.DataFrame:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df = df.rename(columns={"HomeTeam": "Home", "AwayTeam": "Away", "FTHG": "HG", "FTAG": "AG"})
        if not all(c in df.columns for c in ["Home", "Away", "HG", "AG"]):
            return pd.DataFrame()
        df = df.dropna(subset=["Home", "Away", "HG", "AG"]).copy()
        df["HG"] = pd.to_numeric(df["HG"], errors="coerce")
        df["AG"] = pd.to_numeric(df["AG"], errors="coerce")
        df = df.dropna(subset=["HG", "AG"])
        if "Date" in df.columns:
            df["DataTemp"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
            df = df.sort_values("DataTemp", kind="mergesort")

        # Janela histórica dinâmica.
        # Padrão profissional: 500 jogos da liga, com peso mais forte para jogos recentes.
        # Isso mantém estabilidade sem deixar temporadas antigas mandarem demais no cálculo.
        try:
            jogos_historicos = int(jogos_historicos)
        except Exception:
            jogos_historicos = 500
        jogos_historicos = int(np.clip(jogos_historicos, 120, 1500))

        try:
            peso_inicial = float(peso_inicial)
        except Exception:
            peso_inicial = -2.60
        peso_inicial = float(np.clip(peso_inicial, -4.00, -0.50))

        df = df.tail(jogos_historicos).reset_index(drop=True)
        if len(df) > 0:
            df["Peso"] = np.exp(np.linspace(peso_inicial, 0, len(df)))
        else:
            df["Peso"] = []
        return df
    except Exception:
        return pd.DataFrame()


def media_ponderada(serie: pd.Series, pesos: pd.Series, padrao: float) -> float:
    try:
        if len(serie) == 0:
            return float(padrao)
        return float(np.average(serie, weights=pesos))
    except Exception:
        return float(padrao)

# ============================================================
# MOTOR — base antiga melhorada
# ============================================================

def media_ponderada_estabilizada(serie: pd.Series, pesos: pd.Series, media_liga: float, k: float = 10.0) -> float:
    """
    Média do time puxada para a média da liga quando a amostra é pequena.

    Exemplo: se o visitante tem só 1 jogo fora, o app não pode concluir que ele
    é péssimo ou excelente. Com poucos jogos, a média da liga pesa mais.
    """
    try:
        n = len(serie)
        if n == 0:
            return float(media_liga)
        media_time = float(np.average(serie, weights=pesos))
        return float(((n * media_time) + (k * media_liga)) / (n + k))
    except Exception:
        return float(media_liga)


def calcular_forcas_e_probabilidades(df: pd.DataFrame, time_casa: str, time_fora: str) -> Tuple[float, float, Dict[str, float], float, Dict[str, object]]:
    """
    Motor híbrido 15.5:
    - mantém a lógica simples da versão 2.14;
    - usa Poisson direto;
    - corrige o erro de amostra pequena;
    - puxa dados pobres para a média da liga;
    - reduz confiança quando um dos lados tem poucos jogos no mando certo.
    """
    media_gols_casa_liga = max(0.20, float(np.average(df["HG"], weights=df["Peso"])))
    media_gols_fora_liga = max(0.20, float(np.average(df["AG"], weights=df["Peso"])))

    jogos_casa = df[df["Home"] == time_casa]
    jogos_fora = df[df["Away"] == time_fora]

    amostra_casa = len(jogos_casa)
    amostra_fora = len(jogos_fora)
    amostra_minima = min(amostra_casa, amostra_fora)
    amostra_total = amostra_casa + amostra_fora

    # Quanto menor a amostra, mais a média da liga entra no cálculo.
    # Isso evita absurdos como visitante com 1 jogo fora virar ataque 0,20.
    k_casa = 10.0
    k_fora = 12.0

    gols_feitos_casa = media_ponderada_estabilizada(jogos_casa["HG"], jogos_casa["Peso"], media_gols_casa_liga, k=k_casa)
    gols_sofridos_casa = media_ponderada_estabilizada(jogos_casa["AG"], jogos_casa["Peso"], media_gols_fora_liga, k=k_casa)
    gols_feitos_fora = media_ponderada_estabilizada(jogos_fora["AG"], jogos_fora["Peso"], media_gols_fora_liga, k=k_fora)
    gols_sofridos_fora = media_ponderada_estabilizada(jogos_fora["HG"], jogos_fora["Peso"], media_gols_casa_liga, k=k_fora)

    forca_ataque_casa = gols_feitos_casa / media_gols_casa_liga if media_gols_casa_liga > 0 else 1.0
    fragilidade_defesa_fora = gols_sofridos_fora / media_gols_casa_liga if media_gols_casa_liga > 0 else 1.0
    forca_ataque_fora = gols_feitos_fora / media_gols_fora_liga if media_gols_fora_liga > 0 else 1.0
    fragilidade_defesa_casa = gols_sofridos_casa / media_gols_fora_liga if media_gols_fora_liga > 0 else 1.0

    gols_esperados_casa = media_gols_casa_liga * forca_ataque_casa * fragilidade_defesa_fora
    gols_esperados_fora = media_gols_fora_liga * forca_ataque_fora * fragilidade_defesa_casa

    gols_esperados_casa = float(np.clip(gols_esperados_casa, 0.25, 4.00))
    gols_esperados_fora = float(np.clip(gols_esperados_fora, 0.25, 4.00))

    tamanho = 15
    matriz = np.zeros((tamanho, tamanho), dtype=float)
    for g_c in range(tamanho):
        for g_f in range(tamanho):
            matriz[g_c, g_f] = poisson.pmf(g_c, gols_esperados_casa) * poisson.pmf(g_f, gols_esperados_fora)

    soma = matriz.sum()
    if soma > 0:
        matriz = matriz / soma

    prob_casa = float(np.tril(matriz, -1).sum())
    prob_empate = float(np.diag(matriz).sum())
    prob_fora = float(np.triu(matriz, 1).sum())
    prob_mais25 = float(matriz[np.add.outer(np.arange(tamanho), np.arange(tamanho)) >= 3].sum())
    prob_ambos_sim = float(matriz[1:, 1:].sum())

    probabilidades = {
        "Vitória Casa": prob_casa,
        "Empate": prob_empate,
        "Vitória Fora": prob_fora,
        "Casa ou Empate": prob_casa + prob_empate,
        "Fora ou Empate": prob_fora + prob_empate,
        "Mais de 2.5 gols": prob_mais25,
        "Menos de 2.5 gols": 1.0 - prob_mais25,
        "Ambos marcam - Sim": prob_ambos_sim,
        "Ambos marcam - Não": 1.0 - prob_ambos_sim,
    }

    total_sem_empate = prob_casa + prob_fora
    probabilidades["Empate Anula Casa"] = prob_casa / total_sem_empate if total_sem_empate > 0 else 0.0
    probabilidades["Empate Anula Fora"] = prob_fora / total_sem_empate if total_sem_empate > 0 else 0.0

    # Confiança nova: quem manda é o lado com MENOS amostra.
    # Se visitante tem 1 jogo fora, confiança fica baixa, mesmo que o mandante tenha 90 jogos.
    confianca_minima_mando = min(100.0, (amostra_minima / 12.0) * 100.0)
    confianca_total = min(100.0, (amostra_total / 70.0) * 100.0)
    equilibrio = amostra_minima / max(1, max(amostra_casa, amostra_fora))

    confianca = (confianca_minima_mando * 0.70) + (confianca_total * 0.20) + (equilibrio * 10.0)

    if amostra_minima < 4:
        confianca = min(confianca, 35.0)
    elif amostra_minima < 8:
        confianca = min(confianca, 49.0)

    confianca = float(np.clip(confianca, 0.0, 100.0))

    if amostra_minima < 4:
        alerta = "Amostra muito baixa: não operar com dinheiro real."
    elif amostra_minima < 8:
        alerta = "Amostra baixa: observar ou usar valor simbólico."
    else:
        alerta = "Amostra suficiente para análise."

    amostras = {
        "casa": amostra_casa,
        "fora": amostra_fora,
        "total": amostra_total,
        "minima": amostra_minima,
        "alerta": alerta,
        "amostra_fraca": amostra_minima < 8,
    }
    return gols_esperados_casa, gols_esperados_fora, probabilidades, confianca, amostras

# ============================================================
# ODDS MANUAIS E API
# ============================================================

def input_odd(label: str, key: str) -> Optional[float]:
    valor = st.text_input(label, value="", key=key, placeholder="ex: 2,10")
    x = texto_para_float(valor)
    return x if odd_valida(x) else None


def coletar_odds_manuais(prefixo: str = "manual") -> Dict[str, float]:
    st.markdown("### Cotações da casa")
    st.caption("Preencha só o que você quer analisar. Campo vazio fica fora do cálculo.")

    odds: Dict[str, float] = {}

    st.markdown("**Resultado do jogo**")
    c1, c2, c3 = st.columns(3)
    with c1:
        odds["Vitória Casa"] = input_odd("Vitória Casa", f"{prefixo}_vitoria_casa")
    with c2:
        odds["Empate"] = input_odd("Empate", f"{prefixo}_empate")
    with c3:
        odds["Vitória Fora"] = input_odd("Vitória Fora", f"{prefixo}_vitoria_fora")

    st.markdown("**Gols**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Mais de 2.5 gols"] = input_odd("Mais de 2.5 gols", f"{prefixo}_mais25")
    with c2:
        odds["Menos de 2.5 gols"] = input_odd("Menos de 2.5 gols", f"{prefixo}_menos25")

    st.markdown("**Ambos marcam**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Ambos marcam - Sim"] = input_odd("Ambos marcam - Sim", f"{prefixo}_btts_sim")
    with c2:
        odds["Ambos marcam - Não"] = input_odd("Ambos marcam - Não", f"{prefixo}_btts_nao")

    st.markdown("**Proteções**")
    c1, c2 = st.columns(2)
    with c1:
        odds["Casa ou Empate"] = input_odd("Casa ou Empate", f"{prefixo}_casa_empate")
    with c2:
        odds["Fora ou Empate"] = input_odd("Fora ou Empate", f"{prefixo}_fora_empate")

    c1, c2 = st.columns(2)
    with c1:
        odds["Empate Anula Casa"] = input_odd("Empate Anula Casa", f"{prefixo}_anula_casa")
    with c2:
        odds["Empate Anula Fora"] = input_odd("Empate Anula Fora", f"{prefixo}_anula_fora")

    return {m: o for m, o in odds.items() if odd_valida(o)}


@st.cache_data(ttl=300, show_spinner=False)
def buscar_odds_api(chave: str, liga_api: str) -> Optional[List[dict]]:
    if not chave:
        return None
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{liga_api}/odds/"
        params = {
            "apiKey": chave,
            "regions": "eu,uk,us",
            "markets": "h2h,totals,btts",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def achar_time(nome_api: str, times_csv: List[str]) -> str:
    import difflib
    alvo = (nome_api or "").lower().replace("fc", "").replace("ec", "").replace("ac", "").strip()
    candidatos = [t.lower() for t in times_csv]
    achados = difflib.get_close_matches(alvo, candidatos, n=1, cutoff=0.68)
    if achados:
        return next(t for t in times_csv if t.lower() == achados[0])
    return times_csv[0]


def mediana(valores: List[float]) -> Optional[float]:
    limpos = [float(v) for v in valores if odd_valida(v)]
    if not limpos:
        return None
    return float(np.median(limpos))


def extrair_odds_de_jogo_api(jogo: dict) -> Dict[str, float]:
    pools = {m: [] for m in [
        "Vitória Casa", "Empate", "Vitória Fora", "Mais de 2.5 gols", "Menos de 2.5 gols", "Ambos marcam - Sim", "Ambos marcam - Não"
    ]}

    casa_api = jogo.get("home_team")
    fora_api = jogo.get("away_team")

    for book in jogo.get("bookmakers", []):
        for market in book.get("markets", []):
            key = market.get("key")
            for out in market.get("outcomes", []):
                nome = out.get("name")
                odd = texto_para_float(out.get("price"))
                if not odd_valida(odd):
                    continue

                if key == "h2h":
                    if nome == casa_api:
                        pools["Vitória Casa"].append(odd)
                    elif nome == "Draw":
                        pools["Empate"].append(odd)
                    elif nome == fora_api:
                        pools["Vitória Fora"].append(odd)

                elif key == "totals":
                    try:
                        ponto = float(out.get("point", 0))
                    except Exception:
                        ponto = 0
                    if abs(ponto - 2.5) < 0.001:
                        if nome == "Over":
                            pools["Mais de 2.5 gols"].append(odd)
                        elif nome == "Under":
                            pools["Menos de 2.5 gols"].append(odd)

                elif key == "btts":
                    if nome == "Yes":
                        pools["Ambos marcam - Sim"].append(odd)
                    elif nome == "No":
                        pools["Ambos marcam - Não"].append(odd)

    odds = {}
    for mercado, vals in pools.items():
        m = mediana(vals)
        if m is not None:
            odds[mercado] = m
    return odds

# ============================================================
# DECISÃO DE ENTRADA
# ============================================================

def classificar_entrada(prob: float, odd: float, confianca: float, perfil: str) -> Dict[str, object]:
    valor = (prob * odd) - 1.0
    odd_justa = 1.0 / prob if prob > 0 else np.inf

    if perfil == "Conservador":
        regras = [
            (0.18, 75, 0.030, "forte"),
            (0.13, 65, 0.020, "boa"),
            (0.09, 58, 0.010, "leve"),
        ]
    elif perfil == "Volume controlado":
        regras = [
            (0.15, 70, 0.030, "forte"),
            (0.10, 60, 0.020, "boa"),
            (0.06, 52, 0.010, "leve"),
        ]
    else:  # Agressivo com controle
        # Mais volume sem passar de 3% por entrada.
        # A diferença real do modo agressivo aparece em duas partes:
        # 1) aceita valor menor;
        # 2) na barra lateral, o limite total padrão do jogo sobe.
        regras = [
            (0.10, 60, 0.030, "forte"),
            (0.06, 52, 0.020, "boa"),
            (0.03, 45, 0.0075, "leve"),
        ]

    if not odd_valida(odd):
        return {
            "apostar": False,
            "nivel": "nao",
            "percentual": 0.0,
            "motivo": "cotação não informada",
            "valor": valor,
            "odd_justa": odd_justa,
        }

    confianca_minima_absoluta = 45 if perfil == "Agressivo com controle" else 50
    if confianca < confianca_minima_absoluta:
        return {
            "apostar": False,
            "nivel": "nao",
            "percentual": 0.0,
            "motivo": "amostra baixa",
            "valor": valor,
            "odd_justa": odd_justa,
        }

    for valor_min, conf_min, percentual, nivel in regras:
        if valor >= valor_min and confianca >= conf_min:
            return {
                "apostar": True,
                "nivel": nivel,
                "percentual": percentual,
                "motivo": "valor encontrado",
                "valor": valor,
                "odd_justa": odd_justa,
            }

    motivo = "valor insuficiente"
    if valor > 0 and confianca >= 50:
        motivo = "tem algum valor, mas fraco para entrada"
    return {
        "apostar": False,
        "nivel": "nao",
        "percentual": 0.0,
        "motivo": motivo,
        "valor": valor,
        "odd_justa": odd_justa,
    }


def montar_resultados(probabilidades: Dict[str, float], odds: Dict[str, float], confianca: float, banca: float, perfil: str, limite_total_jogo: float) -> List[Dict[str, object]]:
    resultados = []
    for mercado in MERCADOS:
        if mercado not in probabilidades or mercado not in odds:
            continue
        prob = float(probabilidades[mercado])
        odd = float(odds[mercado])
        decisao = classificar_entrada(prob, odd, confianca, perfil)
        percentual_original = min(float(decisao["percentual"]), 0.03)  # trava máxima: 3% por entrada
        resultados.append({
            "mercado": mercado,
            "probabilidade": prob,
            "odd": odd,
            "odd_justa": float(decisao["odd_justa"]),
            "valor": float(decisao["valor"]),
            "apostar": bool(decisao["apostar"]),
            "nivel": str(decisao["nivel"]),
            "percentual": percentual_original if decisao["apostar"] else 0.0,
            "percentual_original": percentual_original if decisao["apostar"] else 0.0,
            "entrada_rs": banca * percentual_original if banca > 0 and decisao["apostar"] else 0.0,
            "motivo": str(decisao["motivo"]),
        })

    ordem = {"forte": 0, "boa": 1, "leve": 2, "nao": 3}
    resultados.sort(key=lambda r: (ordem.get(r["nivel"], 9), -r["valor"]))

    # Limite real de exposição no mesmo jogo.
    # Correção 15.8: em vez de reduzir TODAS as entradas até ficarem minúsculas
    # e depois reprovar tudo, o app escolhe as melhores entradas até preencher o teto.
    # Isso evita o bug em que uma simulação com odds 10 em tudo gerava 0 entradas.
    limite_total_jogo = float(np.clip(limite_total_jogo, 0.01, 0.09))
    minimo_executavel = 0.003  # 0,30% da banca
    usado = 0.0
    aprovadas_ordenadas = [r for r in resultados if r["apostar"] and float(r["percentual_original"]) > 0]

    for r in aprovadas_ordenadas:
        percentual_desejado = float(r["percentual_original"])
        restante = max(0.0, limite_total_jogo - usado)

        if restante < minimo_executavel:
            r["apostar"] = False
            r["nivel"] = "nao"
            r["percentual"] = 0.0
            r["entrada_rs"] = 0.0
            r["motivo"] = "valor existe, mas o limite total do jogo já foi preenchido"
            continue

        if percentual_desejado <= restante:
            percentual_final = percentual_desejado
            if usado > 0:
                r["motivo"] = "valor encontrado; respeitando limite total do jogo"
        else:
            percentual_final = restante
            r["motivo"] = "valor encontrado; entrada reduzida pelo limite total do jogo"

        if percentual_final < minimo_executavel:
            r["apostar"] = False
            r["nivel"] = "nao"
            r["percentual"] = 0.0
            r["entrada_rs"] = 0.0
            r["motivo"] = "valor existe, mas ficou abaixo do mínimo executável após o limite do jogo"
        else:
            r["percentual"] = percentual_final
            r["entrada_rs"] = banca * percentual_final if banca > 0 else 0.0
            usado += percentual_final

    resultados.sort(key=lambda r: (ordem.get(r["nivel"], 9), -r["valor"]))
    return resultados

# ============================================================
# AUDITORIA
# ============================================================

def garantir_pasta_logs() -> None:
    os.makedirs("logs", exist_ok=True)


def carregar_auditoria() -> pd.DataFrame:
    garantir_pasta_logs()
    if os.path.exists(ARQUIVO_AUDITORIA):
        try:
            return pd.read_csv(ARQUIVO_AUDITORIA)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def salvar_auditoria(df: pd.DataFrame) -> None:
    garantir_pasta_logs()
    df.to_csv(ARQUIVO_AUDITORIA, index=False)


def banca_atual_auditada(banca_inicial: float, auditoria: pd.DataFrame) -> float:
    if auditoria.empty or "Resultado R$" not in auditoria.columns:
        return banca_inicial
    valores = pd.to_numeric(auditoria["Resultado R$"], errors="coerce").fillna(0.0)
    return float(banca_inicial + valores.sum())


def registrar_entrada(
    auditoria: pd.DataFrame,
    liga: str,
    jogo: str,
    casa_apostas: str,
    mercado: str,
    odd: float,
    prob: float,
    odd_justa: float,
    valor: float,
    percentual: float,
    entrada_rs: float,
    banca_antes: float,
    origem: str,
    observacao: str = "",
) -> pd.DataFrame:
    nova = {
        "ID": str(uuid.uuid4())[:8],
        "Registrado em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Liga": liga,
        "Jogo": jogo,
        "Casa de apostas": casa_apostas,
        "Mercado": mercado,
        "Cotação de entrada": round(float(odd), 4),
        "Cotação justa": round(float(odd_justa), 4) if np.isfinite(odd_justa) else "",
        "Chance pelo sistema %": round(float(prob) * 100, 2),
        "Valor esperado %": round(float(valor) * 100, 2),
        "Entrada %": round(float(percentual) * 100, 3),
        "Entrada R$": round(float(entrada_rs), 2),
        "Banca antes": round(float(banca_antes), 2),
        "Cotação de fechamento": "",
        "Vantagem no fechamento %": "",
        "Status": "Pendente",
        "Resultado R$": 0.0,
        "Banca depois": "",
        "Origem": origem,
        "Observação": observacao,
    }
    return pd.concat([auditoria, pd.DataFrame([nova])], ignore_index=True)


def calcular_resultado(status: str, entrada_rs: float, odd_entrada: float, valor_cashout: float = 0.0) -> float:
    if status == "Green":
        return entrada_rs * (odd_entrada - 1.0)
    if status == "Red":
        return -entrada_rs
    if status == "Void":
        return 0.0
    if status == "Cashout":
        return valor_cashout - entrada_rs
    return 0.0




def limpar_nome_aba(nome: str, usados: set) -> str:
    """Limpa nome de aba para Excel sem depender de biblioteca externa."""
    proibidos = ['\\', '/', '*', '[', ']', ':', '?']
    nome = str(nome or "Aba")
    for c in proibidos:
        nome = nome.replace(c, "-")
    nome = nome.strip()[:31] or "Aba"
    base = nome
    i = 2
    while nome in usados:
        sufixo = f" {i}"
        nome = (base[:31 - len(sufixo)] + sufixo).strip()
        i += 1
    usados.add(nome)
    return nome


def coluna_excel(n: int) -> str:
    """Converte 1 -> A, 27 -> AA."""
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def gerar_excel_simples(abas: Dict[str, pd.DataFrame]) -> bytes:
    """
    Gera arquivo .xlsx usando apenas bibliotecas internas do Python.
    Assim o app não quebra se o Streamlit Cloud não tiver openpyxl instalado.
    """
    import zipfile
    import html

    buffer = io.BytesIO()
    usados = set()
    nomes_abas = [limpar_nome_aba(nome, usados) for nome in abas.keys()]

    def valor_xml(valor):
        if valor is None:
            return ""
        try:
            if pd.isna(valor):
                return ""
        except Exception:
            pass
        if isinstance(valor, (datetime, date)):
            return valor.strftime("%Y-%m-%d")
        return str(valor)

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        content_types = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
            '<Default Extension="xml" ContentType="application/xml"/>',
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        ]
        for i in range(1, len(nomes_abas) + 1):
            content_types.append(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
        content_types.append('</Types>')
        z.writestr('[Content_Types].xml', ''.join(content_types))

        z.writestr(
            '_rels/.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

        sheets_xml = []
        rels_xml = []
        for i, nome in enumerate(nomes_abas, start=1):
            nome_esc = html.escape(nome, quote=True)
            sheets_xml.append(f'<sheet name="{nome_esc}" sheetId="{i}" r:id="rId{i}"/>')
            rels_xml.append(
                f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
            )

        z.writestr(
            'xl/workbook.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>' + ''.join(sheets_xml) + '</sheets></workbook>'
        )
        z.writestr(
            'xl/_rels/workbook.xml.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join(rels_xml) +
            '</Relationships>'
        )

        for idx, (aba_original, df) in enumerate(abas.items(), start=1):
            df = df.copy()
            if df.empty:
                df = pd.DataFrame([{"Aviso": "Sem registros."}])

            linhas = [list(df.columns)] + df.astype(object).where(pd.notnull(df), "").values.tolist()
            max_cols = max([len(linha) for linha in linhas] + [1])

            # Largura simples das colunas
            cols_xml = ['<cols>']
            for c in range(1, max_cols + 1):
                textos_coluna = [valor_xml(linha[c - 1]) if c - 1 < len(linha) else "" for linha in linhas[:200]]
                largura = min(max(10, max(len(t) for t in textos_coluna) + 2), 38)
                cols_xml.append(f'<col min="{c}" max="{c}" width="{largura}" customWidth="1"/>')
            cols_xml.append('</cols>')

            rows_xml = []
            for r_idx, linha in enumerate(linhas, start=1):
                cells = []
                for c_idx, valor in enumerate(linha, start=1):
                    ref = f"{coluna_excel(c_idx)}{r_idx}"
                    if isinstance(valor, (int, float, np.integer, np.floating)) and np.isfinite(valor):
                        cells.append(f'<c r="{ref}" t="n"><v>{float(valor)}</v></c>')
                    else:
                        texto = html.escape(valor_xml(valor), quote=False)
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{texto}</t></is></c>')
                rows_xml.append(f'<row r="{r_idx}">' + ''.join(cells) + '</row>')

            sheet_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                + ''.join(cols_xml) +
                '<sheetData>' + ''.join(rows_xml) + '</sheetData>'
                '</worksheet>'
            )
            z.writestr(f'xl/worksheets/sheet{idx}.xml', sheet_xml)

    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# CATÁLOGO DE ODDS MANUAIS
# ============================================================

COLUNAS_CATALOGO_ODDS = [
    "ID Coleta",
    "Registrado em",
    "Data da coleta",
    "Hora da coleta",
    "Casa de apostas",
    "Liga",
    "Jogo",
    "Mandante",
    "Visitante",
    "Data do jogo",
    "Hora do jogo",
    "Mercado",
    "Seleção",
    "Cotação",
    "Banca no momento",
    "Perfil",
    "Origem",
    "Observação",
]


COLUNAS_AUDITORIA = [
    "ID",
    "Registrado em",
    "Liga",
    "Jogo",
    "Casa de apostas",
    "Mercado",
    "Cotação de entrada",
    "Cotação justa",
    "Chance pelo sistema %",
    "Valor esperado %",
    "Entrada %",
    "Entrada R$",
    "Banca antes",
    "Cotação de fechamento",
    "Vantagem no fechamento %",
    "Status",
    "Resultado R$",
    "Banca depois",
    "Origem",
    "Observação",
]


def normalizar_catalogo_odds(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que o catálogo sempre tenha as mesmas colunas, na mesma ordem."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS_CATALOGO_ODDS)
    base = df.copy()
    for col in COLUNAS_CATALOGO_ODDS:
        if col not in base.columns:
            base[col] = ""
    return base[COLUNAS_CATALOGO_ODDS].fillna("")


def normalizar_auditoria(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que a auditoria sempre tenha as mesmas colunas, na mesma ordem."""
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUNAS_AUDITORIA)
    base = df.copy()
    for col in COLUNAS_AUDITORIA:
        if col not in base.columns:
            base[col] = ""
    base = base[COLUNAS_AUDITORIA].fillna("")

    # Mantém colunas monetárias/numéricas usáveis quando o dado vem do Google Sheets como texto.
    for col in [
        "Cotação de entrada",
        "Cotação justa",
        "Chance pelo sistema %",
        "Valor esperado %",
        "Entrada %",
        "Entrada R$",
        "Banca antes",
        "Cotação de fechamento",
        "Vantagem no fechamento %",
        "Resultado R$",
        "Banca depois",
    ]:
        if col in base.columns:
            # Não força conversão aqui para preservar células vazias; conversão é feita nos cálculos.
            base[col] = base[col].astype(str).replace({"nan": "", "None": ""})
    return base


def _segredo_para_dict(obj):
    """Converte st.secrets/AttrDict em dict comum, sem expor segredo na tela."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    try:
        return dict(obj)
    except Exception:
        return obj


def obter_config_google_sheets() -> Dict[str, str]:
    """Lê configuração do Google Sheets no secrets.toml, se existir."""
    try:
        cfg = _segredo_para_dict(st.secrets.get("google_sheets", {}))
        spreadsheet_id = str(cfg.get("spreadsheet_id", "")).strip()
        worksheet_catalogo = str(cfg.get("worksheet_catalogo", GOOGLE_SHEETS_WORKSHEET_PADRAO)).strip() or GOOGLE_SHEETS_WORKSHEET_PADRAO
        worksheet_auditoria = str(cfg.get("worksheet_auditoria", GOOGLE_SHEETS_WORKSHEET_AUDITORIA_PADRAO)).strip() or GOOGLE_SHEETS_WORKSHEET_AUDITORIA_PADRAO
        service_account = _segredo_para_dict(st.secrets.get("gcp_service_account", {}))
        client_email = str(service_account.get("client_email", "")).strip() if isinstance(service_account, dict) else ""
        return {
            "spreadsheet_id": spreadsheet_id,
            "worksheet_catalogo": worksheet_catalogo,
            "worksheet_auditoria": worksheet_auditoria,
            "client_email": client_email,
            "configurado": bool(spreadsheet_id and client_email),
        }
    except Exception:
        return {
            "spreadsheet_id": "",
            "worksheet_catalogo": GOOGLE_SHEETS_WORKSHEET_PADRAO,
            "worksheet_auditoria": GOOGLE_SHEETS_WORKSHEET_AUDITORIA_PADRAO,
            "client_email": "",
            "configurado": False,
        }


def google_sheets_configurado() -> bool:
    return bool(obter_config_google_sheets().get("configurado"))


@st.cache_resource(show_spinner=False)
def conectar_google_sheets_catalogo():
    """Abre a planilha Google do catálogo. Usa cache para não reconectar a cada clique."""
    if not google_sheets_configurado():
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        service_account = _segredo_para_dict(st.secrets.get("gcp_service_account", {}))
        service_account = json.loads(json.dumps(service_account))
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(service_account, scopes=scopes)
        client = gspread.authorize(creds)
        cfg = obter_config_google_sheets()
        return client.open_by_key(cfg["spreadsheet_id"])
    except Exception as exc:
        # Não quebra o app; volta para backup local se o Google Sheets falhar.
        st.warning(f"Google Sheets não conectou. O app vai usar backup local temporário. Detalhe: {exc}")
        return None


def obter_aba_catalogo_google():
    planilha = conectar_google_sheets_catalogo()
    if planilha is None:
        return None

    nome_aba = obter_config_google_sheets()["worksheet_catalogo"]
    try:
        aba = planilha.worksheet(nome_aba)
    except Exception:
        aba = planilha.add_worksheet(title=nome_aba, rows=1000, cols=max(20, len(COLUNAS_CATALOGO_ODDS)))

    try:
        primeira_linha = aba.row_values(1)
        if primeira_linha != COLUNAS_CATALOGO_ODDS:
            # Se a aba estiver vazia, cria cabeçalho. Se tiver cabeçalho antigo, atualiza a linha 1.
            if not primeira_linha:
                aba.append_row(COLUNAS_CATALOGO_ODDS, value_input_option="USER_ENTERED")
            else:
                aba.update("A1", [COLUNAS_CATALOGO_ODDS])
    except Exception:
        pass

    return aba




def obter_aba_google(nome_aba: str, colunas: List[str], linhas: int = 1000, cols_extra: int = 4):
    """Obtém uma aba existente no Google Sheets e garante cabeçalho, sem criar aba nova automaticamente."""
    planilha = conectar_google_sheets_catalogo()
    if planilha is None:
        return None

    nome_aba = str(nome_aba).strip()

    # IMPORTANTE:
    # Não usamos add_worksheet aqui.
    # Se o app não encontrar a aba, ele mostra quais abas existem em vez de quebrar
    # com erro redigido do gspread/Streamlit Cloud.
    try:
        abas = planilha.worksheets()
    except Exception as exc:
        st.error(
            "Consegui conectar na planilha, mas não consegui listar as abas do Google Sheets. "
            "Confira se a planilha foi compartilhada com o e-mail da conta de serviço. "
            f"Detalhe: {exc}"
        )
        st.stop()

    aba = None

    # 1) Procura pelo nome exato.
    for ws in abas:
        if str(ws.title).strip() == nome_aba:
            aba = ws
            break

    # 2) Se não achou, procura ignorando maiúsculas/minúsculas e espaços.
    if aba is None:
        for ws in abas:
            if str(ws.title).strip().lower() == nome_aba.lower():
                aba = ws
                break

    # 3) Se não achou, não tenta criar. Mostra o diagnóstico correto.
    if aba is None:
        nomes_abas = ", ".join([str(ws.title) for ws in abas]) or "nenhuma aba encontrada"
        st.error(
            f"Não encontrei a aba '{nome_aba}' na planilha do Google Sheets. "
            f"As abas que o app está enxergando são: {nomes_abas}. "
            "Confira se o nome no Secrets está exatamente igual ao nome da aba."
        )
        st.stop()

    # 4) Garante cabeçalho.
    try:
        primeira_linha = aba.row_values(1)
        if primeira_linha != colunas:
            if not primeira_linha:
                aba.append_row(colunas, value_input_option="USER_ENTERED")
            else:
                aba.update("A1", [colunas])
    except Exception as exc:
        st.warning(
            f"A aba '{nome_aba}' foi encontrada, mas não consegui ajustar o cabeçalho. "
            f"Detalhe: {exc}"
        )

    return aba


def obter_aba_auditoria_google():
    return obter_aba_google(
        "auditoria_entradas",
        COLUNAS_AUDITORIA,
        linhas=1500,
        cols_extra=4
    )


def carregar_auditoria_google() -> Optional[pd.DataFrame]:
    aba = obter_aba_auditoria_google()
    if aba is None:
        return None
    try:
        valores = aba.get_all_values()
        if not valores or len(valores) <= 1:
            return pd.DataFrame(columns=COLUNAS_AUDITORIA)
        cabecalho = valores[0]
        linhas = valores[1:]
        df = pd.DataFrame(linhas, columns=cabecalho)
        return normalizar_auditoria(df)
    except Exception as exc:
        st.warning(f"Não consegui ler a auditoria no Google Sheets. Usando backup local temporário. Detalhe: {exc}")
        return None


def salvar_auditoria_google(auditoria: pd.DataFrame) -> bool:
    aba = obter_aba_auditoria_google()
    if aba is None:
        return False
    try:
        base = normalizar_auditoria(auditoria).astype(str)
        valores = [COLUNAS_AUDITORIA] + base.values.tolist()
        aba.clear()
        aba.update("A1", valores, value_input_option="USER_ENTERED")
        return True
    except Exception as exc:
        st.warning(f"Não consegui salvar a auditoria no Google Sheets. O backup local foi atualizado, mas ele é temporário no Streamlit Cloud. Detalhe: {exc}")
        return False


def carregar_auditoria_local() -> pd.DataFrame:
    garantir_pasta_logs()
    if os.path.exists(ARQUIVO_AUDITORIA):
        try:
            df = pd.read_csv(ARQUIVO_AUDITORIA)
            return normalizar_auditoria(df)
        except Exception:
            return pd.DataFrame(columns=COLUNAS_AUDITORIA)
    return pd.DataFrame(columns=COLUNAS_AUDITORIA)


# As definições abaixo sobrescrevem as funções locais antigas.
# A auditoria agora usa Google Sheets quando configurado, com backup local apenas temporário.
def carregar_auditoria() -> pd.DataFrame:
    if google_sheets_configurado():
        df_google = carregar_auditoria_google()
        if df_google is not None:
            # Migra automaticamente uma auditoria local antiga, se existir, quando a aba online ainda estiver vazia.
            if df_google.empty:
                local = carregar_auditoria_local()
                if not local.empty:
                    salvar_auditoria_google(local)
                    return local
            return df_google
    return carregar_auditoria_local()


def salvar_auditoria(df: pd.DataFrame) -> str:
    garantir_pasta_logs()
    auditoria = normalizar_auditoria(df)

    # Backup local: útil para download, mas NÃO é permanente no Streamlit Cloud.
    auditoria.to_csv(ARQUIVO_AUDITORIA, index=False)
    try:
        excel_bytes = gerar_excel_auditoria(auditoria, banca_inicial if "banca_inicial" in globals() else 1000.0)
        with open(ARQUIVO_AUDITORIA_XLSX, "wb") as f:
            f.write(excel_bytes)
    except Exception:
        pass

    if google_sheets_configurado():
        if salvar_auditoria_google(auditoria):
            return "Google Sheets + backup local"
        return "backup local temporário; Google Sheets falhou"

    return "backup local temporário; Google Sheets não configurado"

def carregar_catalogo_odds_google() -> Optional[pd.DataFrame]:
    aba = obter_aba_catalogo_google()
    if aba is None:
        return None
    try:
        valores = aba.get_all_values()
        if not valores or len(valores) <= 1:
            return pd.DataFrame(columns=COLUNAS_CATALOGO_ODDS)
        cabecalho = valores[0]
        linhas = valores[1:]
        df = pd.DataFrame(linhas, columns=cabecalho)
        return normalizar_catalogo_odds(df)
    except Exception as exc:
        st.warning(f"Não consegui ler o catálogo no Google Sheets. Usando backup local temporário. Detalhe: {exc}")
        return None


def salvar_catalogo_odds_google(catalogo: pd.DataFrame) -> bool:
    aba = obter_aba_catalogo_google()
    if aba is None:
        return False
    try:
        base = normalizar_catalogo_odds(catalogo).astype(str)
        valores = [COLUNAS_CATALOGO_ODDS] + base.values.tolist()
        aba.clear()
        aba.update("A1", valores, value_input_option="USER_ENTERED")
        return True
    except Exception as exc:
        st.warning(f"Não consegui salvar no Google Sheets. O backup local foi atualizado, mas ele é temporário no Streamlit Cloud. Detalhe: {exc}")
        return False


def carregar_catalogo_odds_local() -> pd.DataFrame:
    garantir_pasta_logs()
    if os.path.exists(ARQUIVO_CATALOGO_ODDS):
        try:
            df = pd.read_csv(ARQUIVO_CATALOGO_ODDS)
            return normalizar_catalogo_odds(df)
        except Exception:
            return pd.DataFrame(columns=COLUNAS_CATALOGO_ODDS)
    return pd.DataFrame(columns=COLUNAS_CATALOGO_ODDS)


def carregar_catalogo_odds() -> pd.DataFrame:
    """Carrega do Google Sheets quando configurado; senão, usa arquivo local temporário."""
    if google_sheets_configurado():
        df_google = carregar_catalogo_odds_google()
        if df_google is not None:
            return df_google
    return carregar_catalogo_odds_local()


def selecao_por_mercado(mercado: str, time_casa: str, time_fora: str) -> str:
    mapa = {
        "Vitória Casa": time_casa,
        "Empate": "Empate",
        "Vitória Fora": time_fora,
        "Casa ou Empate": f"{time_casa} ou Empate",
        "Fora ou Empate": f"{time_fora} ou Empate",
        "Empate Anula Casa": time_casa,
        "Empate Anula Fora": time_fora,
        "Mais de 2.5 gols": "Mais de 2.5 gols",
        "Menos de 2.5 gols": "Menos de 2.5 gols",
        "Ambos marcam - Sim": "Sim",
        "Ambos marcam - Não": "Não",
    }
    return mapa.get(str(mercado), str(mercado))


def registrar_odds_no_catalogo(
    catalogo: pd.DataFrame,
    liga: str,
    jogo: str,
    time_casa: str,
    time_fora: str,
    casa_apostas: str,
    odds: Dict[str, float],
    banca: float,
    perfil: str,
    data_jogo: Optional[date] = None,
    hora_jogo: str = "",
    origem: str = "Manual",
    observacao: str = "",
) -> pd.DataFrame:
    agora = datetime.now()
    coleta_id = str(uuid.uuid4())[:8]

    if isinstance(data_jogo, (datetime, date)):
        data_jogo_txt = data_jogo.strftime("%Y-%m-%d")
    else:
        data_jogo_txt = str(data_jogo or "")

    linhas = []
    for mercado, odd in odds.items():
        if not odd_valida(odd):
            continue
        linhas.append({
            "ID Coleta": coleta_id,
            "Registrado em": agora.strftime("%Y-%m-%d %H:%M:%S"),
            "Data da coleta": agora.strftime("%Y-%m-%d"),
            "Hora da coleta": agora.strftime("%H:%M:%S"),
            "Casa de apostas": casa_apostas,
            "Liga": liga,
            "Jogo": jogo,
            "Mandante": time_casa,
            "Visitante": time_fora,
            "Data do jogo": data_jogo_txt,
            "Hora do jogo": str(hora_jogo or ""),
            "Mercado": str(mercado),
            "Seleção": selecao_por_mercado(str(mercado), time_casa, time_fora),
            "Cotação": round(float(odd), 4),
            "Banca no momento": round(float(banca), 2),
            "Perfil": perfil,
            "Origem": origem,
            "Observação": observacao,
        })

    if not linhas:
        return catalogo

    novo = pd.DataFrame(linhas)
    base = pd.concat([catalogo, novo], ignore_index=True)
    for col in COLUNAS_CATALOGO_ODDS:
        if col not in base.columns:
            base[col] = ""
    return base[COLUNAS_CATALOGO_ODDS]


def gerar_excel_catalogo_odds(catalogo: pd.DataFrame) -> bytes:
    if catalogo.empty:
        return gerar_excel_simples({"Catalogo": pd.DataFrame([{"Aviso": "Ainda não há odds salvas no catálogo."}])})

    base = catalogo.copy()
    base["Cotação"] = pd.to_numeric(base.get("Cotação", 0), errors="coerce")
    base["Banca no momento"] = pd.to_numeric(base.get("Banca no momento", 0), errors="coerce")
    base = base.sort_values("Registrado em", kind="mergesort")

    chaves = ["Casa de apostas", "Liga", "Jogo", "Mercado", "Seleção"]
    ultimas = base.groupby(chaves, dropna=False).tail(1).copy()
    ultimas = ultimas[[
        "Registrado em", "Casa de apostas", "Liga", "Jogo", "Data do jogo", "Hora do jogo",
        "Mercado", "Seleção", "Cotação", "Banca no momento", "Perfil", "Origem", "Observação"
    ]]

    resumo_jogo = (
        base.groupby(["Casa de apostas", "Liga", "Jogo"], dropna=False)
        .agg(
            Coletas=("ID Coleta", "nunique"),
            Odds_registradas=("Cotação", "count"),
            Primeira_coleta=("Registrado em", "min"),
            Ultima_coleta=("Registrado em", "max"),
        )
        .reset_index()
    )

    return gerar_excel_simples({
        "Historico odds": base,
        "Ultimas odds": ultimas,
        "Resumo por jogo": resumo_jogo,
    })


def salvar_catalogo_odds(catalogo: pd.DataFrame) -> str:
    """Salva o catálogo. Google Sheets é o destino permanente; local é apenas backup temporário."""
    garantir_pasta_logs()
    catalogo = normalizar_catalogo_odds(catalogo)

    # Backup local: útil para download, mas NÃO é permanente no Streamlit Cloud.
    catalogo.to_csv(ARQUIVO_CATALOGO_ODDS, index=False)
    try:
        excel_bytes = gerar_excel_catalogo_odds(catalogo)
        with open(ARQUIVO_CATALOGO_ODDS_XLSX, "wb") as f:
            f.write(excel_bytes)
    except Exception:
        # O CSV continua sendo salvo mesmo se houver falha ao gerar o XLSX.
        pass

    if google_sheets_configurado():
        if salvar_catalogo_odds_google(catalogo):
            return "Google Sheets + backup local"
        return "backup local temporário; Google Sheets falhou"

    return "backup local temporário; Google Sheets não configurado"


def gerar_excel_auditoria(auditoria: pd.DataFrame, banca_inicial: float) -> bytes:
    """Gera Excel completo da auditoria sem depender de openpyxl."""
    if auditoria.empty:
        return gerar_excel_simples({"Historico": pd.DataFrame([{"Aviso": "Ainda não há entradas registradas na auditoria."}])})

    base = auditoria.copy()
    base["Resultado R$"] = pd.to_numeric(base.get("Resultado R$", 0), errors="coerce").fillna(0.0)
    base["Entrada R$"] = pd.to_numeric(base.get("Entrada R$", 0), errors="coerce").fillna(0.0)
    base["Valor esperado %"] = pd.to_numeric(base.get("Valor esperado %", 0), errors="coerce")
    base["Vantagem no fechamento %"] = pd.to_numeric(base.get("Vantagem no fechamento %", 0), errors="coerce")

    fechadas = base[base["Status"].astype(str).isin(["Green", "Red", "Void", "Cashout"])].copy()
    pendentes = base[base["Status"].astype(str) == "Pendente"].copy()

    lucro_total = float(base["Resultado R$"].sum())
    total_entradas = int(len(base))
    total_fechadas = int(len(fechadas))
    valor_total_apostado = float(fechadas["Entrada R$"].sum()) if total_fechadas else 0.0
    retorno_percentual = (lucro_total / valor_total_apostado * 100.0) if valor_total_apostado > 0 else 0.0
    banca_final = float(banca_inicial + lucro_total)
    acertos = int((fechadas["Status"].astype(str) == "Green").sum()) if total_fechadas else 0
    reds = int((fechadas["Status"].astype(str) == "Red").sum()) if total_fechadas else 0
    anuladas = int((fechadas["Status"].astype(str) == "Void").sum()) if total_fechadas else 0
    taxa_acerto = (acertos / max(1, acertos + reds) * 100.0) if total_fechadas else 0.0
    vantagem_media = float(fechadas["Vantagem no fechamento %"].dropna().mean()) if not fechadas.empty else 0.0

    resumo = pd.DataFrame([
        {"Indicador": "Banca inicial", "Valor": banca_inicial},
        {"Indicador": "Banca atual pela auditoria", "Valor": banca_final},
        {"Indicador": "Resultado total R$", "Valor": lucro_total},
        {"Indicador": "Entradas registradas", "Valor": total_entradas},
        {"Indicador": "Entradas fechadas", "Valor": total_fechadas},
        {"Indicador": "Entradas pendentes", "Valor": int(len(pendentes))},
        {"Indicador": "Greens", "Valor": acertos},
        {"Indicador": "Reds", "Valor": reds},
        {"Indicador": "Anuladas", "Valor": anuladas},
        {"Indicador": "Taxa de acerto %", "Valor": round(taxa_acerto, 2)},
        {"Indicador": "Total apostado em entradas fechadas", "Valor": round(valor_total_apostado, 2)},
        {"Indicador": "Retorno sobre valor apostado %", "Valor": round(retorno_percentual, 2)},
        {"Indicador": "Vantagem média no fechamento %", "Valor": round(vantagem_media, 2)},
    ])

    abas = {"Historico": base, "Resumo": resumo}

    for coluna, aba in [
        ("Mercado", "Por mercado"),
        ("Liga", "Por liga"),
        ("Casa de apostas", "Por casa"),
    ]:
        if coluna in fechadas.columns and not fechadas.empty:
            agrupado = (
                fechadas.groupby(coluna, dropna=False)
                .agg(
                    Entradas=("ID", "count"),
                    Total_apostado=("Entrada R$", "sum"),
                    Resultado=("Resultado R$", "sum"),
                    Valor_esperado_medio=("Valor esperado %", "mean"),
                    Vantagem_fechamento_media=("Vantagem no fechamento %", "mean"),
                )
                .reset_index()
            )
            agrupado["Retorno_%"] = np.where(
                agrupado["Total_apostado"] > 0,
                agrupado["Resultado"] / agrupado["Total_apostado"] * 100.0,
                0.0,
            )
            abas[aba] = agrupado.round(2)

    if not pendentes.empty:
        abas["Pendentes"] = pendentes

    return gerar_excel_simples(abas)


CALENDARIO_LIGAS = [
    {
        "Liga": "Brasileirão Série A",
        "Jan": "fora/consultar", "Fev": "fora/consultar", "Mar": "início provável", "Abr": "jogos", "Mai": "jogos", "Jun": "pausa Copa/consultar", "Jul": "retoma/consultar", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "encerra/consultar",
        "Observação": "Use somente Brasileirão Série A. Não misture estaduais, Copa do Brasil, Série B ou Sub-20. Em 2026, confira a pausa da Copa e a tabela real antes de analisar.",
    },
    {
        "Liga": "Argentina - Primera Division",
        "Jan": "início", "Fev": "jogos", "Mar": "jogos", "Abr": "jogos", "Mai": "jogos", "Jun": "consultar Copa", "Jul": "consultar/retoma", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "encerra",
        "Observação": "Use somente Liga Profesional/Primera División principal. Cuidado com Copa Argentina, Primera Nacional, reservas e fases de mata-mata.",
    },
    {
        "Liga": "EUA - MLS",
        "Jan": "fora", "Fev": "início", "Mar": "jogos", "Abr": "jogos", "Mai": "pausa após 25/05", "Jun": "pausa Copa", "Jul": "retoma após 16/07", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "playoffs", "Dez": "playoffs/consultar",
        "Observação": "Use somente MLS principal. NÃO use MLS Next Pro, times II, reservas ou sub-23; esses jogos são outra competição.",
    },
    {
        "Liga": "México - Liga MX",
        "Jan": "Clausura", "Fev": "Clausura", "Mar": "Clausura", "Abr": "Clausura", "Mai": "mata-mata", "Jun": "pausa", "Jul": "Apertura/início", "Ago": "Apertura", "Set": "Apertura", "Out": "Apertura", "Nov": "mata-mata", "Dez": "mata-mata/consultar",
        "Observação": "Use somente Liga MX principal. Não confundir com Liga de Expansión, Sub-23 ou amistosos.",
    },
    {
        "Liga": "Japão - J1 League",
        "Jan": "fora", "Fev": "temporada especial", "Mar": "temporada especial", "Abr": "temporada especial", "Mai": "temporada especial", "Jun": "fim especial/consultar", "Jul": "pausa", "Ago": "nova temporada", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente J1. Em 2026 há transição de calendário: temporada especial no 1º semestre e J1 2026/27 a partir de agosto. Não misture J2/J3, Copa da Liga ou Copa do Imperador.",
    },
    {
        "Liga": "China - Super League",
        "Jan": "fora", "Fev": "fora/consultar", "Mar": "início", "Abr": "jogos", "Mai": "jogos", "Jun": "jogos/consultar", "Jul": "jogos/consultar", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "encerra", "Dez": "fora",
        "Observação": "Use somente Chinese Super League. Não misture China League One, FA Cup ou torneios sub-21. Sempre confirme jogos reais na casa/API.",
    },
    {
        "Liga": "Suécia - Allsvenskan",
        "Jan": "fora", "Fev": "fora", "Mar": "fora/consultar", "Abr": "início", "Mai": "jogos", "Jun": "pausa/sem jogos elite", "Jul": "retoma início de julho", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "encerra", "Dez": "fora",
        "Observação": "Allsvenskan é a elite sueca. NÃO confundir com 'Suécia - 1ª Div' das casas, que geralmente é Ettan/Division 1, terceira divisão e fora da base do app.",
    },
    {
        "Liga": "Noruega - Eliteserien",
        "Jan": "fora", "Fev": "fora", "Mar": "início", "Abr": "jogos", "Mai": "jogos", "Jun": "pausa/consultar", "Jul": "retoma/jogos", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "jogos", "Dez": "encerra",
        "Observação": "Use somente Eliteserien. Não misture OBOS-ligaen, copa ou reservas. Em 2026, confira pausas de Copa e jogos adiados.",
    },
    {
        "Liga": "Finlândia - Veikkausliiga",
        "Jan": "fora", "Fev": "fora", "Mar": "fora/consultar", "Abr": "início", "Mai": "jogos", "Jun": "jogos", "Jul": "jogos", "Ago": "jogos", "Set": "fase final/consultar", "Out": "fase final/consultar", "Nov": "encerra", "Dez": "fora",
        "Observação": "Use somente Veikkausliiga. Não misture Ykkösliiga/Ykkönen, Copa da Finlândia ou amistosos.",
    },
    {
        "Liga": "Irlanda - Premier Division",
        "Jan": "fora/supercopa", "Fev": "início", "Mar": "jogos", "Abr": "jogos", "Mai": "jogos", "Jun": "jogos/consultar", "Jul": "jogos/consultar", "Ago": "jogos", "Set": "jogos", "Out": "jogos", "Nov": "encerra", "Dez": "fora",
        "Observação": "Use somente League of Ireland Premier Division. Não misture First Division, FAI Cup ou amistosos.",
    },
    {
        "Liga": "Inglaterra - Premier League",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "25/26 encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 22/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente Premier League. Não misture FA Cup, EFL Cup ou amistosos de pré-temporada. A temporada 26/27 começa em 22/08.",
    },
    {
        "Liga": "Inglaterra - Championship",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "playoffs/encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 14-16/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente Championship. Não misture League One, League Two, Carabao Cup ou amistosos.",
    },
    {
        "Liga": "Espanha - La Liga",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início/consultar", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente La Liga. Não misture Copa del Rey, Segunda ou amistosos. Mercado costuma ser eficiente; exigir preço bom.",
    },
    {
        "Liga": "Espanha - Segunda Divisão",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "jogos", "Jun": "playoffs/consultar", "Jul": "pausa", "Ago": "início/consultar", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente Segunda División/LaLiga Hypermotion. Não misture Primera RFEF. Muitos jogos são truncados; olhar mercados de gols com cautela.",
    },
    {
        "Liga": "Itália - Série A",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 22-23/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos/pausa natal",
        "Observação": "Use somente Serie A. Não misture Coppa Italia, Serie B ou amistosos.",
    },
    {
        "Liga": "Itália - Série B",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "playoffs/encerra", "Jun": "playoffs/consultar", "Jul": "pausa", "Ago": "início/consultar", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente Serie B. Cuidado com playoffs/playouts e variação grande de elencos.",
    },
    {
        "Liga": "Alemanha - Bundesliga",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 28/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos/pausa",
        "Observação": "Use somente Bundesliga. Não misture 2. Bundesliga, DFB-Pokal ou amistosos.",
    },
    {
        "Liga": "Alemanha - 2. Bundesliga",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 07/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos/pausa",
        "Observação": "Use somente 2. Bundesliga. Ela começa antes da Bundesliga em 2026/27; confirme sempre se é liga, não copa.",
    },
    {
        "Liga": "França - Ligue 1",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 23/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "até 13/12",
        "Observação": "Use somente Ligue 1. Não misture Ligue 2, Coupe de France ou amistosos. Em 26/27 há pausa no fim de dezembro.",
    },
    {
        "Liga": "Portugal - Primeira Liga",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 09/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente Primeira Liga/Liga Portugal Betclic. Não misture Liga Portugal 2, Taça ou amistosos.",
    },
    {
        "Liga": "Holanda - Eredivisie",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 07-09/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos/pausa",
        "Observação": "Use somente Eredivisie. Não misture Eerste Divisie, KNVB Cup ou amistosos. Boa liga para mercados de gols, mas audite.",
    },
    {
        "Liga": "Bélgica - Pro League",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa/consultar", "Ago": "início 07/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente Belgian/Jupiler Pro League principal. Não misture Challenger Pro League, playoffs antigos, copa ou reservas.",
    },
    {
        "Liga": "Turquia - Super Lig",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "25/26 jogos", "Abr": "25/26 jogos", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 14/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente Süper Lig principal. Não misture 1. Lig turca, copa ou amistosos. Atenção a mando forte e elencos instáveis.",
    },
    {
        "Liga": "Grécia - Super League",
        "Jan": "25/26 jogos", "Fev": "25/26 jogos", "Mar": "fase final/consultar", "Abr": "fase final/consultar", "Mai": "encerra", "Jun": "pausa", "Jul": "pausa", "Ago": "início 22/08", "Set": "26/27 jogos", "Out": "jogos", "Nov": "jogos", "Dez": "jogos",
        "Observação": "Use somente Super League Greece 1. Não misture Super League 2, copa ou amistosos. Atenção a formato com playoffs/playouts.",
    },
]

LIGAS_NAO_COBERTAS = [
    "Suécia - Division 1 / Ettan Norra / Ettan Södra: aparece como 'Suécia - 1ª Div' em algumas casas, mas NÃO é Allsvenskan.",
    "EUA - MLS Next Pro / times II / reservas: Vancouver Whitecaps II, Portland Timbers II, Tacoma Defiance, Real Monarchs etc.",
    "Brasil: estaduais, Série B, Série C, Copa do Brasil, Sub-20 ou feminino.",
    "Argentina: Primera Nacional, Copa Argentina, reservas ou torneios regionais.",
    "México: Liga de Expansión, Sub-23, feminino ou amistosos.",
    "Japão: J2, J3, Copa da Liga, Copa do Imperador e amistosos.",
    "China: China League One/Two, FA Cup e sub-21.",
    "Noruega: OBOS-ligaen, Copa da Noruega ou reservas.",
    "Finlândia: Ykkösliiga/Ykkönen, Copa da Finlândia ou amistosos.",
    "Irlanda: First Division, FAI Cup, Setanta/amistosos.",
    "Inglaterra: FA Cup, EFL Cup, League One, League Two, National League e amistosos.",
    "Espanha: Copa del Rey, Primera RFEF e amistosos.",
    "Itália: Coppa Italia, Serie C, Primavera e amistosos.",
    "Alemanha: DFB-Pokal, 3. Liga, Regionalliga e amistosos.",
    "França: Ligue 2, Coupe de France, National e amistosos.",
    "Portugal: Liga Portugal 2, Taça de Portugal, Liga 3 e amistosos.",
    "Holanda: Eerste Divisie, KNVB Cup e amistosos.",
    "Bélgica: Challenger Pro League, copa, reservas e amistosos.",
    "Turquia: 1. Lig, copa e amistosos.",
    "Grécia: Super League 2, copa e amistosos.",
]


# ============================================================
# CARD VISUAL
# ============================================================

def render_card(resultado: Dict[str, object], banca: float, time_casa: str, time_fora: str) -> None:
    mercado = str(resultado["mercado"])
    nome_mercado = mercado.replace("Vitória Casa", f"Vitória {time_casa}").replace("Vitória Fora", f"Vitória {time_fora}")

    nivel = str(resultado["nivel"])
    apostar = bool(resultado["apostar"])
    percentual = float(resultado["percentual"])

    if apostar and nivel == "forte":
        classe = "card-forte"
        titulo = f"✅ APOSTAR {percentual*100:.2f}% DA BANCA".replace(".", ",")
        cor = "ok"
    elif apostar and nivel == "boa":
        classe = "card-boa"
        titulo = f"🟡 APOSTAR {percentual*100:.2f}% DA BANCA".replace(".", ",")
        cor = "warn"
    elif apostar and nivel == "leve":
        classe = "card-leve"
        titulo = f"🔵 APOSTAR {percentual*100:.2f}% DA BANCA".replace(".", ",")
        cor = "blue"
    else:
        classe = "card-nao"
        titulo = "❌ NÃO APOSTAR"
        cor = "bad"

    odd_justa_txt = "-" if not np.isfinite(float(resultado["odd_justa"])) else numero(float(resultado["odd_justa"]), 2)

    st.markdown(
        f"""
        <div class="card-aposta {classe}">
            <div class="titulo-card {cor}">{titulo}</div>
            <div class="mercado-card">{nome_mercado}</div>
            <div class="linha-info"><b>Cotação da casa:</b> {numero(float(resultado['odd']), 2)}</div>
            <div class="linha-info"><b>Cotação justa:</b> {odd_justa_txt}</div>
            <div class="linha-info"><b>Chance pelo sistema:</b> {porcentagem(float(resultado['probabilidade']), 1)}</div>
            <div class="linha-info"><b>Valor esperado:</b> {porcentagem(float(resultado['valor']), 1)}</div>
            <div class="linha-info"><b>Entrada sugerida:</b> {dinheiro(float(resultado['entrada_rs']))}</div>
            <div class="mini"><b>Motivo:</b> {resultado['motivo']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# APP
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-topo">
            <span class="hero-selo">VISUAL LIMPO</span>
            <span class="hero-selo">CLARO E LEGÍVEL</span>
        </div>
        <div class="hero-titulo">TEX STATISTICS</div>
        <div class="hero-sub">Sistema com interface clara, limpa e profissional, sem fundo azul escuro ofuscando os textos. A leitura fica estável tanto no computador quanto no celular, mesmo quando o aparelho está em modo escuro.</div>
        <div class="hero-chip-wrap">
            <span class="hero-chip">Motor preservado</span>
            <span class="hero-chip">Auditoria preservada</span>
            <span class="hero-chip">Banca preservada</span>
            <span class="hero-chip">Odds preservadas</span>
            <span class="hero-chip">Calendário preservado</span>
        </div>
    </div>
    <div class="painel-resumo">
        <div class="resumo-card"><div class="resumo-label">Visual</div><div class="resumo-valor">Claro, limpo e sem poluição</div></div>
        <div class="resumo-card"><div class="resumo-label">Leitura</div><div class="resumo-valor">Contraste forte no celular</div></div>
        <div class="resumo-card"><div class="resumo-label">Decisão</div><div class="resumo-valor">APOSTAR / NÃO APOSTAR em destaque</div></div>
        <div class="resumo-card"><div class="resumo-label">Base</div><div class="resumo-valor">Mesma lógica do motor</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Banca")
    banca_inicial = st.number_input("Banca inicial da auditoria", min_value=0.0, value=1000.0, step=50.0)
    auditoria_sidebar = carregar_auditoria()
    banca_auditada = banca_atual_auditada(banca_inicial, auditoria_sidebar)
    usar_banca_auditada = st.checkbox("Usar banca calculada pela auditoria", value=True)
    banca_manual = st.number_input("Banca manual", min_value=0.0, value=1000.0, step=50.0)
    banca_usada = banca_auditada if usar_banca_auditada else banca_manual
    st.metric("Banca usada pelo sistema", dinheiro(banca_usada))
    st.caption("A entrada máxima por aposta nunca passa de 3% da banca atual; o total no mesmo jogo também é limitado.")

    st.divider()
    st.header("Perfil")
    perfil = st.selectbox(
        "Como quer operar?",
        ["Volume controlado", "Conservador", "Agressivo com controle"],
        index=0,
        help="Volume controlado é o equilíbrio entre a versão antiga e a auditoria nova.",
    )
    limite_padrao_por_perfil = {
        "Conservador": 3.0,
        "Volume controlado": 4.5,
        "Agressivo com controle": 6.0,
    }
    st.caption(
        "O perfil muda os cortes de entrada e o limite total padrão do jogo. "
        "Conservador busca menos entradas; agressivo busca mais, sem passar de 3% por aposta."
    )
    limite_total_jogo_pct = st.slider(
        "Máximo total no mesmo jogo",
        min_value=1.0,
        max_value=9.0,
        value=limite_padrao_por_perfil.get(perfil, 4.5),
        step=0.5,
        key=f"limite_total_jogo_{perfil}",
        help="Proteção contra várias entradas dependentes do mesmo placar. No agressivo, o padrão sobe para permitir mais entradas no mesmo jogo.",
    ) / 100.0

    st.divider()
    st.header("Dados")
    liga_sel = st.selectbox("Liga", list(LIGAS_CSV.keys()))

    perfil_janela = st.selectbox(
        "Janela histórica do modelo",
        [
            "Atual/agressivo — 380 jogos",
            "Equilibrado — 500 jogos",
            "Estável — 760 jogos",
            "Histórico longo — 1500 jogos",
        ],
        index=1,
        help="Define quantos jogos recentes da liga entram no cálculo. O banco de odds/auditoria não é alterado por essa configuração.",
    )
    config_janela = {
        "Atual/agressivo — 380 jogos": {"jogos": 380, "peso": -2.80, "descricao": "mais sensível à fase recente"},
        "Equilibrado — 500 jogos": {"jogos": 500, "peso": -2.60, "descricao": "padrão recomendado para operar"},
        "Estável — 760 jogos": {"jogos": 760, "peso": -2.20, "descricao": "mais estabilidade, menos sensibilidade"},
        "Histórico longo — 1500 jogos": {"jogos": 1500, "peso": -1.25, "descricao": "modo antigo/estudo, com mais histórico"},
    }
    janela_cfg = config_janela.get(perfil_janela, config_janela["Equilibrado — 500 jogos"])
    jogos_historicos_modelo = int(janela_cfg["jogos"])
    peso_inicial_modelo = float(janela_cfg["peso"])
    st.caption(
        f"Usando os últimos {jogos_historicos_modelo} jogos da liga. "
        f"Peso do jogo mais antigo: {np.exp(peso_inicial_modelo):.1%}. "
        f"Perfil: {janela_cfg['descricao']}."
    )

    chave_api = st.text_input("Chave da API de cotações", value=os.getenv("ODDS_API_KEY", ""), type="password")

    st.divider()
    st.header("Casa de apostas")
    casa_apostas = st.selectbox("Onde você vai apostar?", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"])

aba_analisar, aba_catalogo, aba_auditoria, aba_calendario = st.tabs(["🎯 Analisar jogo", "📊 Catálogo de odds", "📒 Auditoria", "🗓️ Calendário das ligas"])

st.markdown("<div class='caixa-info'><strong>Leitura rápida:</strong> use a aba <strong>Analisar jogo</strong> para ver as oportunidades em blocos; a aba <strong>Catálogo de odds</strong> para guardar cotações manuais; a aba <strong>Auditoria</strong> para registrar e baixar resultados; e a aba <strong>Calendário das ligas</strong> para saber onde focar no mês.</div>", unsafe_allow_html=True)

# O calendário vem antes da análise para nunca depender de jogo selecionado.
with aba_calendario:
    st.subheader("Calendário e conferência de TODAS as ligas")
    st.error(
        "Correção importante: esta aba NÃO é uma lista oficial de jogos. "
        "Ela serve como mapa de ligas cobertas pelo app. Para saber se há jogo hoje, use a casa de apostas ou o botão de conferência pela API."
    )
    st.caption(
        "A regra principal é simples: só analise jogos da mesma liga que está na base do app. "
        "Se o time não aparece na lista da liga, não force por outro nome."
    )

    calendario_df = pd.DataFrame(CALENDARIO_LIGAS)

    st.markdown("### Conferir se existem jogos com cotações agora")
    st.caption(
        "Este botão consulta a The Odds API e mostra apenas ligas que retornarem partidas com cotações. "
        "Use com moderação, porque cada liga consultada pode consumir requisição da sua chave."
    )

    ligas_para_checar = st.multiselect(
        "Ligas para consultar agora",
        list(LIGAS_API.keys()),
        default=[liga_sel] if liga_sel in LIGAS_API else [],
    )

    if st.button("VERIFICAR JOGOS DISPONÍVEIS AGORA"):
        if not chave_api:
            st.warning("Informe a chave da API na barra lateral para conferir jogos disponíveis.")
        elif not ligas_para_checar:
            st.warning("Escolha pelo menos uma liga para consultar.")
        else:
            encontrados = []
            sem_jogos = []
            agora_utc = pd.Timestamp.now(tz="UTC")

            for liga_nome in ligas_para_checar:
                dados_api = buscar_odds_api(chave_api, LIGAS_API[liga_nome])
                jogos_futuros = []
                for jogo in dados_api or []:
                    try:
                        inicio = pd.to_datetime(jogo.get("commence_time"), utc=True)
                        if inicio > agora_utc:
                            jogos_futuros.append({
                                "Liga": liga_nome,
                                "Jogo": f"{jogo.get('home_team', '')} x {jogo.get('away_team', '')}",
                                "Data/Hora": inicio.tz_convert("America/Sao_Paulo").strftime("%d/%m %H:%M"),
                            })
                    except Exception:
                        continue

                if jogos_futuros:
                    encontrados.extend(jogos_futuros[:10])
                else:
                    sem_jogos.append(liga_nome)

            if encontrados:
                st.success(f"Encontrei {len(encontrados)} jogo(s) com cotações nas ligas consultadas.")
                st.dataframe(pd.DataFrame(encontrados), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma das ligas consultadas retornou jogo com cotação agora.")

            if sem_jogos:
                with st.expander("Ligas consultadas sem jogos/cotações agora"):
                    for liga_nome in sem_jogos:
                        st.write(f"- {liga_nome}")

    st.markdown("### Mapa mensal, com cuidado")
    st.warning(
        "O mapa abaixo foi revisado liga por liga. Mesmo assim, ele é um mapa operacional, não uma lista oficial de partidas. "
        "Em ano de Copa do Mundo e pausas internacionais, várias ligas param mesmo dentro do mês normal."
    )

    mes_atual = st.selectbox(
        "Escolha o mês para ver o mapa geral",
        ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
        index=datetime.now().month - 1,
    )

    ativas = calendario_df[calendario_df[mes_atual].astype(str).str.strip() != ""].copy()
    st.markdown(f"### Mapa geral em {mes_atual}")
    if ativas.empty:
        st.info("Nenhuma liga marcada para este mês no mapa geral do app.")
    else:
        for _, linha in ativas.iterrows():
            st.markdown(
                f"""
                <div class="card-aposta card-leve">
                    <div class="mercado-card">{linha['Liga']}</div>
                    <div class="linha-info"><b>Mapa do mês:</b> {linha[mes_atual]}</div>
                    <div class="linha-info"><b>Observação:</b> {linha['Observação']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Ligas que parecem parecidas, mas NÃO são cobertas")
    st.caption("Se aparecer uma dessas na casa, não use a base atual do app para analisar.")
    for item in LIGAS_NAO_COBERTAS:
        st.markdown(f"- ❌ {item}")

    with st.expander("Ver tabela completa do mapa"):
        st.dataframe(calendario_df, use_container_width=True, hide_index=True)

    st.markdown("### Como usar na prática")
    st.markdown(
        """
        - **Primeiro:** confira se a liga da casa é exatamente a liga coberta pelo app.
        - **Segundo:** se o time não aparece na lista do app, não force análise.
        - **Terceiro:** use o botão de conferência pela API para ver se há jogo real com cotação.
        - **Quarto:** nas 3 primeiras rodadas de uma liga, use valor simbólico ou espere formar amostra.
        - **Quinto:** depois da 6ª rodada, a leitura estatística tende a ficar mais confiável.
        """
    )

    csv_cal = calendario_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "BAIXAR MAPA DAS LIGAS EM CSV",
        data=csv_cal,
        file_name="mapa_ligas_tex_pro_15.csv",
        mime="text/csv",
    )

    excel_cal = gerar_excel_simples({"Mapa_ligas": calendario_df, "Nao_cobertas": pd.DataFrame({"Liga/competição": LIGAS_NAO_COBERTAS})})
    st.download_button(
        "BAIXAR MAPA DAS LIGAS EM EXCEL",
        data=excel_cal,
        file_name="mapa_ligas_tex_pro_15.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )




with aba_analisar:
    with st.spinner("Carregando dados históricos da liga..."):
        df = extrair_dados(LIGAS_CSV[liga_sel], jogos_historicos_modelo, peso_inicial_modelo)

    if df.empty:
        st.error("Não consegui carregar os dados históricos desta liga.")
        st.stop()

    times = sorted(df["Home"].dropna().unique().tolist())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Jogos históricos", len(df))
    col2.metric("Times", len(times))
    col3.metric("Gols casa", numero(np.average(df["HG"], weights=df["Peso"]), 2))
    col4.metric("Gols fora", numero(np.average(df["AG"], weights=df["Peso"]), 2))

    st.markdown("---")
    modo = st.radio("Escolha o modo de análise", ["Manual", "Automático pela API"], horizontal=True)

    odds: Dict[str, float] = {}
    time_casa = times[0]
    time_fora = times[min(1, len(times)-1)]
    jogo_nome = ""
    origem = modo

    botao_salvar_catalogo = False
    data_jogo_catalogo = date.today()
    hora_jogo_catalogo = ""

    if modo == "Manual":
        st.markdown("### Jogo")
        c1, c2 = st.columns(2)
        with c1:
            time_casa = st.selectbox("Mandante", times, key="time_casa_manual")
        with c2:
            time_fora = st.selectbox("Visitante", times, key="time_fora_manual")

        c1, c2 = st.columns(2)
        with c1:
            data_jogo_catalogo = st.date_input("Data do jogo/mercado", value=date.today(), key="data_jogo_catalogo_manual")
        with c2:
            hora_jogo_catalogo = st.text_input("Hora do jogo", value="", placeholder="ex: 15:45", key="hora_jogo_catalogo_manual")

        if time_casa == time_fora:
            st.warning("Mandante e visitante não podem ser o mesmo time. Altere um dos times para analisar. As outras abas continuam funcionando normalmente.")
            botao_analisar = False
        else:
            jogo_nome = f"{time_casa} x {time_fora}"
            odds = coletar_odds_manuais("manual")
            c1, c2 = st.columns(2)
            with c1:
                botao_analisar = st.button("ANALISAR JOGO MANUAL", type="primary")
            with c2:
                botao_salvar_catalogo = st.button("SALVAR ODDS NO CATÁLOGO")

            if botao_salvar_catalogo:
                if not odds:
                    st.error("Nenhuma cotação válida foi informada para salvar no catálogo.")
                else:
                    catalogo = carregar_catalogo_odds()
                    catalogo = registrar_odds_no_catalogo(
                        catalogo=catalogo,
                        liga=liga_sel,
                        jogo=jogo_nome,
                        time_casa=time_casa,
                        time_fora=time_fora,
                        casa_apostas=casa_apostas,
                        odds=odds,
                        banca=float(banca_usada),
                        perfil=perfil,
                        data_jogo=data_jogo_catalogo,
                        hora_jogo=hora_jogo_catalogo,
                        origem="Manual digitado",
                        observacao="Odds salvas antes/sem obrigação de apostar",
                    )
                    destino_catalogo = salvar_catalogo_odds(catalogo)
                    st.success(f"{len(odds)} cotação(ões) salvas no catálogo. Destino: {destino_catalogo}.")

    else:
        if not chave_api:
            st.warning("Informe a chave da API na barra lateral. Se a API não tiver jogo disponível, use o modo manual.")
            botao_analisar = False
        elif liga_sel not in LIGAS_API:
            st.warning("Esta liga não está mapeada na API. Use o modo manual.")
            botao_analisar = False
        else:
            with st.spinner("Buscando jogos na API..."):
                jogos_api = buscar_odds_api(chave_api, LIGAS_API[liga_sel])

            if not jogos_api:
                st.warning("API sem dados disponíveis para esta liga agora. Isso não significa que sua chave está errada. Pode não haver jogo aberto, mercado disponível ou cobertura para esta liga neste momento. Use o modo manual.")
                botao_analisar = False
            else:
                opcoes = {}
                agora = pd.Timestamp.now(tz="UTC")
                for jogo in jogos_api:
                    try:
                        inicio = pd.to_datetime(jogo.get("commence_time"), utc=True)
                        if inicio <= agora:
                            continue
                        horario = inicio.tz_convert("America/Sao_Paulo").strftime("%d/%m %H:%M")
                        label = f"{jogo.get('home_team')} x {jogo.get('away_team')} — {horario}"
                        opcoes[label] = jogo
                    except Exception:
                        continue

                if not opcoes:
                    st.warning("A API respondeu, mas não há partida pré-jogo disponível. Use o modo manual.")
                    botao_analisar = False
                else:
                    escolha = st.selectbox("Partida", list(opcoes.keys()))
                    jogo_api = opcoes[escolha]
                    time_casa = achar_time(jogo_api.get("home_team", ""), times)
                    time_fora = achar_time(jogo_api.get("away_team", ""), times)

                    c1, c2 = st.columns(2)
                    with c1:
                        time_casa = st.selectbox("Mandante na base", times, index=times.index(time_casa), key="time_casa_api")
                    with c2:
                        time_fora = st.selectbox("Visitante na base", times, index=times.index(time_fora), key="time_fora_api")

                    odds = extrair_odds_de_jogo_api(jogo_api)
                    jogo_nome = f"{time_casa} x {time_fora}"
                    st.info(f"Cotações reais encontradas: {len(odds)} mercado(s). Mercados de proteção só entram no automático se a API entregar esse tipo de cotação.")
                    botao_analisar = st.button("ANALISAR JOGO AUTOMÁTICO", type="primary")

    if botao_analisar and not odds:
        st.error("Nenhuma cotação válida foi informada ou encontrada.")

    if botao_analisar and odds:
        gols_casa, gols_fora, probabilidades, confianca, amostras = calcular_forcas_e_probabilidades(df, time_casa, time_fora)
        resultados = montar_resultados(probabilidades, odds, confianca, banca_usada, perfil, limite_total_jogo_pct)
        st.session_state["ultima_analise"] = {
            "id": str(pd.Timestamp.now().value),
            "liga": liga_sel,
            "jogo_nome": jogo_nome,
            "time_casa": time_casa,
            "time_fora": time_fora,
            "origem": origem,
            "casa_apostas": casa_apostas,
            "perfil": perfil,
            "banca_usada": float(banca_usada),
            "limite_total_jogo_pct": float(limite_total_jogo_pct),
            "gols_casa": float(gols_casa),
            "gols_fora": float(gols_fora),
            "confianca": float(confianca),
            "amostras": amostras,
            "resultados": resultados,
        }

    analise_atual = st.session_state.get("ultima_analise")

    if analise_atual:
        liga_analise = analise_atual["liga"]
        jogo_nome_analise = analise_atual["jogo_nome"]
        time_casa_analise = analise_atual["time_casa"]
        time_fora_analise = analise_atual["time_fora"]
        origem_analise = analise_atual["origem"]
        casa_apostas_analise = analise_atual["casa_apostas"]
        perfil_analise = analise_atual.get("perfil", "não registrado")
        banca_analise = float(analise_atual["banca_usada"])
        limite_analise = float(analise_atual["limite_total_jogo_pct"])
        gols_casa = float(analise_atual["gols_casa"])
        gols_fora = float(analise_atual["gols_fora"])
        confianca = float(analise_atual["confianca"])
        amostras = analise_atual["amostras"]
        resultados = analise_atual["resultados"]
        aprovadas = [r for r in resultados if r["apostar"]]

        st.markdown("---")
        st.subheader(f"Análise — {jogo_nome_analise}")
        st.caption(f"Resultado da última análise calculada no perfil: {perfil_analise}. Você pode marcar/desmarcar entradas abaixo sem a tela fechar.")
        if perfil_analise != perfil or abs(limite_analise - limite_total_jogo_pct) > 0.00001:
            st.warning(
                "Você mudou o perfil ou o limite total depois da última análise. "
                "Clique em ANALISAR JOGO novamente para o resultado mudar de verdade."
            )
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Força de gols casa", numero(gols_casa, 2))
        m2.metric("Força de gols fora", numero(gols_fora, 2))
        m3.metric("Confiança", f"{confianca:.1f}%".replace(".", ","))
        m4.metric("Entradas", len(aprovadas))
        m5.metric("Máximo no jogo", dinheiro(banca_analise * limite_analise))

        st.caption(f"Amostra: {time_casa_analise} em casa {amostras['casa']} jogos | {time_fora_analise} fora {amostras['fora']} jogos.")
        if amostras.get("amostra_fraca"):
            st.error(f"⚠️ {amostras.get('alerta')} O lado com menor amostra tem apenas {amostras.get('minima')} jogo(s). O app bloqueia entradas reais nesse cenário.")
        else:
            st.success(str(amostras.get("alerta", "Amostra suficiente para análise.")))

        if aprovadas:
            total_sugerido = sum(float(r["entrada_rs"]) for r in aprovadas)
            st.success(f"Foram encontradas {len(aprovadas)} entrada(s). Total sugerido se fizer todas: {dinheiro(total_sugerido)}.")
            if total_sugerido >= banca_analise * limite_analise * 0.99 and len(aprovadas) > 1:
                st.warning("As entradas aprovadas foram ajustadas para respeitar o limite total do mesmo jogo. Isso evita concentrar dinheiro demais em mercados que dependem do mesmo placar.")
        else:
            st.info("Nenhuma entrada passou. Se você quiser mais volume, use o perfil 'Agressivo com controle', mas registre tudo na auditoria.")

        st.markdown("### Blocos de decisão")
        for r in resultados:
            render_card(r, banca_analise, time_casa_analise, time_fora_analise)

        if aprovadas:
            st.markdown("---")
            st.markdown("### Registrar entradas aprovadas")
            st.caption("Marque somente as entradas que você realmente fez. Elas irão para a auditoria.")
            auditoria = carregar_auditoria()
            escolhidas = []
            analise_id = analise_atual.get("id", "ultima")

            with st.form(key=f"form_registrar_{analise_id}"):
                for i, r in enumerate(aprovadas):
                    nome = r["mercado"].replace("Vitória Casa", f"Vitória {time_casa_analise}").replace("Vitória Fora", f"Vitória {time_fora_analise}")
                    label = f"Registrar {nome} — {numero(r['odd'], 2)} — {dinheiro(r['entrada_rs'])}"
                    marcado = st.checkbox(label, value=True, key=f"reg_{analise_id}_{i}")
                    if marcado:
                        escolhidas.append(r)

                observacao = st.text_area(
                    "Observação para a auditoria",
                    value="",
                    placeholder="Ex: Pixbet, cotação conferida antes de apostar, escalação ok...",
                    key=f"obs_{analise_id}",
                )
                salvar_form = st.form_submit_button("SALVAR ENTRADAS MARCADAS NA AUDITORIA", type="primary")

            if salvar_form:
                if not escolhidas:
                    st.warning("Nenhuma entrada foi marcada para salvar.")
                else:
                    for r in escolhidas:
                        auditoria = registrar_entrada(
                            auditoria=auditoria,
                            liga=liga_analise,
                            jogo=jogo_nome_analise,
                            casa_apostas=casa_apostas_analise,
                            mercado=str(r["mercado"]),
                            odd=float(r["odd"]),
                            prob=float(r["probabilidade"]),
                            odd_justa=float(r["odd_justa"]),
                            valor=float(r["valor"]),
                            percentual=float(r["percentual"]),
                            entrada_rs=float(r["entrada_rs"]),
                            banca_antes=float(banca_analise),
                            origem=origem_analise,
                            observacao=observacao,
                        )
                    destino_auditoria = salvar_auditoria(auditoria)
                    st.success(f"Entradas salvas na auditoria. Destino: {destino_auditoria}.")

        if st.button("LIMPAR ÚLTIMA ANÁLISE"):
            st.session_state.pop("ultima_analise", None)
            st.rerun()


with aba_catalogo:
    st.subheader("Catálogo de odds")
    st.caption("Aqui ficam salvas as cotações que você digitou manualmente. O app registra horário, data, banca usada, casa de apostas, liga, jogo, mercado e odd.")

    cfg_google = obter_config_google_sheets()
    if cfg_google.get("configurado"):
        url_planilha = f"https://docs.google.com/spreadsheets/d/{cfg_google['spreadsheet_id']}"
        st.success(f"Catálogo permanente ativo no Google Sheets. Aba usada: {cfg_google['worksheet_catalogo']}.")
        st.markdown(f"[Abrir planilha no Google Sheets]({url_planilha})")
    else:
        st.warning("Google Sheets ainda não está configurado. Se salvar assim no Streamlit Cloud, o catálogo local pode sumir quando o app reiniciar.")

    catalogo = carregar_catalogo_odds()

    c1, c2, c3 = st.columns(3)
    c1.metric("Odds salvas", len(catalogo))
    c2.metric("Coletas", catalogo["ID Coleta"].nunique() if not catalogo.empty else 0)
    c3.metric("Casas", catalogo["Casa de apostas"].nunique() if not catalogo.empty else 0)

    if cfg_google.get("configurado"):
        local_existente = carregar_catalogo_odds_local()
        if not local_existente.empty and catalogo.empty:
            if st.button("MIGRAR BACKUP LOCAL PARA GOOGLE SHEETS"):
                destino_migracao = salvar_catalogo_odds(local_existente)
                st.success(f"Backup local migrado. Destino: {destino_migracao}.")
                st.rerun()

    if catalogo.empty:
        st.info("Ainda não há odds salvas. Vá na aba Analisar jogo, preencha as odds manuais e clique em SALVAR ODDS NO CATÁLOGO.")
    else:
        st.markdown("### Filtros")
        f1, f2, f3 = st.columns(3)
        with f1:
            filtro_casa = st.multiselect("Casa", sorted(catalogo["Casa de apostas"].dropna().unique().tolist()))
        with f2:
            filtro_liga = st.multiselect("Liga", sorted(catalogo["Liga"].dropna().unique().tolist()))
        with f3:
            filtro_jogo = st.text_input("Buscar jogo/time", value="", placeholder="Ex: Derry, Shamrock, Galway...")

        filtrado = catalogo.copy()
        if filtro_casa:
            filtrado = filtrado[filtrado["Casa de apostas"].isin(filtro_casa)]
        if filtro_liga:
            filtrado = filtrado[filtrado["Liga"].isin(filtro_liga)]
        if filtro_jogo.strip():
            termo = filtro_jogo.strip().lower()
            filtrado = filtrado[
                filtrado["Jogo"].astype(str).str.lower().str.contains(termo, na=False)
                | filtrado["Mandante"].astype(str).str.lower().str.contains(termo, na=False)
                | filtrado["Visitante"].astype(str).str.lower().str.contains(termo, na=False)
            ]

        st.markdown("### Histórico catalogado")
        st.dataframe(filtrado.tail(500), use_container_width=True, hide_index=True)

        st.markdown("### Últimas odds por mercado")
        ultimas = (
            filtrado.sort_values("Registrado em", kind="mergesort")
            .groupby(["Casa de apostas", "Liga", "Jogo", "Mercado", "Seleção"], dropna=False)
            .tail(1)
        )
        colunas_ultimas = [
            "Registrado em", "Casa de apostas", "Liga", "Jogo", "Data do jogo", "Hora do jogo",
            "Mercado", "Seleção", "Cotação", "Banca no momento", "Perfil"
        ]
        st.dataframe(ultimas[colunas_ultimas].tail(300), use_container_width=True, hide_index=True)

        csv_cat = filtrado.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "BAIXAR CATÁLOGO FILTRADO EM CSV",
            data=csv_cat,
            file_name="catalogo_odds_tex_pro_15.csv",
            mime="text/csv",
        )

        excel_cat = gerar_excel_catalogo_odds(filtrado)
        st.download_button(
            "BAIXAR CATÁLOGO EM EXCEL (.xlsx)",
            data=excel_cat,
            file_name="catalogo_odds_tex_pro_15.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        if google_sheets_configurado():
            st.caption("Fonte permanente: Google Sheets. O arquivo local é só backup temporário/download.")
        else:
            st.caption(f"Arquivo local atualizado automaticamente em: {ARQUIVO_CATALOGO_ODDS_XLSX}. Atenção: no Streamlit Cloud esse arquivo pode sumir ao reiniciar.")


with aba_auditoria:
    st.subheader("Auditoria operacional")
    st.caption("Aqui você acompanha banca, resultado e vantagem no fechamento.")

    cfg_google_aud = obter_config_google_sheets()
    if cfg_google_aud.get("configurado"):
        st.success(f"Auditoria permanente ativa no Google Sheets. Aba usada: {cfg_google_aud.get('worksheet_auditoria', GOOGLE_SHEETS_WORKSHEET_AUDITORIA_PADRAO)}.")
    else:
        st.warning("Auditoria em backup local temporário. Configure o Google Sheets para não perder entradas quando o Streamlit reiniciar.")

    auditoria = carregar_auditoria()
    banca_calc = banca_atual_auditada(banca_inicial, auditoria)

    c1, c2, c3 = st.columns(3)
    c1.metric("Banca inicial", dinheiro(banca_inicial))
    c2.metric("Banca auditada", dinheiro(banca_calc))
    lucro_total = banca_calc - banca_inicial
    c3.metric("Resultado total", dinheiro(lucro_total))

    st.markdown("---")
    st.markdown("### Lançar entrada manual na auditoria")
    with st.expander("Adicionar entrada que fiz fora do motor"):
        c1, c2 = st.columns(2)
        with c1:
            aud_liga = st.text_input("Liga", value=liga_sel, key="aud_liga")
            aud_jogo = st.text_input("Jogo", value="", placeholder="Ex: Botafogo x Santos", key="aud_jogo")
            aud_mercado = st.selectbox("Mercado", MERCADOS, key="aud_mercado")
            aud_casa = st.selectbox("Casa de apostas", ["Pixbet", "Pinnacle", "Bet365", "Betano", "Superbet", "KTO", "Outra"], key="aud_casa")
        with c2:
            aud_odd = st.text_input("Cotação de entrada", value="", key="aud_odd")
            aud_entrada = st.text_input("Valor da entrada em R$", value="", key="aud_entrada")
            aud_banca_antes = st.number_input("Banca antes", min_value=0.0, value=float(banca_calc), step=10.0, key="aud_banca_antes")
            aud_obs = st.text_input("Observação", value="", key="aud_obs")

        if st.button("SALVAR ENTRADA MANUAL"):
            odd = texto_para_float(aud_odd)
            entrada = texto_para_float(aud_entrada)
            if not odd_valida(odd) or entrada is None or entrada <= 0 or not aud_jogo.strip():
                st.error("Preencha jogo, cotação válida e valor da entrada.")
            else:
                percentual = entrada / aud_banca_antes if aud_banca_antes > 0 else 0.0
                auditoria = registrar_entrada(
                    auditoria=auditoria,
                    liga=aud_liga,
                    jogo=aud_jogo,
                    casa_apostas=aud_casa,
                    mercado=aud_mercado,
                    odd=float(odd),
                    prob=0.0,
                    odd_justa=0.0,
                    valor=0.0,
                    percentual=percentual,
                    entrada_rs=float(entrada),
                    banca_antes=float(aud_banca_antes),
                    origem="Manual livre",
                    observacao=aud_obs,
                )
                destino_auditoria = salvar_auditoria(auditoria)
                st.success(f"Entrada manual salva. Destino: {destino_auditoria}.")

    st.markdown("---")
    st.markdown("### Fechar resultado de uma entrada")
    if auditoria.empty:
        st.info("Ainda não há entradas registradas.")
    else:
        pendentes = auditoria[auditoria["Status"].astype(str) == "Pendente"].copy()
        if pendentes.empty:
            st.info("Não há entradas pendentes para fechar.")
        else:
            opcoes = []
            mapa = {}
            for idx, row in pendentes.iterrows():
                label = f"{row['ID']} — {row['Jogo']} — {row['Mercado']} — {row['Casa de apostas']} — {dinheiro(row['Entrada R$'])}"
                opcoes.append(label)
                mapa[label] = idx

            escolha = st.selectbox("Escolha a entrada", opcoes)
            idx = mapa[escolha]
            row = auditoria.loc[idx]

            c1, c2, c3 = st.columns(3)
            with c1:
                status = st.selectbox("Resultado", ["Green", "Red", "Void", "Cashout"], key="fechar_status")
            with c2:
                odd_fechamento_txt = st.text_input("Cotação de fechamento", value="", key="fechar_odd")
            with c3:
                valor_cashout = st.number_input("Valor recebido no cashout", min_value=0.0, value=0.0, step=1.0, key="fechar_cashout")

            obs_fechamento = st.text_input("Observação do fechamento", value="", key="fechar_obs")

            if st.button("FECHAR ENTRADA"):
                entrada_rs = float(row["Entrada R$"])
                odd_entrada = float(row["Cotação de entrada"])
                resultado_rs = calcular_resultado(status, entrada_rs, odd_entrada, valor_cashout)
                odd_fechamento = texto_para_float(odd_fechamento_txt)
                vantagem_fechamento = ""
                if odd_valida(odd_fechamento):
                    vantagem_fechamento = round(((odd_entrada / odd_fechamento) - 1.0) * 100.0, 2)

                banca_depois = float(row["Banca antes"]) + resultado_rs
                auditoria.loc[idx, "Status"] = status
                auditoria.loc[idx, "Resultado R$"] = round(resultado_rs, 2)
                auditoria.loc[idx, "Banca depois"] = round(banca_depois, 2)
                auditoria.loc[idx, "Cotação de fechamento"] = odd_fechamento if odd_fechamento is not None else ""
                auditoria.loc[idx, "Vantagem no fechamento %"] = vantagem_fechamento
                auditoria.loc[idx, "Observação"] = str(row.get("Observação", "")) + " | Fechamento: " + obs_fechamento
                destino_auditoria = salvar_auditoria(auditoria)
                st.success(f"Entrada fechada e auditoria atualizada. Destino: {destino_auditoria}.")

    st.markdown("---")
    st.markdown("### Histórico")
    auditoria = carregar_auditoria()
    if auditoria.empty:
        st.info("Nenhum registro ainda.")
    else:
        # Mostra tabela só na auditoria, não na tela principal
        st.dataframe(auditoria.tail(300), use_container_width=True, hide_index=True)
        csv = auditoria.to_csv(index=False).encode("utf-8-sig")
        st.download_button("BAIXAR AUDITORIA EM CSV", data=csv, file_name="auditoria_tex_pro_15.csv", mime="text/csv")

        excel_bytes = gerar_excel_auditoria(auditoria, banca_inicial)
        st.download_button(
            "BAIXAR AUDITORIA EM EXCEL (.xlsx)",
            data=excel_bytes,
            file_name="auditoria_tex_pro_15.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
