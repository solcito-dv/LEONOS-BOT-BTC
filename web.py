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

# --- 2. DISEÑO ESTRUCTURAL (FORCE CSS) ---
st.set_page_config(page_title="LEONOS BTC | V19", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Dashboard: Menos distancia entre columnas */
    [data-testid="column"] { padding: 0 4px !important; }

    /* Paneles Dorado Mate */
    .neon-panel { 
        border: 1px solid #B8860B; 
        border-radius: 8px; 
        background: #080808; 
        margin-bottom: 10px; 
    }
    
    .panel-header { 
        background: rgba(184, 134, 11, 0.1); 
        padding: 6px 12px; 
        border-bottom: 1px solid #B8860B; 
        color: #DAA520; 
        font-family: 'Orbitron'; 
        font-size: 11px; 
        text-transform: uppercase;
    }
    
    .panel-content { padding: 10px 12px; }
    .price-main { color: #FFFFFF; font-size: 28px; font-weight: 900; font-family: 'Orbitron'; }
    .sub-info { color: #FFFFFF !important; font-size: 11px; margin-top: 3px; }

    /* Situación Actual (Tamaño Normalizado y Fondo Página) */
    .status-box {
        border: 1px solid #333;
        background: #000000; /* Fondo igual a la página */
        color: #FFFFFF;
        padding: 10px;
        border-radius: 6px;
        text-align: center;
        text-transform: uppercase;
        font-weight: 700;
        font-size: 13px;
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    button[kind="header"] svg { fill: #DAA520 !important; } /* Flechita Amarilla */
    
    /* Forzar textos del sidebar a blanco */
    .stToggle label p, .stRadio label p, .stMarkdown p, .stWidgetLabel p { 
        color: #FFFFFF !important; 
        font-size: 13px !important; 
    }

    /* Historial Enmarcado y Acomodado */
    .hist-box {
        border: 1px solid #333;
        background: #050505;
        border-radius: 6px;
        padding: 12px;
        margin: 5px 0;
    }
    .hist-grid-header {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #DAA520; 
        font-weight: 900; 
        font-size: 11px; 
        border-bottom: 1px solid #444; 
        padding-bottom: 6px;
        margin-bottom: 6px;
    }
    .hist-grid-row {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #FFFFFF; 
        font-size: 12px; 
        padding: 5px 0; 
        border-bottom: 1px solid #1a1a1a;
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
        delta = df['close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet, exchange = fetch_all()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<p style="color:#DAA520; font-family:Orbitron; font-size:16px;">LEONOS CONTROL</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#DAA520; font-size:10px; font-weight:bold;">BTC NUBE</p>', unsafe_allow_html=True)
    
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    
    modo = st.radio("INTENSIDAD:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"])
    targets = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55, "Tendencia (0.90%)": 0.90}
    target_actual = targets[modo]
    
    st.markdown("---")
    st.write("• Servidor: Online")
    st.write("• Exchange: MEXC Global")

# CABECERA
st.markdown('<h1 style="font-family:Orbitron; color:#DAA520; margin-bottom:12px; font-size:24px;">🦁 LEONOS BTC <span style="font-weight:300; color:white;">V19</span></h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    # DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div class="sub-info">EMA200: ${ema200:,.1f}</div></div></div>', unsafe_allow_html=True)
    with c2: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI & ESTRATEGIA</div><div class="panel-content"><span class="price-main" style="color:#FFFFFF;">{rsi:.2f}</span><div class="sub-info">OBJETIVO: < 35</div></div></div>', unsafe_allow_html=True)
    with c3: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">DISPONIBLE</div><div class="panel-content"><span class="price-main" style="color:#DAA520;">${wallet:.2f}</span><div class="sub-info">USDT EN MEXC</div></div></div>', unsafe_allow_html=True)
    with c4: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div class="sub-info">PROFIT NETO</div></div></div>', unsafe_allow_html=True)

    log_msg = "Acechando entrada..."
    if not bot_encendido:
        log_msg = "SISTEMA EN PAUSA"
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
            tp = promedio * (1 + (target_actual / 100))
            
            st.markdown(f"""
                <div style="display: flex; gap: 8px; justify-content: center; margin-bottom: 10px;">
                    <div style="border: 1px solid #DAA520; color: #FFF; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight:bold;">BUY: ${promedio:,.1f}</div>
                    <div style="border: 1px solid #00FF88; color: #FFF; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight:bold;">TP: ${tp:,.1f}</div>
                </div>
            """, unsafe_allow_html=True)
            log_msg = f"POSICIÓN: {neta:.2f}% (META {target_actual}%)"

    # SITUACIÓN ACTUAL
    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-box">{log_msg}</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL DE OPERACIONES ENMARCADO
    st.markdown('<div class="neon-panel"><div class="panel-header">📜 HISTORIAL DE CAZA BTC</div><div class="panel-content">', unsafe_allow_html=True)
    st.markdown('<div class="hist-box">', unsafe_allow_html=True)
    st.markdown("""
        <div class="hist-grid-header">
            <div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>PROFIT</div>
        </div>
    """, unsafe_allow_html=True)
    
    if state["history"]:
        for op in reversed(state["history"][-8:]):
            color_p = "#00FF00" if "-" not in op["Neto"] else "#FF4444"
            st.markdown(f"""
                <div class="hist-grid-row">
                    <div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div>
                    <div style="color:{color_p}; font-weight:bold;">{op["Neto"]}</div>
                    <div style="color:{color_p};">{op["Profit"]}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<p style="text-align:center; color:#555; font-size:12px; padding:10px;">Esperando operaciones...</p>', unsafe_allow_html=True)
    
    st.markdown('</div></div></div>', unsafe_allow_html=True)

time.sleep(10)
st.rerun()