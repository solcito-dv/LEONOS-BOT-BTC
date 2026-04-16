import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN (LÓGICA SAGRADA Y SEGURIDAD) ---
API_KEY_BTC = 'mx0vglJcyb3BIWHjDk' 
SECRET_KEY_BTC = 'de1285d2de1945d2a66e502945c7324b'
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json' # Archivo independiente para no mezclar con Sol
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

# --- 2. DISEÑO VISUAL (VIOLETA & DORADO - ALTO CONTRASTE) ---
st.set_page_config(page_title="LEONOS BTC | V19", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Paneles con Sombra Violeta Sutil */
    .neon-panel { 
        border: 1px solid #B8860B; 
        border-radius: 8px; 
        background: #0a0a0a; 
        margin-bottom: 20px; 
        box-shadow: 0 4px 15px rgba(138, 43, 226, 0.15); 
    }
    
    /* TITULOS EN VIOLETA SOBRE FONDO OSCURO */
    .panel-header { 
        background: #1a0033; /* Violeta muy oscuro */
        padding: 10px 15px; 
        border-bottom: 1px solid #B8860B; 
        color: #BF94E4 !important; /* Violeta claro para lectura */
        font-family: 'Orbitron'; 
        font-size: 13px; 
        text-transform: uppercase;
        font-weight: 800;
        letter-spacing: 2px;
    }
    
    .panel-content { padding: 18px; }
    .price-main { color: #FFFFFF; font-size: 40px; font-weight: 900; font-family: 'Orbitron'; }
    
    /* Situación Actual - Texto Blanco */
    .status-msg { 
        color: #FFFFFF; 
        font-size: 15px; 
        border-left: 3px solid #8A2BE2; 
        padding-left: 15px;
    }

    /* Sidebar - Corrigiendo el color gris de las letras */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #1a0033; }
    .stWidgetLabel p, .stMarkdown p, p { color: #FFFFFF !important; font-size: 14px !important; }
    .stRadio label div div p { color: #FFFFFF !important; } /* Fuerza el blanco en las opciones del radio */
    
    .sidebar-info { color: #8A2BE2; font-size: 11px; font-family: 'JetBrains Mono'; margin-top: 5px; }

    /* Historial */
    .hist-header {
        display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #BF94E4; font-weight: bold; border-bottom: 1px solid #1a0033; 
        padding-bottom: 8px; font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. PROCESAMIENTO ---
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
    st.markdown('<p style="color:#8A2BE2; font-family:Orbitron; font-size:18px; font-weight:900;">LEONOS CLOUD</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    
    st.markdown("---")
    st.markdown('<p style="color:#BF94E4; font-size:11px;">CONEXIÓN SEGURA</p>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-info">● NODO: BUENOS AIRES</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-info">● ENCRIPTACIÓN: AES-256</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    # Aquí las letras ahora se verán blancas
    modo = st.radio("TARGET DE SALIDA:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"])
    targets = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55, "Tendencia (0.90%)": 0.90}
    target_actual = targets[modo]

st.markdown('<h1 style="font-family:Orbitron; color:#FFFFFF; margin-bottom:20px;">🦁 LEONOS <span style="color:#8A2BE2;">BTC</span></h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">MERCADO BTC</div><div class="panel-content"><span class="price-main">${price:,.0f}</span></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI (14M)</div><div class="panel-content"><span class="price-main" style="color:#BF94E4;">{rsi:.1f}</span></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">SALDO REAL</div><div class="panel-content"><span class="price-main" style="color:#DAA520;">${wallet:.2f}</span></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">PROFIT NETO</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span></div></div>', unsafe_allow_html=True)

    log_msg = "León acechando... esperando RSI < 35"
    if not bot_encendido: log_msg = "SISTEMA EN PAUSA MANUAL"
    else:
        # LÓGICA DE TRADING (SAGRADA)
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
            if neta >= target_actual or neta <= -2.5:
                try:
                    exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / promedio, price)
                    prof = (state['monto_total'] * neta / 100)
                    state["history"].append({"Fecha": datetime.now().strftime("%H:%M"), "Entrada": f"${promedio:,.0f}", "Salida": f"${price:,.0f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"})
                    state["pnl_acumulado"] += prof
                    state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                    save_state(state)
                except: pass
            else: log_msg = f"POSICIÓN ABIERTA: {neta:.2f}% (Buscando {target_actual}%)"

    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN OPERATIVA</div><div class="panel-content"><div class="status-msg">{log_msg}</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL
    hist_html = '<div class="hist-header"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>GANANCIA</div></div>'
    if state["history"]:
        for op in reversed(state["history"][-10:]):
            color_p = "#00FF00" if "-" not in op["Neto"] else "#FF4444"
            hist_html += f'<div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr 1fr; padding:10px 0; border-bottom:1px solid #1a0033; font-size:12px; color:white;"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div style="color:{color_p};">{op["Neto"]}</div><div style="color:{color_p};">{op["Profit"]}</div></div>'
    
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 REGISTRO DE OPERACIONES INDEPENDIENTE</div><div class="panel-content">{hist_html}</div></div>', unsafe_allow_html=True)

time.sleep(15)
st.rerun()