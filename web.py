import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
import requests
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
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
    defaults = {"capital_asignado": 10.0, "pnl_acumulado": 0.0, "posiciones": [], "history": [], "last_cz_sell_time": 0}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data
        except: return defaults
    return defaults

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# --- 2. INTERFAZ ---
st.set_page_config(page_title="LEONOS BTC | V34.0", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    .neon-panel { border: 2px solid #DC143C; border-radius: 12px; background: #050505; margin-bottom: 20px; }
    .panel-header { background: rgba(220, 20, 60, 0.2); padding: 10px; color: #FFFF00; font-weight: bold; border-bottom: 1px solid #DC143C; }
    .price-main { font-size: 40px; font-weight: 900; color: #FFFFFF; }
    </style>
    """, unsafe_allow_html=True)

state = load_state()

def fetch_data():
    try:
        mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
        df = pd.DataFrame(bars, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        df['ema9'] = df['c'].ewm(span=9, adjust=False).mean()
        df['ema200'] = df['c'].ewm(span=200, adjust=False).mean()
        # RSI
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        return df.iloc[-1], mexc
    except: return None, None

data, exchange = fetch_data()

with st.sidebar:
    st.title("🦁 LEONOS V34.0")
    bot_activo = st.toggle("SISTEMA ACTIVO", value=True)
    target_base = 0.40 # Tu objetivo de 0.40%
    trailling_gap = 0.02 # Lo que pediste: si baja de 0.40 a 0.38, vende.

# --- 3. LÓGICA DE TRADING ---
if data is not None:
    price = data['c']
    rsi = data['rsi']
    ema9 = data['ema9']
    ema200 = data['ema200']
    
    # Cálculos de Capital
    total_cap = float(state["capital_asignado"]) + float(state["pnl_acumulado"])
    monto_op = (total_cap * 0.50) - 0.05

    # Visualización (Resumida para evitar duplicados)
    col1, col2, col3 = st.columns(3)
    col1.metric("PRECIO BTC", f"${price:,.2f}")
    col2.metric("RSI (1m)", f"{rsi:.2f}")
    col3.metric("PNL TOTAL", f"${state['pnl_acumulado']:.4f}")

    # COMPRAS
    if bot_activo and len(state["posiciones"]) < 2:
        t_compra = None
        # Nueva Confirmación: RSI bajo + Precio cruzando EMA 9 hacia arriba
        confirmado = price > ema9 
        
        # Lógica Abeja
        if rsi < 40 and confirmado and price > ema200 and not any(p['tipo']=="Abeja" for p in state["posiciones"]):
            t_compra = "Abeja"
        
        # Lógica Cazadora (Separada por 0.5%)
        distancia_ok = True
        if state["posiciones"]:
            distancia_ok = abs(price - state["posiciones"][0]["precio"]) > (state["posiciones"][0]["precio"] * 0.005)
            
        if rsi < 30 and confirmado and distancia_ok and not any(p['tipo']=="Cazadora" for p in state["posiciones"]):
            t_compra = "Cazadora"

        if t_compra:
            try:
                exchange.create_market_buy_order(SYMBOL, monto_op / price)
                state["posiciones"].append({
                    "precio": price, "monto": monto_op, "tipo": t_compra, 
                    "max_alc": price, "breakeven": False
                })
                save_state(state)
                send_telegram_msg(f"🦁 COMPRA {t_compra}: ${price:,.2f}")
            except: pass

    # VENTAS (PROTECCIÓN Y GATILLO)
    nuevas_pos = []
    for pos in state["posiciones"]:
        p_ganancia = ((price - pos['precio']) / pos['precio']) * 100
        if price > pos['max_alc']: pos['max_alc'] = price
        
        # 1. Breakeven (Si toca +0.15%, el Stop Loss ahora es el precio de entrada)
        if p_ganancia >= 0.15: pos['breakeven'] = True
        
        # 2. Stop Loss Dinámico
        stop_loss_real = -0.80 # Inicial
        if pos['breakeven']: stop_loss_real = 0.0 # Ya no perdemos
        if p_ganancia >= 0.30: stop_loss_real = 0.15 # Subimos el piso

        # 3. Gatillo Rápido (Take Profit Dinámico)
        # Si ya pasó el 0.40% y retrocedió 0.02% desde el máximo... ¡VENDE!
        caida_desde_max = ((price - pos['max_alc']) / pos['max_alc']) * 100
        se_agoto = (p_ganancia >= target_base and caida_desde_max <= -trailling_gap)

        if p_ganancia <= stop_loss_real or se_agoto:
            try:
                exchange.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
                profit = (pos['monto'] * p_ganancia / 100)
                state["pnl_acumulado"] += profit
                h_actual = datetime.now().strftime("%H:%M:%S")
                state["history"].append({
                    "Fecha": f"{datetime.now().strftime('%d/%m')} {h_actual}",
                    "Entrada": f"${pos['precio']:,.0f}", "Salida": f"${price:,.0f}",
                    "%": f"{p_ganancia:.2f}%", "Profit": f"${profit:.4f}"
                })
                save_state(state)
                send_telegram_msg(f"💰 VENTA {pos['tipo']}: {p_ganancia:.2f}% | ${profit:.4f}")
            except: nuevas_pos.append(pos)
        else:
            nuevas_pos.append(pos)

    state["posiciones"] = nuevas_pos
    save_state(state)

    # --- HISTORIAL Y ESTADO ---
    st.markdown("---")
    st.subheader("📜 Historial de Operaciones (Últimas 10)")
    if state["history"]:
        df_hist = pd.DataFrame(state["history"]).iloc[::-1].head(10)
        st.table(df_hist)

time.sleep(15)
st.rerun()