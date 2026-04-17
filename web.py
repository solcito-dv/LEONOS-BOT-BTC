import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
import requests
from datetime import datetime

# --- 1. CONFIGURACIÓN (LÓGICA SAGRADA BLINDADA) ---
API_KEY_BTC = 'mx0vglJcyb3BIWHjDk' 
SECRET_KEY_BTC = 'de1285d2de1945d2a66e502945c7324b'
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json'

CAPITAL_INICIAL = 10.0 

# CONFIGURACIÓN TELEGRAM (Tus credenciales se mantienen intactas)
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
                if "posiciones" not in state: state["posiciones"] = []
                if "history" not in state: state["history"] = []
                return state
        except: pass
    return {"posiciones": [], "history": [], "pnl_acumulado": 0.0}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

# --- 2. DISEÑO Y ESTILOS (V22 - FIXED COLORS) ---
st.set_page_config(page_title="LEONOS BTC | V22", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    /* Fondo General */
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Paneles Neon */
    .neon-panel { border: 2px solid #DC143C; border-radius: 12px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(220, 20, 60, 0.1); }
    .panel-header { background: rgba(220, 20, 60, 0.2); padding: 12px; border-bottom: 1px solid #DC143C; color: #FFFF00 !important; font-family: 'Orbitron'; font-size: 14px; text-transform: uppercase; font-weight: 900; letter-spacing: 1px; }
    .panel-content { padding: 20px; }
    
    /* Texto de Radio Buttons (Fix Gris) */
    div[data-testid="stWidgetLabel"] p { color: #FFFFFF !important; font-weight: bold; }
    div[role="radiogroup"] label { color: #FFFFFF !important; }

    /* Precios y Burbujas */
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    .sub-info-yellow { color: #FFFF00 !important; font-size: 12px; margin-top: 5px; font-weight: 800; }
    .burbuja { padding: 10px 20px; border-radius: 30px; font-weight: 800; font-size: 13px; display: inline-block; margin: 5px; border: 1px solid rgba(255,255,255,0.1); }
    .b-entrada { background: #1E90FF; color: white; }
    .b-venta { background: #228B22; color: white; }
    .b-stop { background: #B22222; color: white; }

    /* Historial */
    .hist-header-row { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; color: #FFFF00 !important; font-weight: 900; border-bottom: 2px solid #DC143C; padding: 10px 5px; font-size: 13px; background: rgba(220,20,60,0.1); }
    .hist-item { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; padding: 12px 5px; border-bottom: 1px solid #222; color: white; font-size: 13px; align-items: center; }
    
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MOTOR ---
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
data, wallet_real, exchange = fetch_all()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:18px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    # El CSS de arriba arregla el color gris de este Radio
    modo = st.radio("INTENSIDAD DE TRADING:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"])
    target_pct = {"Scalper (0.35%)": 0.35, "Equilibrado (0.55%)": 0.55, "Tendencia (0.90%)": 0.90}[modo]

st.markdown('<h1 style="font-family:Orbitron; color:#DC143C; margin-bottom:20px;">🦁 LEONOS BTC V22</h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    
    capital_total_bot = CAPITAL_INICIAL + state["pnl_acumulado"]
    monto_cada_op = capital_total_bot / 2
    capital_en_uso = sum(pos['monto'] for pos in state["posiciones"])

    # DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div class="sub-info-yellow">EMA200: ${ema200:,.0f}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div class="sub-info-yellow">OBJETIVO: < 35</div></div></div>', unsafe_allow_html=True)
    with c3: 
        disponible = capital_total_bot - capital_en_uso
        st.markdown(f'<div class="neon-panel"><div class="panel-header">DISPONIBLE</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${disponible:.2f}</span><div class="sub-info-yellow">FONDO PROPIO</div></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">PROFIT</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div style="color: #00FF00; font-size: 12px; margin-top: 5px;">ACUMULADO</div></div></div>', unsafe_allow_html=True)

    # --- 5. BURBUJAS DE OPERACIÓN (FIJAS) ---
    if state["posiciones"]:
        st.markdown('<div style="text-align: center; margin-bottom: 20px;">', unsafe_allow_html=True)
        for i, pos in enumerate(state["posiciones"]):
            v_target = pos['precio'] * (1 + target_pct/100)
            v_stop = pos['precio'] * 0.975
            st.markdown(f"""
                <div class="burbuja b-entrada">OP {i+1} | ENTRADA: ${pos['precio']:,.0f}</div>
                <div class="burbuja b-venta">VENTA: ${v_target:,.0f}</div>
                <div class="burbuja b-stop">STOP: ${v_stop:,.0f}</div>
                <br>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 6. LÓGICA ---
    log_msg = "Acechando mercado..."
    if bot_encendido:
        # COMPRA 1
        if len(state["posiciones"]) == 0 and rsi < 35 and wallet_real >= monto_cada_op:
            try:
                exchange.create_limit_buy_order(SYMBOL, monto_cada_op / price, price)
                state["posiciones"].append({"precio": price, "monto": monto_cada_op})
                save_state(state)
                send_telegram_msg(f"🦁 *COMPRA 1*\nEntrada: ${price:,.0f}")
            except: pass
        
        # COMPRA 2
        elif len(state["posiciones"]) == 1:
            if price <= (state["posiciones"][0]["precio"] * 0.99) and wallet_real >= monto_cada_op:
                try:
                    exchange.create_limit_buy_order(SYMBOL, monto_cada_op / price, price)
                    state["posiciones"].append({"precio": price, "monto": monto_cada_op})
                    save_state(state)
                    send_telegram_msg(f"🦁 *COMPRA 2*\nEntrada: ${price:,.0f}")
                except: pass

        # VENTA
        nuevas_pos = []
        for pos in state["posiciones"]:
            neta = ((price - pos['precio']) / pos['precio']) * 100
            if neta >= target_pct or neta <= -2.5:
                try:
                    exchange.create_limit_sell_order(SYMBOL, pos['monto'] / pos['precio'], price)
                    prof = (pos['monto'] * neta / 100)
                    state["pnl_acumulado"] += prof
                    state["history"].append({"Fecha": datetime.now().strftime("%d/%m %H:%M"), "Entrada": f"${pos['precio']:,.0f}", "Salida": f"${price:,.0f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"})
                    save_state(state)
                    send_telegram_msg(f"🦁 *VENTA*\nNeto: {neta:.2f}% | Profit: ${prof:.4f}")
                except: nuevas_pos.append(pos)
            else: 
                nuevas_pos.append(pos)
                log_msg = f"Operando: {neta:.2f}%"
        state["posiciones"] = nuevas_pos
        save_state(state)

    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # --- 8. HISTORIAL (CABEZALES CORREGIDOS) ---
    st.markdown('<div class="neon-panel"><div class="panel-header">📜 ÚLTIMAS OPERACIONES BTC</div><div class="panel-content">', unsafe_allow_html=True)
    st.markdown('<div class="hist-header-row"><div>FECHA/HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>PROFIT</div></div>', unsafe_allow_html=True)
    
    for op in reversed(state["history"][-10:]):
        c_neto = "#00FF00" if "-" not in op["Neto"] else "#FF0000"
        st.markdown(f"""
            <div class="hist-item">
                <div>{op["Fecha"]}</div>
                <div>{op["Entrada"]}</div>
                <div>{op["Salida"]}</div>
                <div style="color:{c_neto}; font-weight:bold;">{op["Neto"]}</div>
                <div style="color:{c_neto};">{op["Profit"]}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

time.sleep(15)
st.rerun()