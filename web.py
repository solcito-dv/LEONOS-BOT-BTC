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

# Datos de Telegram
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
                state.setdefault("pnl_acumulado", 0.0)
                state.setdefault("posiciones", [])
                state.setdefault("history", [])
                return state
        except: pass
    return {"posiciones": [], "history": [], "pnl_acumulado": 0.0}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=4)

# --- 2. ESTILOS PROFESIONALES (FIX CABEZALES Y COLORES) ---
st.set_page_config(page_title="LEONOS BTC | V23", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    
    /* Sidebar Fix (Texto Blanco) */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    [data-testid="stSidebar"] .stText, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #FFFFFF !important; font-weight: bold;
    }

    /* Paneles */
    .neon-panel { border: 2px solid #DC143C; border-radius: 10px; background: #080808; margin-bottom: 20px; overflow: hidden; }
    .panel-header { background: rgba(220, 20, 60, 0.25); padding: 10px 15px; border-bottom: 1px solid #DC143C; color: #FFFF00 !important; font-family: 'Orbitron'; font-size: 13px; font-weight: 900; }
    .panel-content { padding: 15px; }
    
    .price-main { color: #FFFFFF; font-size: 38px; font-weight: 900; font-family: 'Orbitron'; line-height: 1.2; }
    .sub-info-yellow { color: #FFFF00 !important; font-size: 12px; font-weight: 800; }

    /* Burbujas */
    .burbuja { padding: 8px 15px; border-radius: 20px; font-weight: 800; font-size: 12px; display: inline-block; margin: 5px; border: 1px solid rgba(255,255,255,0.1); }
    .b-entrada { background: #1E90FF; color: #FFF; }
    .b-venta { background: #228B22; color: #FFF; }
    .b-stop { background: #B22222; color: #FFF; }

    /* Historial Corregido */
    .hist-container { background: #050505; border: 1px solid #222; border-radius: 5px; margin-top: 10px; }
    .hist-header-row { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; padding: 10px; background: rgba(220, 20, 60, 0.15); color: #FFFF00; font-weight: 900; font-size: 11px; border-bottom: 1px solid #DC143C; }
    .hist-item { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr 1fr; padding: 10px; border-bottom: 1px solid #151515; font-size: 12px; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. PROCESAMIENTO ---
def fetch_all():
    try:
        mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=50)
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

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:18px;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    # Limpieza de duplicados y fuente blanca vía CSS superior
    modo_label = st.radio("INTENSIDAD:", ["Scalper (0.35%)", "Equilibrado (0.55%)", "Tendencia (0.90%)"], index=1)
    target_pct = float(modo_label.split('(')[1].split('%')[0])

st.markdown('<h2 style="font-family:Orbitron; color:#DC143C;">🦁 LEONOS BTC V23</h2>', unsafe_allow_html=True)

if data is not None:
    price = data['close']
    rsi = data['rsi']
    
    # DATOS REALES DE CAPITAL
    capital_en_posiciones = sum(pos['monto'] for pos in state["posiciones"])
    # El capital total que el bot "cree" que tiene es su base de 10 + lo que ha ganado
    capital_total_registrado = 10.0 + state["pnl_acumulado"]

    # DASHBOARD
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO BTC</div><div class="panel-content"><span class="price-main">${price:,.0f}</span></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI (1M)</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span></div></div>', unsafe_allow_html=True)
    with c3: 
        # Aquí mostramos cuánto capital del bot está trabajando ahora mismo
        st.markdown(f'<div class="neon-panel"><div class="panel-header">CAPITAL EN USO</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${capital_en_posiciones:.2f}</span></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">HISTÓRICO PNL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span></div></div>', unsafe_allow_html=True)

    # --- 5. BURBUJAS DE OPERACIÓN ACTIVA ---
    if state["posiciones"]:
        st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
        for i, pos in enumerate(state["posiciones"]):
            v_target = pos['precio'] * (1 + target_pct/100)
            v_stop = pos['precio'] * 0.975
            st.markdown(f"""
                <div class="burbuja b-entrada">OP {i+1} | ENTRADA: ${pos['precio']:,.0f}</div>
                <div class="burbuja b-venta">VENTA EN: ${v_target:,.0f}</div>
                <div class="burbuja b-stop">STOP LOSS: ${v_stop:,.0f}</div><br>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 6. MOTOR DE TRADING ---
    if bot_encendido:
        # Lógica de venta (Cierre de operaciones actuales)
        nuevas_pos = []
        for pos in state["posiciones"]:
            rendimiento = ((price - pos['precio']) / pos['precio']) * 100
            if rendimiento >= target_pct or rendimiento <= -2.5:
                try:
                    exchange.create_limit_sell_order(SYMBOL, pos['monto'] / pos['precio'], price)
                    ganancia = (pos['monto'] * rendimiento / 100)
                    state["pnl_acumulado"] += ganancia
                    state["history"].append({
                        "Fecha": datetime.now().strftime("%d/%m %H:%M"),
                        "Entrada": f"${pos['precio']:,.0f}",
                        "Salida": f"${price:,.0f}",
                        "Neto": f"{rendimiento:.2f}%",
                        "Profit": f"${ganancia:.4f}"
                    })
                    save_state(state)
                    send_telegram_msg(f"🦁 VENTA REALIZADA\nNeto: {rendimiento:.2f}%\nProfit: ${ganancia:.4f}")
                except: nuevas_pos.append(pos)
            else: nuevas_pos.append(pos)
        state["posiciones"] = nuevas_pos
        save_state(state)

    # --- 7. HISTORIAL PROFESIONAL ---
    st.markdown('<div class="neon-panel"><div class="panel-header">📜 REGISTRO DE OPERACIONES</div><div class="panel-content">', unsafe_allow_html=True)
    st.markdown("""
        <div class="hist-container">
            <div class="hist-header-row">
                <div>FECHA/HORA</div><div>ENTRADA</div><div>SALIDA</div><div>NETO</div><div>PROFIT</div>
            </div>
    """, unsafe_allow_html=True)
    
    for op in reversed(state["history"][-10:]):
        color = "#00FF00" if "-" not in op["Neto"] else "#FF0000"
        st.markdown(f"""
            <div class="hist-item">
                <div>{op['Fecha']}</div><div>{op['Entrada']}</div><div>{op['Salida']}</div>
                <div style="color:{color}; font-weight:bold;">{op['Neto']}</div>
                <div style="color:{color};">{op['Profit']}</div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div></div></div>', unsafe_allow_html=True)

time.sleep(15)
st.rerun()