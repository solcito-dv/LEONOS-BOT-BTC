import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
import requests
from datetime import datetime

# --- 1. CONFIGURACIÓN TÉCNICA ---
API_KEY_BTC = 'mx0vglJcyb3BIWHjDk' 
SECRET_KEY_BTC = 'de1285d2de1945d2a66e502945c7324b'
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json'

TELEGRAM_TOKEN = '8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss'
TELEGRAM_CHAT_ID = '6458029736'

def send_telegram_msg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}&parse_mode=Markdown"
        requests.get(url)
    except: pass

def load_state():
    data_recuperada = {
        "pnl_acumulado": 0.0176,
        "posiciones": [
            {"precio": 74832.0, "monto": 10.0},
            {"precio": 75066.0, "monto": 5.0}
        ],
        "history": [
            {"Fecha": "Anterior", "Entrada": "Varias", "Salida": "Venta Ejecutada", "Neto": "Profit", "Profit": "$0.0176"}
        ]
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if not state.get("posiciones") and not state.get("pnl_acumulado"):
                    return data_recuperada
                return state
        except: pass
    return data_recuperada

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        st.error(f"ERROR CRÍTICO DE MEMORIA: No se pudo guardar el archivo {e}")

# --- 2. ESTILOS PROFESIONALES ---
st.set_page_config(page_title="LEONOS BTC | V28", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #FFFFFF !important; font-weight: bold; }
    .neon-panel { border: 2px solid #DC143C; border-radius: 12px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(220, 20, 60, 0.2); }
    .panel-header { background: rgba(220, 20, 60, 0.2); padding: 12px; border-bottom: 1px solid #DC143C; color: #FFFF00 !important; font-family: 'Orbitron'; font-size: 14px; text-transform: uppercase; font-weight: 900; }
    .panel-content { padding: 20px; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    .status-msg { color: #FFFFFF; font-style: italic; font-size: 15px; border-left: 4px solid #FFFF00; padding-left: 15px; }
    .burbuja { padding: 12px 20px; border-radius: 30px; font-weight: 800; font-size: 13px; display: inline-block; margin: 8px; border: 1px solid rgba(255,255,255,0.2); }
    .b-entrada { background: #1E90FF; color: white; }
    .b-venta { background: #228B22; color: white; }
    .b-stop { background: #B22222; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. INICIO ---
state = load_state()
save_state(state)

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

data, wallet_real, exchange = fetch_all()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:20px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    modo = st.radio("INTENSIDAD DE TRADING:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"], index=0)
    target_pct = float(modo.split('(')[1].split('%')[0])
    st.markdown("---")
    st.markdown("● SERVIDOR: OPERATIVO")
    st.markdown("● EXCHANGE: MEXC CONNECTED")

st.markdown('<h1 style="font-family:Orbitron; color:#DC143C;">🦁 LEONOS BTC V28</h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    capital_en_uso = sum(pos['monto'] for pos in state["posiciones"])
    
    # DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div style="color:#FFFF00; font-size:12px; font-weight:bold;">EMA200: ${ema200:,.0f}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI ACTUAL</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div style="color:#FFFF00; font-size:12px; font-weight:bold;">OBJETIVO: < 35</div></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">CAPITAL EN USO</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${capital_en_uso:.2f}</span><div style="color:#FFFF00; font-size:12px; font-weight:bold;">EN OPERACIÓN</div></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">PNL TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div style="color:#00FF00; font-size:12px; font-weight:bold;">GANANCIA ACUMULADA</div></div></div>', unsafe_allow_html=True)

    # --- 5. TARJETAS DE OPERACIÓN ACTIVA (FILA ÚNICA) ---
    if state["posiciones"]:
        # Creamos una columna por cada posición para que queden una al lado de la otra
        cols_tarjetas = st.columns(len(state["posiciones"]))
        for i, pos in enumerate(state["posiciones"]):
            v_target = pos['precio'] * (1 + target_pct/100)
            v_stop = pos['precio'] * 0.975
            with cols_tarjetas[i]:
                st.markdown(f"""
                    <div style="text-align: center; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 15px; border: 1px solid #333;">
                        <div class="burbuja b-entrada" style="display:block; margin: 5px auto;">COMPRA {i+1}: ${pos['precio']:,.0f}</div>
                        <div class="burbuja b-venta" style="display:block; margin: 5px auto;">VENTA: ${v_target:,.0f}</div>
                        <div class="burbuja b-stop" style="display:block; margin: 5px auto;">STOP: ${v_stop:,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)

    # --- 6. LÓGICA DE TRADING ---
    log_msg = "Monitoreando señales..."
    if bot_encendido:
        nuevas_pos = []
        for pos in state["posiciones"]:
            neta = ((price - pos['precio']) / pos['precio']) * 100
            if neta >= target_pct or neta <= -2.5:
                try:
                    exchange.create_limit_sell_order(SYMBOL, pos['monto'] / pos['precio'], price)
                    prof = (pos['monto'] * neta / 100)
                    state["pnl_acumulado"] += prof
                    state["history"].append({"Fecha": datetime.now().strftime("%H:%M:%S"), "Entrada": f"${pos['precio']:,.0f}", "Salida": f"${price:,.0f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"})
                    save_state(state)
                    send_telegram_msg(f"🦁 VENTA BTC: {neta:.2f}% | +${prof:.4f}")
                except: nuevas_pos.append(pos)
            else:
                nuevas_pos.append(pos)
                log_msg = f"Posición abierta: {neta:.2f}%"
        state["posiciones"] = nuevas_pos
        save_state(state)

    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # --- 7. HISTORIAL FINAL ---
    contenido_hist = '<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; color: #FFFF00; font-weight: bold; border-bottom: 3px solid #DC143C; padding-bottom:8px; font-size:15px;"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>GANANCIA</div></div>'
    for op in reversed(state["history"][-10:]):
        color_neto = "#00FF00" if "-" not in op["Neto"] else "#FF0000"
        contenido_hist += f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; padding: 11px 0; border-bottom: 2px solid #222; color: white; font-size: 14px;"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div style="color:{color_neto}; font-weight:bold;">{op["Neto"]}</div><div style="color:{color_neto};">{op["Profit"]}</div></div>'

    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMAS OPERACIONES</div><div class="panel-content">{contenido_hist}</div></div>', unsafe_allow_html=True)

time.sleep(15)
st.rerun()