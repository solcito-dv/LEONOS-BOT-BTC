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

# --- 2. DISEÑO CUSTOM (V19 PROPORTIONAL) ---
st.set_page_config(page_title="LEONOS BTC | V19", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Espaciado general de columnas */
    [data-testid="column"] { padding: 0 5px !important; }

    /* Paneles Dorado Mate */
    .neon-panel { 
        border: 1px solid #B8860B; 
        border-radius: 8px; 
        background: #080808; 
        margin-bottom: 15px; /* Menos distancia entre recuadros */
        overflow: hidden;
    }
    
    .panel-header { 
        background: rgba(184, 134, 11, 0.15); 
        padding: 8px 15px; 
        border-bottom: 1px solid #B8860B; 
        color: #DAA520; 
        font-family: 'Orbitron'; 
        font-size: 12px; 
        text-transform: uppercase;
    }
    
    .panel-content { padding: 12px 15px; }
    .price-main { color: #FFFFFF; font-size: 32px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    .sub-info { color: #FFFFFF !important; font-size: 11px; margin-top: 4px; font-weight: 500; }

    /* Situación Actual (Tamaño Normalizado) */
    .status-box {
        border: 1px solid #333;
        background: #050505;
        color: #FFF;
        padding: 12px;
        border-radius: 6px;
        text-align: center;
        text-transform: uppercase;
        font-weight: 700;
        font-size: 15px;
        letter-spacing: 1px;
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    .sidebar-title { color: #DAA520; font-family: 'Orbitron'; font-size: 18px; }
    .stToggle label p, .stRadio label p, .stMarkdown p { 
        color: #FFFFFF !important; 
        font-size: 13px !important; 
        font-weight: 500 !important; 
    }

    /* Grid del Historial (Compacto y enmarcado) */
    .hist-container {
        border: 1px solid #333;
        border-radius: 6px;
        padding: 10px;
        background: #050505;
    }
    .hist-grid-header {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #DAA520; 
        font-weight: 900; 
        font-size: 12px; 
        border-bottom: 1px solid #333; 
        padding-bottom: 8px;
        margin-bottom: 8px;
    }
    .hist-grid-row {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #FFFFFF; 
        font-size: 13px; 
        padding: 6px 0; 
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
    st.markdown('<p class="sidebar-title">LEONOS CONTROL</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#DAA520; font-size:10px; font-weight:bold;">SISTEMA BTC V19</p>', unsafe_allow_html=True)
    
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    
    modo = st.radio("INTENSIDAD DE SALIDA:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"])
    targets = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55, "Tendencia (0.90%)": 0.90}
    target_actual = targets[modo]
    
    st.markdown("---")
    st.write("• Servidor: Online")
    st.write("• Exchange: MEXC Global")

# CABECERA
st.markdown('<h1 style="font-family:Orbitron; color:#DAA520; margin-bottom:15px; font-size:28px;">🦁 LEONOS BTC <span style="font-weight:300; color:white;">V19</span></h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    # FILA 1: DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div class="sub-info">EMA200: ${ema200:,.1f}</div></div></div>', unsafe_allow_html=True)
    with c2: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI & ESTRATEGIA</div><div class="panel-content"><span class="price-main" style="color:#FFFFFF;">{rsi:.2f}</span><div class="sub-info">OBJETIVO: < 35</div></div></div>', unsafe_allow_html=True)
    with c3: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">DISPONIBLE</div><div class="panel-content"><span class="price-main" style="color:#DAA520;">${wallet:.2f}</span><div class="sub-info">USDT EN BILLETERA</div></div></div>', unsafe_allow_html=True)
    with c4: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div class="sub-info">RENDIMIENTO NETO</div></div></div>', unsafe_allow_html=True)

    log_msg = "Acechando entrada en mercado..."
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
                <div style="display: flex; gap: 10px; justify-content: center; margin-bottom: 15px;">
                    <div style="border: 1px solid #DAA520; color: #FFF; padding: 6px 15px; border-radius: 4px; font-size: 13px; font-weight:bold;">ENTRY: ${promedio:,.1f}</div>
                    <div style="border: 1px solid #00FF88; color: #FFF; padding: 6px 15px; border-radius: 4px; font-size: 13px; font-weight:bold;">META: ${tp:,.1f}</div>
                </div>
            """, unsafe_allow_html=True)

            if neta >= target_actual or neta <= -2.5:
                try:
                    exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / promedio, price)
                    prof = (state['monto_total'] * neta / 100)
                    state["history"].append({"Fecha": datetime.now().strftime("%H:%M"), "Entrada": f"${promedio:,.0f}", "Salida": f"${price:,.0f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"})
                    state["pnl_acumulado"] += prof
                    state.update({"in_position": False, "compras": [], "monto_total": 0.0}); save_state(state)
                except: pass
            else:
                log_msg = f"DENTRO: {neta:.2f}% (Meta {target_actual}%)"

    # SITUACIÓN ACTUAL
    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-box">{log_msg}</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL COMPACTO Y ENMARCADO
    st.markdown('<div class="neon-panel"><div class="panel-header">📜 HISTORIAL DE CAZA BTC</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-content">', unsafe_allow_html=True)
    st.markdown('<div class="hist-container">', unsafe_allow_html=True)
    
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
        st.markdown('<p style="text-align:center; color:#555; font-size:13px; padding:10px;">Esperando primera operación...</p>', unsafe_allow_html=True)
    
    st.markdown('</div></div></div>', unsafe_allow_html=True)

time.sleep(10)
st.rerun()