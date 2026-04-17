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
    # DATOS EXACTOS SOLICITADOS: $10.077 capital y $0.0077 ganancia
    data_real = {
        "capital_asignado": 10.077, 
        "pnl_acumulado": 0.0077,
        "posiciones": [],
        "history": []
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                return state
        except: pass
    return data_real

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except: pass

# --- 2. ESTILOS ---
st.set_page_config(page_title="LEONOS BTC | V32.2", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    .neon-panel { border: 2px solid #DC143C; border-radius: 12px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(220, 20, 60, 0.2); }
    .panel-header { background: rgba(220, 20, 60, 0.2); padding: 12px; border-bottom: 1px solid #DC143C; color: #FFFF00 !important; font-family: 'Orbitron'; font-size: 14px; font-weight: 900; }
    .panel-content { padding: 20px; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    .status-msg { color: #FFFFFF; font-style: italic; font-size: 15px; border-left: 4px solid #FFFF00; padding-left: 15px; }
    .burbuja { padding: 12px 20px; border-radius: 30px; font-weight: 800; font-size: 13px; display: inline-block; margin: 8px; border: 1px solid rgba(255,255,255,0.2); }
    .b-entrada { background: #1E90FF; color: white; }
    .b-venta { background: #228B22; color: white; }
    .b-stop { background: #B22222; color: white; }
    </style>
    """, unsafe_allow_html=True)

state = load_state()

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
        return df.iloc[-1], mexc
    except: return None, None

data, exchange = fetch_all()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:20px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    st.markdown("**ESTRATEGIA CAZADORA**")
    target_cazadora = st.slider("Target Cazadora (%)", 0.20, 2.0, 0.35, step=0.05)
    st.markdown("---")
    st.markdown("**ESTRATEGIA ABEJA**")
    target_abeja = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15, step=0.01)

st.markdown('<h1 style="font-family:Orbitron; color:#DC143C;">🦁 LEONOS BTC V32.2</h1>', unsafe_allow_html=True)

if data is not None:
    price, rsi, ema200 = data['close'], data['rsi'], data['ema200']
    capital_total_real = state["capital_asignado"] + state["pnl_acumulado"]
    capital_invertido = sum(pos['monto'] for pos in state["posiciones"])
    capital_disponible = capital_total_real - capital_invertido

    # DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div style="color:#FFFF00; font-size:12px;">EMA200: ${ema200:,.0f}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI OBJETIVO</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div style="color:#FFFF00; font-size:11px; font-weight:bold;">ABEJA: < 45 | CAZADORA: < 35</div></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">SALDO DISPONIBLE</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${capital_disponible:.3f}</span><div style="color:#FFFF00; font-size:12px;">USDT PARA OPERAR</div></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div style="color:#00FF00; font-size:12px;">INCLUYE 0.077% INICIAL</div></div></div>', unsafe_allow_html=True)

    # --- 5. TARJETAS (SOLO SI HAY OPERACIONES) ---
    if state["posiciones"]:
        st.markdown('<div style="text-align: center; margin-bottom: 20px;">', unsafe_allow_html=True)
        for i, pos in enumerate(state["posiciones"]):
            pct = target_abeja if pos.get("tipo") == "Abeja" else target_cazadora
            v_target = pos['precio'] * (1 + pct/100)
            v_stop = pos['precio'] * 0.975
            st.markdown(f"""
                <div class="burbuja b-entrada">[{pos.get('tipo')}] ENTRADA: ${pos['precio']:,.1f}</div>
                <div class="burbuja b-venta">SALIDA ({pct}%): ${v_target:,.1f}</div>
                <div class="burbuja b-stop">STOP LOSS: ${v_stop:,.1f}</div><br>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 6. LÓGICA Y SITUACIÓN ACTUAL ---
    log_msg = "Monitoreando señales..."
    if bot_encendido:
        # COMPRAS
        ya_abeja = any(p['tipo'] == "Abeja" for p in state["posiciones"])
        ya_cazadora = any(p['tipo'] == "Cazadora" for p in state["posiciones"])
        
        if not ya_abeja and rsi < 45 and price > ema200 and capital_disponible > 5:
            monto = capital_disponible * 0.5
            state["posiciones"].append({"precio": price, "monto": monto, "tipo": "Abeja"})
            send_telegram_msg(f"🐝 ABEJA COMPRÓ: ${price:,.0f}")
            save_state(state)
        elif not ya_cazadora and rsi < 35 and capital_disponible > 5:
            monto = capital_disponible 
            state["posiciones"].append({"precio": price, "monto": monto, "tipo": "Cazadora"})
            send_telegram_msg(f"🦁 CAZADORA COMPRÓ: ${price:,.0f}")
            save_state(state)

        # VENTAS
        nuevas_pos = []
        for pos in state["posiciones"]:
            pct_actual = target_abeja if pos.get("tipo") == "Abeja" else target_cazadora
            neta = ((price - pos['precio']) / pos['precio']) * 100
            if neta >= pct_actual or neta <= -2.5:
                try:
                    prof = (pos['monto'] * neta / 100)
                    state["pnl_acumulado"] += prof
                    state["history"].append({
                        "Fecha": datetime.now().strftime("%d/%m %H:%M"), 
                        "Entrada": f"${pos['precio']:,.0f}", "Salida": f"${price:,.0f}", 
                        "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"
                    })
                    send_telegram_msg(f"💰 VENTA [{pos.get('tipo')}]: {neta:.2f}%")
                    save_state(state)
                except: nuevas_pos.append(pos)
            else:
                nuevas_pos.append(pos)
                log_msg = f"Operación [{pos.get('tipo')}] activa: {neta:.2f}%"
        state["posiciones"] = nuevas_pos
        save_state(state)

    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # --- 7. HISTORIAL ---
    contenido_hist = '<div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 1fr 1fr; color: #FFFF00; font-weight: bold; border-bottom: 3px solid #DC143C; padding-bottom:8px; font-size:14px;"><div>FECHA/HORA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>PROFIT</div></div>'
    for op in reversed(state["history"][-10:]):
        color_neto = "#00FF00" if "-" not in op["Neto"] else "#FF0000"
        contenido_hist += f'<div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 1fr 1fr; padding: 10px 0; border-bottom: 1px solid #222; color: white; font-size: 13px;"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div style="color:{color_neto}; font-weight:bold;">{op["Neto"]}</div><div style="color:{color_neto};">{op["Profit"]}</div></div>'
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMAS OPERACIONES</div><div class="panel-content">{contenido_hist}</div></div>', unsafe_allow_html=True)

time.sleep(15)
st.rerun()