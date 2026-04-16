import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
import requests
from datetime import datetime

# --- 1. CONFIGURACIÓN (LÓGICA SAGRADA) ---
API_KEY_BTC = 'mx0vglJcyb3BIWHjDk' 
SECRET_KEY_BTC = 'de1285d2de1945d2a66e502945c7324b'
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json'
MONTO_OPERACION = 10.0

# CONFIGURACIÓN TELEGRAM (REEMPLAZAR CON TUS DATOS)
TELEGRAM_TOKEN = '8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss'
TELEGRAM_CHAT_ID = '6458029736'

def send_telegram_msg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}&parse_mode=Markdown"
        requests.get(url)
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

# --- 2. DISEÑO Y ESTILOS (OFICIAL: ROJO Y AMARILLO) ---
st.set_page_config(page_title="LEONOS BTC | V19", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    .neon-panel { 
        border: 2px solid #DC143C; 
        border-radius: 12px; 
        background: #050505; 
        margin-bottom: 20px; 
        box-shadow: 0 0 15px rgba(220, 20, 60, 0.2); 
    }
    
    .panel-header { 
        background: rgba(220, 20, 60, 0.2); 
        padding: 12px; 
        border-bottom: 1px solid #DC143C; 
        color: #FFFF00 !important; 
        font-family: 'Orbitron'; 
        font-size: 14px; 
        text-transform: uppercase;
        font-weight: 900;
        letter-spacing: 1px;
    }
    
    .panel-content { padding: 20px; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    .sub-info-yellow { color: #FFFF00 !important; font-size: 12px; margin-top: 5px; font-weight: 800; }
    
    .status-msg { 
        color: #FFFFFF; 
        font-style: italic; 
        font-size: 15px; 
        border-left: 4px solid #FFFF00; 
        padding-left: 15px; 
    }

    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    .stWidgetLabel p, label, .stSelectbox div, .stRadio div { color: #FFFFFF !important; font-size: 14px !important; }
    .sidebar-info { color: #00FF00; font-size: 12px; font-family: 'JetBrains Mono'; margin-top: 10px; }

    .hist-header-row {
        display: grid; 
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr; 
        color: #FFFF00; 
        font-weight: bold; 
        border-bottom: 1px solid #DC143C; 
        padding-bottom: 8px; 
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
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet, exchange = fetch_all()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:18px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    modo = st.radio("INTENSIDAD:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"])
    target_actual = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55, "Tendencia (0.90%)": 0.90}[modo]

st.markdown('<h1 style="font-family:Orbitron; color:#DC143C; margin-bottom:20px;">🦁 LEONOS BTC V19</h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    # DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div class="sub-info-yellow">EMA200: ${ema200:,.0f}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI ACTUAL</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div class="sub-info-yellow">OBJETIVO: < 35</div></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">BILLETERA USDT</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${wallet:.2f}</span><div style="color: #FFFF00; font-size: 12px; margin-top: 5px;">DISPONIBLE</div></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div style="color: #00FF00; font-size: 12px; margin-top: 5px;">TOTAL ACUMULADO</div></div></div>', unsafe_allow_html=True)

    log_msg = "Acechando entrada..."
    if not bot_encendido:
        log_msg = "SISTEMA EN PAUSA MANUAL"
        st.info("⏸️ Bot en pausa.")
    else:
        if not state["in_position"]:
            if rsi < 35 and wallet >= MONTO_OPERACION: 
                try:
                    exchange.create_limit_buy_order(SYMBOL, MONTO_OPERACION / price, price)
                    state.update({"in_position": True, "compras": [price], "monto_total": MONTO_OPERACION})
                    save_state(state)
                    st.success(f"🚀 COMPRA EJECUTADA: BTC a ${price:,.0f}")
                    send_telegram_msg(f"🦁 *LEONOS BTC*\n🚀 *COMPRA*\n💰 Precio: ${price:,.0f}\n🎯 Objetivo: +{target_actual}%")
                except: pass
        else:
            promedio = state["compras"][0]
            neta = ((price - promedio) / promedio) * 100
            
            # Lógica de Venta (TP o SL)
            if neta >= target_actual or neta <= -2.5:
                tipo_venta = "TAKE PROFIT" if neta >= target_actual else "STOP LOSS"
                try:
                    exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / promedio, price)
                    prof = (state['monto_total'] * neta / 100)
                    state["history"].append({"Fecha": datetime.now().strftime("%H:%M"), "Entrada": f"${promedio:,.0f}", "Salida": f"${price:,.0f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"})
                    state["pnl_acumulado"] += prof
                    state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                    save_state(state)
                    
                    if neta >= 0: st.balloons(); st.success(f"💰 VENTA EXITOSA ({tipo_venta}): {neta:.2f}%")
                    else: st.error(f"📉 VENTA POR SEGURIDAD ({tipo_venta}): {neta:.2f}%")
                    
                    send_telegram_msg(f"🦁 *LEONOS BTC*\n🏁 *VENTA ({tipo_venta})*\n📥 Entrada: ${promedio:,.0f}\n📤 Salida: ${price:,.0f}\n📊 Neto: {neta:.2f}%\n💵 Profit: ${prof:.4f}")
                except: pass
            else: 
                log_msg = f"DENTRO: {neta:.2f}% (Meta {target_actual}%)"
                st.warning(f"⚖️ Posición abierta: {neta:.2f}%")

    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    hist_header = '<div class="hist-header-row"><div>HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>PROFIT</div></div>'
    hist_body = ""
    if state["history"]:
        for op in reversed(state["history"][-10:]):
            color_p = "#00FF00" if "-" not in op["Neto"] else "#FF0000"
            hist_body += f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; padding: 10px 0; border-bottom: 1px solid #222; color: white; font-size: 13px;"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div style="color:{color_p}; font-weight:bold;">{op["Neto"]}</div><div style="color:{color_p};">{op["Profit"]}</div></div>'
    
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMAS OPERACIONES BTC</div><div class="panel-content">{hist_header}{hist_body}</div></div>', unsafe_allow_html=True)

time.sleep(15)
st.rerun()