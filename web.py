import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN (LÓGICA SAGRADA) ---
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

# --- 2. DISEÑO Y ESTILOS (CELESTE FIRME Y DORADO) ---
st.set_page_config(page_title="LEONOS BTC | V19", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Paneles Dorados */
    .neon-panel { 
        border: 2px solid #B8860B; 
        border-radius: 12px; 
        background: #050505; 
        margin-bottom: 20px; 
        box-shadow: 0 0 15px rgba(184, 134, 11, 0.2); 
    }
    
    /* Cabeceras Estándar */
    .panel-header { 
        background: rgba(184, 134, 11, 0.1); 
        padding: 12px; 
        border-bottom: 1px solid #B8860B; 
        color: #FFFFFF !important; 
        font-family: 'Orbitron'; 
        font-size: 14px; 
        text-transform: uppercase;
        font-weight: 900;
    }

    /* CELESTE FIRME (DEEP SKY BLUE) PARA TÍTULOS E INFO */
    .header-celeste { 
        color: #00BFFF !important; 
        padding: 12px;
        font-family: 'Orbitron'; 
        font-size: 14px; 
        text-transform: uppercase;
        font-weight: 900;
        border-bottom: none !important; /* Eliminada la línea de abajo del título */
    }
    
    .sub-info-celeste { color: #00BFFF !important; font-size: 12px; margin-top: 5px; font-weight: 800; }
    
    .panel-content { padding: 20px; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    
    /* Estado con borde lateral celeste */
    .status-msg { 
        color: #FFFFFF; 
        font-style: italic; 
        font-size: 15px; 
        border-left: 4px solid #00BFFF; 
        padding-left: 15px; 
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    .stWidgetLabel p, label { color: #FFFFFF !important; }
    .sidebar-info { color: #00FF00; font-size: 12px; font-family: 'JetBrains Mono'; margin-top: 10px; }

    /* Historial Cabezales Blancos */
    .hist-header-row {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #FFFFFF; 
        font-weight: bold; 
        border-bottom: 1px solid #333; 
        padding-bottom: 8px; 
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MOTOR DE DATOS ---
def fetch_all():
    try:
        mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet, exchange = fetch_all()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<p style="color:#DAA520; font-family:Orbitron; font-size:18px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    st.markdown('<p style="color:#DAA520; font-size:12px; font-weight:bold;">ESTADO DE LA NUBE</p>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-info">● SERVIDOR: OPERATIVO</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-info">● EXCHANGE: MEXC CONNECTED</div>', unsafe_allow_html=True)
    st.markdown("---")
    modo = st.radio("INTENSIDAD:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"])
    target_actual = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55, "Tendencia (0.90%)": 0.90}[modo]

st.markdown('<h1 style="font-family:Orbitron; color:#DAA520; margin-bottom:20px;">🦁 LEONOS BTC V19</h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    # DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div class="sub-info-celeste">EMA200: ${ema200:,.0f}</div></div></div>', unsafe_allow_html=True)
    with c2: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI ACTUAL</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div class="sub-info-celeste">OBJETIVO: < 35</div></div></div>', unsafe_allow_html=True)
    with c3: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">BILLETERA USDT</div><div class="panel-content"><span class="price-main" style="color:#DAA520;">${wallet:.2f}</span><div style="color: #DAA520; font-size: 12px; margin-top: 5px;">DISPONIBLE</div></div></div>', unsafe_allow_html=True)
    with c4: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div style="color: #00FF00; font-size: 12px; margin-top: 5px;">TOTAL ACUMULADO</div></div></div>', unsafe_allow_html=True)

    log_msg = "Acechando entrada..."
    if not bot_encendido: log_msg = "SISTEMA EN PAUSA MANUAL"
    else:
        if not state["in_position"]:
            if rsi < 35 and wallet >= MONTO_OPERACION: 
                try:
                    exchange.create_limit_buy_order(SYMBOL, MONTO_OPERACION / price, price)
                    state.update({"in_position": True, "compras": [price], "monto_total": MONTO_OPERACION})
                    save_state(state)
                except: pass
        else:
            promedio = state["compras"][0]
            neta = ((price - promedio) / promedio) * 100
            if neta >= target_actual or neta <= -2.5:
                try:
                    exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / promedio, price)
                    prof = (state['monto_total'] * neta / 100)
                    state["history"].append({"Fecha": datetime.now().strftime("%H:%M"), "Entrada": f"${promedio:,.0f}", "Salida": f"${price:,.0f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"})
                    state["pnl_acumulado"] += prof
                    state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                    save_state(state)
                except: pass
            else: log_msg = f"DENTRO DEL MERCADO: {neta:.2f}% (Buscando {target_actual}%)"

    # SITUACIÓN ACTUAL
    st.markdown(f'<div class="neon-panel"><div class="header-celeste">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL
    hist_header = '<div class="hist-header-row"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>PROFIT</div></div>'
    hist_body = ""
    if state["history"]:
        for op in reversed(state["history"][-10:]):
            color_p = "#00FF00" if "-" not in op["Neto"] else "#FF4444"
            hist_body += f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; padding: 10px 0; border-bottom: 1px solid #222; color: white; font-size: 13px;"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div style="color:{color_p}; font-weight:bold;">{op["Neto"]}</div><div style="color:{color_p};">{op["Profit"]}</div></div>'
    
    st.markdown(f'<div class="neon-panel"><div class="header-celeste">📜 ÚLTIMAS OPERACIONES BTC</div><div class="panel-content">{hist_header}{hist_body}</div></div>', unsafe_allow_html=True)

time.sleep(15)
st.rerun()