import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN (Sin tocar tus llaves personales) ---
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json'
MONTO_OPERACION = 10.0 # Tu presupuesto fijo de 10 USDT

def enviar_telegram_simple(mensaje):
    token = "8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss"
    chat_id = "6458029736"
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={mensaje}"
    try: requests.get(url)
    except: pass

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

# --- 2. DISEÑO NEÓN (Estilo V19 mejorado para BTC) ---
st.set_page_config(page_title="LEONOS BTC | V19 CUSTOM", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Panel Neón Naranja/Oro para Bitcoin */
    .neon-panel { border: 2px solid #FF8C00; border-radius: 12px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(255, 140, 0, 0.3); }
    .panel-header { background: rgba(255, 140, 0, 0.2); padding: 12px; border-bottom: 1px solid #FF8C00; color: #FFD700; font-family: 'Orbitron'; font-size: 14px; text-transform: uppercase; }
    .panel-content { padding: 20px; }
    
    /* Números Grandes y Visibles */
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1.1; }
    .status-msg { color: #FFD700; font-style: italic; font-size: 15px; border-left: 4px solid #FF8C00; padding-left: 15px; }
    
    /* Botones de Modo en Sidebar */
    .stSelectbox label { color: #FFD700 !important; font-family: 'Orbitron'; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MOTOR DE DATOS ---
def fetch_all():
    try:
        # Aquí usa tus llaves de BTC que ya pusiste antes
        mexc = ccxt.mexc({'apiKey': 'mx0vgl09AkPKRbOGO0', 'secret': '39820e86675d494eb5fb0b5c3a184741', 'options': {'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet, exchange = fetch_all()

# BARRA LATERAL (SIDEBAR) PARA AGRESIVIDAD
with st.sidebar:
    st.markdown("<h2 style='color:#FFD700; font-family:Orbitron;'>AJUSTES BTC</h2>", unsafe_allow_html=True)
    modo = st.radio("VELOCIDAD DE VENTA:", ["Scalper (0.35%)", "Equilibrado (0.50%)", "Seguro (0.80%)"])
    targets = {"Scalper (0.35%)": 0.35, "Equilibrado (0.50%)": 0.50, "Seguro (0.80%)": 0.80}
    target_actual = targets[modo]
    st.info(f"Objetivo actual: {target_actual}%")

# CABECERA DINÁMICA
st.markdown('<h1 style="font-family:Orbitron; color:#FFD700; margin:0;">🦁 LEONOS BTC | V19 FULL</h1>', unsafe_allow_html=True)
st.markdown("---")

if data is not None:
    price, rsi = data['close'], data['rsi']
    
    # DASHBOARD DE 4 COLUMNAS (Igual al de SOL)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO BTC</div><div class="panel-content"><span class="price-main">${price:,.1f}</span><br><small>BITCOIN LIVE</small></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI (COMPRA < 30)</div><div class="panel-content"><span class="price-main" style="color:#28a745;">{rsi:.2f}</span><br><small>FUERZA MERCADO</small></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">BILLETERA USDT</div><div class="panel-content"><span class="price-main" style="color:#FFD700;">${wallet:.2f}</span><br><small>DISPONIBLE</small></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><br><small>ESTE BOT</small></div></div>', unsafe_allow_html=True)

    log_msg = "León acechando entrada en Bitcoin..."

    # LÓGICA DE TRADING
    if not state["in_position"]:
        if rsi < 30 and wallet >= MONTO_OPERACION:
            try:
                exchange.create_limit_buy_order(SYMBOL, MONTO_OPERACION / price, price)
                state.update({"in_position": True, "compras": [price], "monto_total": MONTO_OPERACION})
                save_state(state)
                enviar_telegram_simple(f"🦁 BTC COMPRADO: ${price:,.2f}\nModo: {modo}")
            except Exception as e: log_msg = f"❌ ERROR: {e}"
    else:
        promedio = state["compras"][0]
        neta = ((price - promedio) / promedio) * 100
        tp = promedio * (1 + (target_actual / 100))
        
        # Etiquetas visuales de posición (Igual al de SOL)
        st.markdown(f"""
            <div style="display: flex; gap: 10px; margin-bottom: 5px; justify-content: center; flex-wrap: wrap;">
                <span style="background: #FFD70022; color: #FFD700; padding: 5px 15px; border-radius: 20px; border: 1px solid #FFD700; font-size: 12px;"><b>COMPRA:</b> ${promedio:,.2f}</span>
                <span style="background: #00FF0022; color: #00FF00; padding: 5px 15px; border-radius: 20px; border: 1px solid #00FF00; font-size: 12px;"><b>OBJETIVO ({target_actual}%):</b> ${tp:,.2f}</span>
            </div>
            <div style="text-align: center; color: #FF8C00; font-size: 11px; margin-bottom: 20px;">
                PROGRESO ACTUAL: {neta:.2f}%
            </div>
        """, unsafe_allow_html=True)

        if neta >= target_actual or neta <= -2.5:
            try:
                exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / promedio, price)
                prof = (state['monto_total'] * neta / 100)
                state["history"].append({
                    "Fecha": datetime.now().strftime("%H:%M"), "Entrada": f"${promedio:,.1f}",
                    "Salida": f"${price:,.1f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"
                })
                state["pnl_acumulado"] += prof
                state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                save_state(state)
                enviar_telegram_simple(f"💰 VENTA BTC: ${price:,.2f}\nGanancia: ${prof:.4f}")
            except: pass
        else:
            log_msg = f"DENTRO: {neta:.2f}% neto. Buscando {target_actual}%"

    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL FINAL (Estructura de cuadrícula que te gusta)
    st.markdown("<h3 style='font-family:Orbitron; color:#FFD700; font-size:16px;'>📜 ÚLTIMOS MOVIMIENTOS BTC</h3>", unsafe_allow_html=True)
    
    header_html = '<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; color: #FFD700; font-weight: bold; border-bottom: 1px solid #FF8C00; padding-bottom:5px;"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>PROFIT</div></div>'
    filas_html = ""
    for op in reversed(state["history"][-10:]):
        color_pnl = "#00FF00" if "-" not in op["Neto"] else "#FF4444"
        filas_html += f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; padding: 8px 0; border-bottom: 1px solid #333; color: white;"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div style="color:{color_pnl}">{op["Neto"]}</div><div style="color:{color_pnl}">{op["Profit"]}</div></div>'
    
    st.markdown(f'<div class="neon-panel"><div class="panel-content">{header_html}{filas_html}</div></div>', unsafe_allow_html=True)

time.sleep(10)
st.rerun()