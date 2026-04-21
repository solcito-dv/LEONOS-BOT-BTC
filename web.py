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
    defaults = {"capital_asignado": 10.0, "pnl_acumulado": 0.0, "posiciones": [], "history": []}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: return json.load(f)
        except: return defaults
    return defaults

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=4)
    except: pass

# --- 2. ESTILOS (INTERFAZ OFICIAL) ---
st.set_page_config(page_title="LEONOS BTC | V34.3", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    .neon-panel { border: 2px solid #DC143C; border-radius: 12px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(220, 20, 60, 0.2); }
    .panel-header { background: rgba(220, 20, 60, 0.2); padding: 12px; border-bottom: 1px solid #DC143C; color: #FFFF00 !important; font-family: 'Orbitron'; font-size: 14px; font-weight: 900; text-align: left; }
    .panel-content { padding: 20px; text-align: left; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    .status-msg { color: #FFFFFF; font-style: italic; font-size: 15px; border-left: 4px solid #FFFF00; padding-left: 15px; }
    .burbuja { padding: 12px 20px; border-radius: 30px; font-weight: 800; font-size: 13px; display: inline-block; margin: 8px; border: 1px solid rgba(255,255,255,0.2); }
    .b-entrada { background: #1E90FF; color: white; }
    .b-venta { background: #228B22; color: white; }
    </style>
    """, unsafe_allow_html=True)

state = load_state()

def fetch_data(timeframe, limit=100):
    try:
        mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        return df, mexc
    except: return None, None

df_1m, exchange = fetch_data('1m')
df_15m, _ = fetch_data('15m')

with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:20px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    target_ab = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15, step=0.01)
    target_cz = st.slider("Target Cazadora (%)", 0.10, 1.0, 0.40, step=0.05)
    gap_v = 0.02 

st.markdown('<h1 style="font-family:Orbitron; color:#DC143C;">🦁 LEONOS BTC V34.3</h1>', unsafe_allow_html=True)

if df_1m is not None and df_15m is not None:
    d1 = df_1m.iloc[-1]
    price, rsi, ema9, ema200 = d1['close'], d1['rsi'], d1['ema9'], d1['ema200']
    
    # Radar discreto (Aviso chico en lugar vacío)
    d15 = df_15m.iloc[-1]
    radar_txt = "ALCISTA" if price > d15['ema9'] else "BAJISTA"
    radar_col = "#00FF00" if radar_txt == "ALCISTA" else "#FF0000"

    total_patrimonio = float(state["capital_asignado"]) + float(state["pnl_acumulado"])
    cap_inv = sum(float(p['monto']) for p in state["posiciones"])
    cap_disponible = total_patrimonio - cap_inv
    pnl_clean = state["pnl_acumulado"] if state["pnl_acumulado"] > 0 else 0.0

    # --- DASHBOARD (TAL CUAL ANTES) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA 9/200</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div style="color:#FFFF00; font-size:12px;">EMA 9: ${ema9:,.0f} | EMA 200: ${ema200:,.0f}</div><div style="font-size:10px; color:{radar_col}; margin-top:5px;">Radar 15m: {radar_txt}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">ESTRATEGIA RSI</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div style="color:#FFFF00; font-size:11px; font-weight:bold;">ABEJA < 40 | CAZA < 30</div></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">SALDO LIBRE</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${cap_disponible:.3f}</span><div style="color:#FFFF00; font-size:12px;">CAPITAL: $10.0</div></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${pnl_clean:.4f}</span><div style="color:#00FF00; font-size:12px;">PNL ACUMULADO</div></div></div>', unsafe_allow_html=True)

    if state["posiciones"]:
        st.markdown('<div style="text-align: center; margin-bottom: 20px;">', unsafe_allow_html=True)
        for pos in state["posiciones"]:
            t_obj = target_ab if pos['tipo'] == "Abeja" else target_cz
            st.markdown(f'<div class="burbuja b-entrada">[{pos["tipo"]}] ${pos["precio"]:,.1f}</div><div class="burbuja b-venta">TARGET: {t_obj}%</div><br>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- LÓGICA DE COMPRA ---
    log_msg = "SISTEMA EN PAUSA"
    if bot_encendido:
        log_msg = "Analizando mercado..."
        monto_op = 4.95
        if len(state["posiciones"]) < 2:
            t_compra = None
            if rsi < 40 and price > ema9 and price > ema200 and not any(p['tipo'] == "Abeja" for p in state["posiciones"]):
                t_compra = "Abeja"
            if rsi < 30 and price > ema9 and radar_txt == "ALCISTA" and not any(p['tipo'] == "Cazadora" for p in state["posiciones"]):
                t_compra = "Cazadora"

            if t_compra:
                try:
                    exchange.create_market_buy_order(SYMBOL, monto_op / price)
                    state["posiciones"].append({"precio": price, "monto": monto_op, "tipo": t_compra, "max_alc": price, "be_act": False})
                    save_state(state)
                    send_telegram_msg(f"🦁 COMPRA {t_compra}: ${price:,.2f}")
                except: pass

    # --- LÓGICA DE VENTA ---
    nuevas = []
    for pos in state["posiciones"]:
        neta = ((price - pos['precio']) / pos['precio']) * 100
        if price > pos.get('max_alc', pos['precio']): pos['max_alc'] = price
        if neta >= 0.15: pos['be_act'] = True
        
        sl_d = -1.20
        if pos['be_act']: sl_d = 0.0
        if neta >= 0.30: sl_d = 0.15
        
        t_obj = target_ab if pos['tipo'] == "Abeja" else target_cz
        caida_p = ((price - pos['max_alc']) / pos['max_alc']) * 100
        se_agoto = (neta >= t_obj and caida_p <= -gap_v)

        if neta <= sl_d or se_agoto:
            try:
                exchange.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
                profit = (pos['monto'] * neta / 100)
                state["pnl_acumulado"] += profit
                state["history"].append({"Fecha": datetime.now().strftime('%H:%M:%S'), "Entrada": f"${pos['precio']:,.0f}", "Salida": f"${price:,.0f}", "%": f"{neta:.2f}%", "Profit": f"${profit:.4f}"})
                save_state(state)
                send_telegram_msg(f"💰 VENTA {pos['tipo']}: {neta:.2f}%")
            except: nuevas.append(pos)
        else:
            nuevas.append(pos)
            if bot_encendido: log_msg = f"Operando: {pos['tipo']} ({neta:.2f}%)"
    
    state["posiciones"] = nuevas
    save_state(state)

    # --- PANEL ÚNICO e HISTORIAL ---
    st.markdown(f'<div class="neon-panel"><div class="panel-header">ESTADO DEL MOTOR</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)
    hist_html = '<div style="display: grid; grid-template-columns: 1.3fr 1fr 1fr 1fr 1fr; color: #FFFF00; font-weight: bold; border-bottom: 2px solid #DC143C; padding-bottom:8px;"><div>HORA</div><div>ENTRADA</div><div>SALIDA</div><div>%</div><div>PROFIT</div></div>'
    for h in reversed(state["history"][-10:]):
        color = "#00FF00" if "-" not in h["%"] else "#FF0000"
        hist_html += f'<div style="display: grid; grid-template-columns: 1.3fr 1fr 1fr 1fr 1fr; padding: 8px 0; border-bottom: 1px solid #222;"><div>{h["Fecha"]}</div><div>{h["Entrada"]}</div><div>{h["Salida"]}</div><div style="color:{color}; font-weight:bold;">{h["%"]}</div><div style="color:{color};">{h["Profit"]}</div></div>'
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMOS MOVIMIENTOS</div><div class="panel-content">{hist_html}</div></div>', unsafe_allow_html=True)

time.sleep(15)
st.rerun()