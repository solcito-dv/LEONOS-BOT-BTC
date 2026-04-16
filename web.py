import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN DE SEGURIDAD Y LLAVES ---
# REEMPLAZA ESTO CON TU NUEVA LLAVE DE BTC
API_KEY_BTC = 'mx0vglJcyb3BIWHjDk' 
SECRET_KEY_BTC = 'de1285d2de1945d2a66e502945c7324b'
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json' 
MONTO_OPERACION = 10.0  # Monto fijo e independiente

def enviar_telegram_pro(titulo, precio, profit, neto, estado):
    token = "8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss"
    chat_id = "6458029736"
    # Formato profesional para Telegram
    msg = (f"🦁 {titulo}\n"
           f"━━━━━━━━━━━━━━━\n"
           f"💰 Precio: {precio}\n"
           f"📈 Profit: {profit}\n"
           f"📊 Neto: {neto}\n"
           f"📝 Estado: {estado}\n"
           f"📍 Moneda: BITCOIN")
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
    try: requests.get(url)
    except: pass

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                if "pnl_ganado" not in state: state["pnl_ganado"] = 0.0
                return state
        except: pass
    return {"in_position": False, "compras": [], "monto_total": 0.0, "history": [], "pnl_ganado": 0.0}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

# --- 2. DISEÑO DE INTERFAZ PROFESIONAL ---
st.set_page_config(page_title="LEONOS BTC SCALPER", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono'; color: #FFFFFF; }
    .neon-panel { border: 2px solid #FF8C00; border-radius: 12px; background: #050505; margin-bottom: 15px; box-shadow: 0 0 15px rgba(255, 140, 0, 0.3); }
    .panel-header { background: rgba(255, 140, 0, 0.2); padding: 10px; border-bottom: 1px solid #FF8C00; color: #FFD700; font-family: 'Orbitron'; font-size: 13px; text-transform: uppercase; }
    .panel-content { padding: 15px; text-align: center; }
    .price-main { color: #FFFFFF; font-size: 40px; font-weight: 900; font-family: 'Orbitron'; text-shadow: 0 0 10px rgba(255,255,255,0.2); }
    .metric-sub { color: #888; font-size: 12px; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MOTOR DE DATOS Y CONEXIÓN ---
def fetch_all():
    try:
        mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        # Cálculo de RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        # Saldo real
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet_real, exchange = fetch_all()

# --- CABECERA ---
st.markdown('<h1 style="font-family:Orbitron; color:#FFD700; text-align:center; margin-bottom:5px;">🦁 LEONOS BTC SCALPER</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="text-align:center; color:#FF8C00; font-size:14px;">MODO 0 FEE | PREPUSESTO: ${MONTO_OPERACION} USDT</p>', unsafe_allow_html=True)

if data is not None:
    price, rsi = data['close'], data['rsi']
    target_scalp = 0.55  # 0.55% de ganancia para Bitcoin
    
    # DASHBOARD DE 3 COLUMNAS
    c1, c2, c3 = st.columns(3)
    with c1: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO BITCOIN</div><div class="panel-content"><span class="price-main">${price:,.2f}</span><div class="metric-sub">Símbolo: {SYMBOL}</div></div></div>', unsafe_allow_html=True)
    with c2: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI (COMPRA < 30)</div><div class="panel-content"><span class="price-main" style="color:#FFA500;">{rsi:.2f}</span><div class="metric-sub">Filtro de Sobreventa</div></div></div>', unsafe_allow_html=True)
    with c3: 
        st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA ACUMULADA</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_ganado"]:.4f}</span><div class="metric-sub">Solo de este bot</div></div></div>', unsafe_allow_html=True)

    # --- LÓGICA DE OPERACIÓN ---
    log_status = "👁️ Acechando entrada perfecta..."
    
    if not state["in_position"]:
        # Solo compra si RSI está bajo y hay dinero en la billetera
        if rsi < 30 and wallet_real >= MONTO_OPERACION:
            try:
                exchange.create_limit_buy_order(SYMBOL, MONTO_OPERACION / price, price)
                state.update({"in_position": True, "compras": [price], "monto_total": MONTO_OPERACION})
                save_state(state)
                enviar_telegram_pro("COMPRA BTC 🦁", f"${price:,.2f}", "---", "---", "Buscando Scalp Rápido")
            except Exception as e: st.error(f"Error en Compra: {e}")
    else:
        precio_entrada = state["compras"][0]
        ganancia_neta = ((price - precio_entrada) / precio_entrada) * 100
        
        # VENTAS: Scalping Rápido (0.55%) o Stop Loss (-2.5%)
        if ganancia_neta >= target_scalp or ganancia_neta <= -2.5:
            try:
                exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / precio_entrada, price)
                profit_usd = (state['monto_total'] * ganancia_neta / 100)
                state["pnl_ganado"] += profit_usd
                state["history"].append({
                    "H": datetime.now().strftime("%H:%M:%S"),
                    "P": f"{ganancia_neta:.2f}%",
                    "USD": f"${profit_usd:.4f}"
                })
                state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                save_state(state)
                enviar_telegram_pro("VENTA BTC 💰", f"${price:,.2f}", f"${profit_usd:.4f}", f"{ganancia_neta:.2f}%", "Operación Cerrada")
            except: pass
        else:
            log_status = f"🚀 En posición: {ganancia_neta:.2f}% (Buscando {target_scalp}%)"

    st.info(log_status)

    # --- TABLA DE HISTORIAL ESTILO TRADING ---
    st.markdown('<p style="color:#FFD700; font-family:Orbitron; font-size:14px; margin-top:20px;">📜 ÚLTIMOS ESCALPES BTC</p>', unsafe_allow_html=True)
    if state["history"]:
        df_hist = pd.DataFrame(state["history"]).tail(5)
        st.table(df_hist)
    else:
        st.write("Esperando primera operación...")

# --- BARRA LATERAL DE CONTROL ---
with st.sidebar:
    st.markdown("### ⚙️ CONTROL")
    st.write(f"Billetera Real: **${wallet_real:.2f} USDT**")
    if st.button("RESETEAR HISTORIAL BTC"):
        state["history"] = []
        save_state(state)
        st.rerun()

time.sleep(10)
st.rerun()