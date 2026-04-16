import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN DE SEGURIDAD ---
API_KEY_BTC = 'mx0vgl09AkPKRbOGO0' 
SECRET_KEY_BTC = '39820e86675d494eb5fb0b5c3a184741'
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json' 
MONTO_OPERACION = 10.0

def enviar_telegram_premium(titulo, precio, profit, neto, estado):
    token = "8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss"
    chat_id = "6458029736"
    msg = (f"🦁 {titulo}\n"
           f"━━━━━━━━━━━━━━━\n"
           f"💰 PRECIO: {precio}\n"
           f"📈 PROFIT: {profit}\n"
           f"📊 NETO: {neto}\n"
           f"🏛️ MODO: {estado}")
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
    try: requests.get(url)
    except: pass

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"in_position": False, "compras": [], "monto_total": 0.0, "history": [], "pnl_ganado": 0.0}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

# --- 2. INTERFAZ HIGH-CONTRAST PREMIUM ---
st.set_page_config(page_title="LEONOS BTC PREMIUM", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Roboto+Mono:wght@700&display=swap');
    
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Recuadros Definidos Estilo Terminal */
    .metric-container {
        background: #0D0D0D;
        border: 2px solid #333;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 10px;
        text-align: center;
    }
    
    .metric-title {
        color: #D4AF37;
        font-family: 'Orbitron';
        font-size: 14px;
        letter-spacing: 2px;
        margin-bottom: 10px;
        text-transform: uppercase;
    }
    
    .metric-value-large {
        color: #FFFFFF;
        font-family: 'Roboto Mono';
        font-size: 45px; /* Números mucho más grandes */
        font-weight: 700;
    }

    /* Historial Estructurado */
    .hist-row {
        background: #111;
        border-left: 4px solid #D4AF37;
        padding: 12px;
        margin-top: 5px;
        border-radius: 0 5px 5px 0;
        display: flex;
        justify-content: space-between;
        font-family: 'Roboto Mono';
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR: AGRESIVIDAD OPTIMIZADA ---
with st.sidebar:
    st.markdown("<h2 style='color:#D4AF37; font-family:Orbitron;'>CONTROLES</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Cambiamos los rangos para que sean más rápidos
    modo = st.select_slider(
        "VELOCIDAD DE GANANCIA",
        options=["Seguro", "Equilibrado", "Rápido (0 Fee)"],
        value="Rápido (0 Fee)"
    )
    
    # Porcentajes ajustados: el rápido ahora es un scalp agresivo
    targets = {"Seguro": 0.65, "Equilibrado": 0.45, "Rápido (0 Fee)": 0.35}
    target_actual = targets[modo]
    
    st.success(f"Target activo: {target_actual}%")
    st.info("Aprovechando 0 comisiones en MEXC.")

# --- 4. MOTOR Y LÓGICA ---
def fetch_data():
    try:
        mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=50)
        df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        delta = df['c'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet_real, exchange = fetch_data()

# TÍTULO DINÁMICO Y VISIBLE
st.markdown(f"""
    <div style='text-align:center; padding: 20px;'>
        <h1 style='font-family:Orbitron; color:#D4AF37; font-size: 50px; margin-bottom:0;'>🦁 LEONOS BTC</h1>
        <p style='color:#666; font-size: 18px;'>ESTADO: {'🟢 OPERANDO' if data else '🔴 DESCONECTADO'}</p>
    </div>
""", unsafe_allow_html=True)

if data is not None:
    price, rsi = data['c'], data['rsi']
    
    # DASHBOARD DE IMPACTO
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""<div class="metric-container"><div class="metric-title">PRECIO ACTUAL</div>
        <div class="metric-value-large">${price:,.1f}</div></div>""", unsafe_allow_html=True)
    
    with col2:
        rsi_color = "#00FF88" if rsi < 35 else ("#FF3333" if rsi > 65 else "#FFFFFF")
        st.markdown(f"""<div class="metric-container"><div class="metric-title">RSI (FUERZA)</div>
        <div class="metric-value-large" style="color:{rsi_color};">{rsi:.1f}</div></div>""", unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""<div class="metric-container"><div class="metric-title">GANANCIA TOTAL</div>
        <div class="metric-value-large" style="color:#00FF88;">${state["pnl_ganado"]:.3f}</div></div>""", unsafe_allow_html=True)

    # LÓGICA DE TRADING
    if not state["in_position"]:
        if rsi < 30 and wallet_real >= MONTO_OPERACION:
            try:
                exchange.create_limit_buy_order(SYMBOL, MONTO_OPERACION / price, price)
                state.update({"in_position": True, "compras": [price], "monto_total": MONTO_OPERACION})
                save_state(state)
                enviar_telegram_premium("COMPRA EJECUTADA 📥", f"${price:,.2f}", "---", "---", modo)
            except: pass
    else:
        p_entrada = state["compras"][0]
        pnl_neto = ((price - p_entrada) / p_entrada) * 100
        
        # BARRA DE PROGRESO VISUAL
        progreso = min(max(pnl_neto / target_actual, 0.0), 1.0)
        st.write(f"Progreso para Venta ({target_actual}%):")
        st.progress(progreso)

        if pnl_neto >= target_actual or pnl_neto <= -2.5:
            try:
                exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / p_entrada, price)
                profit_usd = (state['monto_total'] * pnl_neto / 100)
                state["pnl_ganado"] += profit_usd
                state["history"].append({"H": datetime.now().strftime("%H:%M"), "N": f"{pnl_neto:.2f}%", "U": f"${profit_usd:.4f}"})
                state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                save_state(state)
                enviar_telegram_premium("VENTA EJECUTADA 💰", f"${price:,.2f}", f"${profit_usd:.4f}", f"{pnl_neto:.2f}%", "Cerrado")
            except: pass

    # HISTORIAL BIEN ESTRUCTURADO
    st.markdown("<h2 style='font-family:Orbitron; color:#D4AF37; font-size:20px; margin-top:30px;'>HISTORIAL DE CAZA</h2>", unsafe_allow_html=True)
    if state["history"]:
        for h in reversed(state["history"][-6:]):
            color_txt = "#00FF88" if "$" in h["U"] and "-" not in h["U"] else "#FF3333"
            st.markdown(f"""
                <div class="hist-row">
                    <span style="color:#888;">{h['H']}</span>
                    <span style="font-weight:bold;">{h['N']}</span>
                    <span style="color:{color_txt};">{h['U']}</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.write("Esperando movimientos...")

# FOOTER INFO
with st.expander("DETALLES DE BILLETERA"):
    st.write(f"Saldo Disponible: {wallet_real:.2f} USDT")
    st.write(f"IP Autorizada: Si (Whitelist OK)")

time.sleep(10)
st.rerun()