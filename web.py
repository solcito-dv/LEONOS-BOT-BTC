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
    msg = (f"💎 LEONOS PREMIUM | {titulo}\n"
           f"━━━━━━━━━━━━━━━\n"
           f"💰 PRECIO: {precio}\n"
           f"📈 PROFIT: {profit}\n"
           f"📊 NETO: {neto}\n"
           f"🏛️ ESTADO: {estado}")
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

# --- 2. INTERFAZ PREMIUM (ESTILO DARK STEALTH) ---
st.set_page_config(page_title="LEONOS BTC PREMIUM", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700&family=IBM+Plex+Mono&display=swap');
    
    .stApp { background-color: #000000; font-family: 'Inter', sans-serif; color: #E0E0E0; }
    
    /* Paneles Elegantes */
    .metric-card {
        background: #0A0A0A;
        border: 1px solid #222;
        border-radius: 4px;
        padding: 20px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .metric-label { color: #888; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
    .metric-value { color: #D4AF37; font-size: 32px; font-weight: 700; font-family: 'IBM Plex Mono'; }
    
    /* Sidebar Premium */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #111; }
    
    /* Tabla de Historial */
    .pnl-pos { color: #00FF88; font-weight: bold; }
    .pnl-neg { color: #FF3333; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. BARRA LATERAL (SIDEBAR SMART) ---
with st.sidebar:
    st.markdown("<h2 style='color:#D4AF37; font-size:20px;'>CONTROL CENTER</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Selector de Agresividad
    agresividad = st.select_slider(
        "MODO DE AGRESIVIDAD",
        options=["Conservador", "Equilibrado", "Scalper"],
        value="Equilibrado"
    )
    
    targets = {"Conservador": 0.45, "Equilibrado": 0.60, "Scalper": 0.85}
    target_actual = targets[agresividad]
    
    st.write(f"🎯 Target Objetivo: **{target_actual}%**")
    st.markdown("---")
    
    if st.button("RESETEAR SISTEMA"):
        st.session_state.clear()
        st.rerun()

# --- 4. EJECUCIÓN DEL MOTOR ---
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

# HEADER
st.markdown("<div style='text-align:center;'><h1 style='color:#D4AF37; font-weight:300; letter-spacing:5px;'>LEONOS <span style='font-weight:700;'>BITCOIN</span></h1><p style='color:#555;'>INSTITUTIONAL GRADE SCALPING</p></div>", unsafe_allow_html=True)

if data is not None:
    price, rsi = data['c'], data['rsi']
    
    # DASHBOARD
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Market Price</div><div class="metric-value">${price:,.2f}</div></div>', unsafe_allow_html=True)
    with c2:
        color_rsi = "#D4AF37" if 30 < rsi < 70 else ("#00FF88" if rsi <= 30 else "#FF3333")
        st.markdown(f'<div class="metric-card"><div class="metric-label">RSI Index</div><div class="metric-value" style="color:{color_rsi};">{rsi:.2f}</div></div>', unsafe_allow_html=True)
    with c3:
        color_pnl = "#00FF88" if state["pnl_ganado"] >= 0 else "#FF3333"
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Profit</div><div class="metric-value" style="color:{color_pnl};">${state["pnl_ganado"]:.4f}</div></div>', unsafe_allow_html=True)

    # LÓGICA DE TRADING
    if not state["in_position"]:
        if rsi < 30 and wallet_real >= MONTO_OPERACION:
            try:
                exchange.create_limit_buy_order(SYMBOL, MONTO_OPERACION / price, price)
                state.update({"in_position": True, "compras": [price], "monto_total": MONTO_OPERACION})
                save_state(state)
                enviar_telegram_premium("ENTRY EXECUTED", f"${price:,.2f}", "---", "---", f"Agresividad: {agresividad}")
            except Exception as e: st.error(f"Error: {e}")
    else:
        p_entrada = state["compras"][0]
        pnl_neto = ((price - p_entrada) / p_entrada) * 100
        
        if pnl_neto >= target_actual or pnl_neto <= -2.5:
            try:
                exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / p_entrada, price)
                profit_usd = (state['monto_total'] * pnl_neto / 100)
                state["pnl_ganado"] += profit_usd
                state["history"].append({"Hora": datetime.now().strftime("%H:%M"), "Neto": f"{pnl_neto:.2f}%", "USD": f"${profit_usd:.4f}"})
                state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                save_state(state)
                enviar_telegram_premium("EXIT EXECUTED", f"${price:,.2f}", f"${profit_usd:.4f}", f"{pnl_neto:.2f}%", "Closed")
            except: pass
        else:
            st.markdown(f"<p style='text-align:center; color:#888;'>🚀 Position Active: <span style='color:#D4AF37;'>{pnl_neto:.2f}%</span> (Target: {target_actual}%)</p>", unsafe_allow_html=True)

    # HISTORIAL PREMIUM
    st.markdown("<br><h3 style='font-size:14px; color:#555; letter-spacing:2px;'>RECENT ACTIVITY</h3>", unsafe_allow_html=True)
    if state["history"]:
        # Crear tabla con colores
        for h in reversed(state["history"][-5:]):
            clase = "pnl-pos" if "-" not in h["USD"] else "pnl-neg"
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #111;">
                    <span style="color:#555;">{h['Hora']}</span>
                    <span style="font-family:'IBM Plex Mono';">{h['Neto']}</span>
                    <span class="{clase}" style="font-family:'IBM Plex Mono';">{h['USD']}</span>
                </div>
            """, unsafe_allow_html=True)

time.sleep(10)
st.rerun()