import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
API_KEY_BTC = 'mx0vglJcyb3BIWHjDk' 
SECRET_KEY_BTC = 'de1285d2de1945d2a66e502945c7324b'
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json'
MONTO_OPERACION = 10.0

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if "pnl_acumulado" not in state: state["pnl_acumulado"] = 0.0
                return state
        except: pass
    return {"in_position": False, "compras": [], "monto_total": 0.0, "history": [], "pnl_acumulado": 0.0}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

# --- 2. DISEÑO FINAL (ESTILO SOL) ---
st.set_page_config(page_title="LEONOS BTC | V19", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Espaciado de columnas */
    [data-testid="column"] { padding: 0 10px !important; }

    /* Paneles Estilo Referencia */
    .neon-panel { 
        border: 2px solid #B8860B; 
        border-radius: 12px; 
        background: #050505; 
        margin-bottom: 20px; 
        box-shadow: 0 0 10px rgba(184, 134, 11, 0.2);
    }
    
    .panel-header { 
        background: rgba(184, 134, 11, 0.2); 
        padding: 12px; 
        border-bottom: 1px solid #B8860B; 
        color: #DAA520; 
        font-family: 'Orbitron'; 
        font-size: 14px; 
        text-transform: uppercase;
    }
    
    .panel-content { padding: 20px; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1.1; }
    
    /* Situación Actual (Compacta) */
    .status-msg { 
        color: #DAA520; 
        font-style: italic; 
        font-size: 15px; 
        border-left: 4px solid #B8860B; 
        padding-left: 15px; 
    }

    /* Sidebar Forzado Blanco */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    .stToggle label p, .stRadio label p, .stMarkdown p, .stWidgetLabel p { 
        color: #FFFFFF !important; 
        font-size: 14px !important; 
    }

    /* Grid del Historial (Exacto al ejemplo) */
    .hist-header {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #DAA520; 
        font-weight: bold; 
        border-bottom: 1px solid #B8860B; 
        padding-bottom: 8px;
        font-size: 13px;
    }
    .hist-row {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        padding: 10px 0; 
        border-bottom: 1px solid #333; 
        color: white;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

state = load_state()
data, wallet, exchange = fetch_all()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<p style="color:#DAA520; font-family:Orbitron; font-size:18px;">LEONOS BTC</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    modo = st.radio("INTENSIDAD:", ["Scalper (0.35%)", "Equilibrado (0.55%)"])
    target_actual = 0.35 if "Scalper" in modo else 0.55

# --- DASHBOARD ---
st.markdown('<h1 style="font-family:Orbitron; color:#DAA520; margin-bottom:20px;">🦁 LEONOS BTC V19</h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><br><small>EMA: {ema200:,.0f}</small></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI ACTUAL</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><br><small>OBJETIVO: < 35</small></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">BILLETERA USDT</div><div class="panel-content"><span class="price-main" style="color:#DAA520;">${wallet:.2f}</span><br><small>DISPONIBLE</small></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><br><small>TOTAL</small></div></div>', unsafe_allow_html=True)

    log_msg = "Acechando..."
    # (Lógica de trading igual...)

    # SITUACIÓN ACTUAL
    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL FINAL (Grilla Limpia)
    hist_html = '<div class="hist-header"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>GANANCIA</div></div>'
    for op in reversed(state["history"][-10:]):
        hist_html += f'<div class="hist-row"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div>{op["Neto"]}</div><div>{op["Profit"]}</div></div>'
    
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMAS OPERACIONES</div><div class="panel-content">{hist_html}</div></div>', unsafe_allow_html=True)

time.sleep(10)
st.rerun()