import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN (LÓGICA SAGRADA - NO TOCAR) ---
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

# --- 2. DISEÑO VISUAL (AJUSTADO SEGÚN TU REFERENCIA) ---
st.set_page_config(page_title="LEONOS BTC | V19", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Recuadros con sombra y bordes según tu referencia */
    .neon-panel { 
        border: 2px solid #B8860B; 
        border-radius: 12px; 
        background: #050505; 
        margin-bottom: 20px; 
        box-shadow: 0 0 15px rgba(184, 134, 11, 0.3); 
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
    
    /* Situación Actual compacta */
    .status-msg { 
        color: #DAA520; 
        font-style: italic; 
        font-size: 15px; 
        border-left: 4px solid #B8860B; 
        padding-left: 15px; 
    }

    /* Sidebar Forzado Blanco */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    .stToggle label p, .stRadio label p, .stMarkdown p { color: #FFFFFF !important; font-size: 14px !important; }

    /* Grilla del Historial exacta a tu ejemplo */
    .hist-grid-header {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #DAA520; 
        font-weight: bold; 
        border-bottom: 1px solid #B8860B; 
        padding-bottom: 8px;
        font-size: 13px;
    }
    .hist-grid-row {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        padding: 10px 0; 
        border-bottom: 1px solid #333; 
        color: white;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MOTOR DE DATOS (MANTENIDO) ---
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

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown('<p style="color:#DAA520; font-family:Orbitron; font-size:18px;">LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    modo = st.radio("INTENSIDAD DE SALIDA:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"])
    targets = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55, "Tendencia (0.90%)": 0.90}
    target_actual = targets[modo]

st.markdown('<h1 style="font-family:Orbitron; color:#DAA520; margin-bottom:20px;">🦁 LEONOS BTC <span style="font-weight:300; color:white;">V19</span></h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    # DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><br><small>EMA200: ${ema200:,.0f}</small></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI ACTUAL</div><div class="panel-content"><span class="price-main" style="color:#FFFFFF;">{rsi:.2f}</span><br><small>OBJETIVO: < 35</small></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">BILLETERA USDT</div><div class="panel-content"><span class="price-main" style="color:#DAA520;">${wallet:.2f}</span><br><small>DISPONIBLE</small></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><br><small>PROFIT NETO</small></div></div>', unsafe_allow_html=True)

    log_msg = "León acechando entrada..."
    if not bot_encendido:
        log_msg = "SISTEMA EN PAUSA"
    else:
        # AQUÍ VA LA LÓGICA DE TRADING COMPLETA (SAGRADA)
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
                <div style="display: flex; gap: 10px; margin-bottom: 15px; justify-content: center;">
                    <span style="border: 1px solid #DAA520; color: #FFF; padding: 5px 15px; border-radius: 20px; font-size: 12px;"><b>BUY:</b> ${promedio:,.0f}</span>
                    <span style="border: 1px solid #00FF00; color: #FFF; padding: 5px 15px; border-radius: 20px; font-size: 12px;"><b>TP:</b> ${tp:,.0f}</span>
                </div>
            """, unsafe_allow_html=True)

            if neta >= target_actual or neta <= -2.5:
                try:
                    exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / promedio, price)
                    prof = (state['monto_total'] * neta / 100)
                    state["history"].append({
                        "Fecha": datetime.now().strftime("%H:%M"), "Entrada": f"${promedio:,.0f}",
                        "Salida": f"${price:,.0f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"
                    })
                    state["pnl_acumulado"] += prof
                    state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                    save_state(state)
                except: pass
            else:
                log_msg = f"DENTRO: {neta:.2f}% (Meta {target_actual}%)"

    # SITUACIÓN ACTUAL
    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL FINAL CON LA ESTRUCTURA QUE PEDISTE
    hist_html = '<div class="hist-grid-header"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>PROFIT</div></div>'
    if state["history"]:
        for op in reversed(state["history"][-12:]):
            color_p = "#00FF00" if "-" not in op["Neto"] else "#FF4444"
            hist_html += f"""
                <div class="hist-grid-row">
                    <div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div>
                    <div style="color:{color_p}; font-weight:bold;">{op["Neto"]}</div>
                    <div style="color:{color_p};">{op["Profit"]}</div>
                </div>"""
    else:
        hist_html += '<div style="text-align:center; padding:15px; color:#555;">Esperando operaciones...</div>'
    
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMAS OPERACIONES</div><div class="panel-content">{hist_html}</div></div>', unsafe_allow_html=True)

time.sleep(10)
st.rerun()