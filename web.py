import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN DE SEGURIDAD ---
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

# --- 2. DISEÑO DE ALTO IMPACTO (CUSTOM CSS) ---
st.set_page_config(page_title="LEONOS BTC | ELITE", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Paneles con Neón Naranja */
    .neon-box {
        border: 2px solid #FF8C00;
        border-radius: 15px;
        background: #080808;
        margin-bottom: 25px;
        box-shadow: 0 0 20px rgba(255, 140, 0, 0.15);
        overflow: hidden;
    }
    
    .box-header {
        background: linear-gradient(90deg, #FF8C00 0%, #FFD700 100%);
        padding: 10px 20px;
        color: #000000;
        font-family: 'Orbitron';
        font-size: 13px;
        font-weight: 900;
        letter-spacing: 2px;
    }
    
    .box-content { padding: 20px; }
    
    /* Números de Pantalla */
    .big-number {
        font-family: 'Orbitron';
        font-size: 48px;
        font-weight: 900;
        color: #FFFFFF;
        line-height: 1;
    }
    
    /* Estado del Bot (Blanco y Elegante) */
    .status-container {
        background: #FFFFFF;
        color: #000000;
        border-radius: 8px;
        padding: 15px;
        font-weight: 800;
        text-align: center;
        text-transform: uppercase;
        font-size: 14px;
        letter-spacing: 1px;
        border: 2px solid #FFD700;
    }

    /* Estilo del Sidebar (Selectores) */
    .stRadio [data-testid="stWidgetLabel"] p { color: #FFD700 !important; font-family: 'Orbitron'; font-size: 16px; }
    
    /* Tabla de Historial */
    .table-header {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
        color: #FFD700;
        font-weight: bold;
        padding: 10px;
        border-bottom: 2px solid #FF8C00;
        font-size: 12px;
    }
    
    .table-row {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
        padding: 12px 10px;
        border-bottom: 1px solid #222;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGICA Y DATOS ---
def fetch_all():
    try:
        mexc = ccxt.mexc({'apiKey': 'mx0vglJcyb3BIWHjDk', 'secret': 'de1285d2de1945d2a66e502945c7324b', 'options': {'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet, exchange = fetch_all()

# --- 4. SIDEBAR (CONTROLES PERSONALIZADOS) ---
with st.sidebar:
    st.markdown("<h1 style='color:#FF8C00; font-family:Orbitron; font-size:22px;'>CONFIG BTC</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Selector de porcentaje con el estilo que te gusta
    modo = st.radio("VELOCIDAD DE SALIDA:", 
                    ["Scalper (0.35%)", "Equilibrado (0.55%)", "Inversor (1.00%)"], 
                    index=0)
    
    targets = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55, "Inversor (1.00%)": 1.00}
    target_actual = targets[modo]
    
    st.markdown("---")
    # Interruptor de pausa
    encendido = st.toggle("SISTEMA ACTIVO", value=True)
    
    if st.button("RESETEAR CACHÉ"):
        st.session_state.clear()
        st.rerun()

# --- 5. CABECERA ---
st.markdown('<h1 style="font-family:Orbitron; color:#FFD700; margin-bottom:5px;">🦁 LEONOS BTC <span style="color:#FFFFFF; font-weight:300;">ELITE EDITION</span></h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi = data['close'], data['rsi']
    
    # FILA 1: DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="neon-box"><div class="box-header">PRECIO MARKET</div><div class="box-content"><span class="big-number">${price:,.0f}</span></div></div>', unsafe_allow_html=True)
    with c2:
        rsi_color = "#00FF88" if rsi < 35 else ("#FF4444" if rsi > 65 else "#FFD700")
        st.markdown(f'<div class="neon-box"><div class="box-header">RSI INDICATOR</div><div class="box-content"><span class="big-number" style="color:{rsi_color};">{rsi:.1f}</span></div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="neon-box"><div class="box-header">WALLET USDT</div><div class="box-content"><span class="big-number" style="color:#FFD700;">${wallet:.1f}</span></div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="neon-box"><div class="box-header">PNL ACUMULADO</div><div class="box-content"><span class="big-number" style="color:#00FF88;">${state["pnl_acumulado"]:.3f}</span></div></div>', unsafe_allow_html=True)

    # FILA 2: SITUACIÓN Y LOGICA
    log_msg = "ACECHANDO OPORTUNIDAD..."
    if not encendido:
        log_msg = "SISTEMA EN PAUSA"
    else:
        if not state["in_position"]:
            if rsi < 30 and wallet >= MONTO_OPERACION:
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
                <div style="display: flex; gap: 15px; justify-content: center; margin-bottom: 20px;">
                    <div style="background:#FFD700; color:#000; padding:10px 25px; border-radius:5px; font-weight:900;">ENTRY: ${promedio:,.2f}</div>
                    <div style="background:#00FF88; color:#000; padding:10px 25px; border-radius:5px; font-weight:900;">TARGET: ${tp:,.2f}</div>
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
                log_msg = f"POSICIÓN ABIERTA: {neta:.2f}% (Buscando {target_actual}%)"

    # CAJA DE ESTADO (Blanca con letras negras)
    st.markdown(f'<div class="status-container">{log_msg}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # FILA 3: HISTORIAL RECUADRADO
    st.markdown('<div class="neon-box">', unsafe_allow_html=True)
    st.markdown('<div class="box-header">📜 HISTORIAL DE OPERACIONES</div>', unsafe_allow_html=True)
    st.markdown('<div class="box-content">', unsafe_allow_html=True)
    
    # Encabezado de la tabla
    st.markdown('<div class="table-header"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>GANANCIA</div></div>', unsafe_allow_html=True)
    
    # Filas de la tabla
    if state["history"]:
        for op in reversed(state["history"][-8:]):
            color_res = "#00FF88" if "-" not in op["Neto"] else "#FF4444"
            st.markdown(f"""
                <div class="table-row">
                    <div style="color:#777;">{op["Fecha"]}</div>
                    <div>{op["Entrada"]}</div>
                    <div>{op["Salida"]}</div>
                    <div style="color:{color_res}; font-weight:bold;">{op["Neto"]}</div>
                    <div style="color:{color_res};">{op["Profit"]}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<p style="text-align:center; color:#555; padding:20px;">Sin operaciones recientes</p>', unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)

time.sleep(10)
st.rerun()