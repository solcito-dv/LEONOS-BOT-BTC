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

# --- 2. DISEÑO AJUSTADO (ESTILO REFERENCIA) ---
st.set_page_config(page_title="LEONOS BTC | V19", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Recuadros estilo referencia */
    .neon-panel { 
        border: 1px solid #B8860B; 
        border-radius: 12px; 
        background: #050505; 
        margin-bottom: 15px; 
    }
    
    .panel-header { 
        background: rgba(184, 134, 11, 0.15); 
        padding: 10px; 
        border-bottom: 1px solid #B8860B; 
        color: #DAA520; 
        font-family: 'Orbitron'; 
        font-size: 13px; 
        text-transform: uppercase;
    }
    
    .panel-content { padding: 15px; }
    
    .price-main { color: #FFFFFF; font-size: 36px; font-weight: 900; font-family: 'Orbitron'; line-height: 1.1; }
    
    /* Situación Actual ajustada */
    .status-msg { 
        color: #FFFFFF; 
        font-size: 14px; 
        border-left: 4px solid #B8860B; 
        padding-left: 15px; 
        text-transform: uppercase;
        font-weight: 700;
    }

    /* SIDEBAR CORRECCIONES */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    button[kind="header"] svg { fill: #DAA520 !important; } /* Flecha Amarilla */
    .stToggle label p, .stRadio label p, .stMarkdown p { 
        color: #FFFFFF !important; 
        font-size: 13px !important; 
    }

    /* Grid del Historial (Copiado de tu referencia) */
    .hist-grid-header {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #DAA520; 
        font-weight: bold; 
        border-bottom: 1px solid #B8860B; 
        padding-bottom: 5px;
        font-size: 12px;
    }
    .hist-grid-row {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        padding: 8px 0; 
        border-bottom: 1px solid #333; 
        color: white;
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
        delta = df['close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet, exchange = fetch_all()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<p style="color:#DAA520; font-family:Orbitron; font-size:18px;">LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    modo = st.radio("MODO:", ["Scalper (0.35%)", "Equilibrado (0.55%)"])
    targets = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55}
    target_actual = targets[modo]

# CABECERA
st.markdown('<h1 style="font-family:Orbitron; color:#DAA520; margin-bottom:15px; font-size:26px;">🦁 LEONOS BTC | HISTORIAL</h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    # DASHBOARD 4 COLUMNAS (Misma estructura de recuadros)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><br><small>EMA: {ema200:,.0f}</small></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI ACTUAL</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><br><small>OBJETIVO: < 35</small></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">BILLETERA USDT</div><div class="panel-content"><span class="price-main" style="color:#DAA520;">${wallet:.2f}</span><br><small>DISPONIBLE</small></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><br><small>NETO TOTAL</small></div></div>', unsafe_allow_html=True)

    log_msg = "Acechando oportunidad..."
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
                    <span style="border: 1px solid #DAA520; color: #FFF; padding: 5px 15px; border-radius: 20px; font-size: 12px;"><b>BUY:</b> ${promedio:,.0f}</span>
                    <span style="border: 1px solid #00FF00; color: #FFF; padding: 5px 15px; border-radius: 20px; font-size: 12px;"><b>TP:</b> ${tp:,.0f}</span>
                </div>
            """, unsafe_allow_html=True)
            log_msg = f"DENTRO: {neta:.2f}% (Meta: {target_actual}%)"

    # SITUACIÓN ACTUAL
    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL (Usando exactamente la lógica del código que me pasaste)
    contenido_hist = '<div class="hist-grid-header"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>GANANCIA</div></div>'
    
    if state["history"]:
        for op in reversed(state["history"][-8:]):
            color_p = "#00FF00" if "-" not in op["Neto"] else "#FF4444"
            contenido_hist += f'<div class="hist-grid-row"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div style="color:{color_p}; font-weight:bold;">{op["Neto"]}</div><div style="color:{color_p};">{op["Profit"]}</div></div>'
    else:
        contenido_hist += '<div style="text-align:center; padding:15px; font-size:12px; color:#666;">Esperando primera operación...</div>'
    
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMAS OPERACIONES BTC</div><div class="panel-content">{contenido_hist}</div></div>', unsafe_allow_html=True)

time.sleep(10)
st.rerun()