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
        requests.get(url, timeout=5)
    except: pass

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"capital_asignado": 10.0, "pnl_acumulado": 0.0, "posiciones": [], "history": [], "last_cz_sell_time": 0}

def save_state(state_data):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state_data, f, indent=4)
    except: pass

# --- 2. INTERFAZ Y ESTILOS ---
st.set_page_config(page_title="LEONOS BTC", layout="wide")

# Estilos inyectados una sola vez para evitar parpadeos de CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    .neon-panel { border: 2px solid #DC143C; border-radius: 12px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(220, 20, 60, 0.2); }
    .panel-header { background: rgba(220, 20, 60, 0.2); padding: 12px; border-bottom: 1px solid #DC143C; color: #FFFF00 !important; font-family: 'Orbitron'; font-size: 14px; font-weight: 900; }
    .panel-content { padding: 15px; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    .burbuja { padding: 10px 18px; border-radius: 30px; font-weight: 800; font-size: 12px; display: inline-block; margin: 5px; border: 1px solid rgba(255,255,255,0.2); }
    .b-compra { background: #1E90FF; color: white; }
    .b-venta { background: #00FF00; color: black; }
    .b-sl { background: #FF0000; color: white; }
    /* Eliminar animaciones de carga para suavizar el refresh */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

state = load_state()
main_placeholder = st.empty()

with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:20px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    target_ab = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15, step=0.01)
    target_cz = st.slider("Target Cazadora (%)", 0.10, 1.0, 0.40, step=0.05)

# --- 3. PROCESAMIENTO DE DATOS ---
try:
    mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
    
    # Obtener velas (limit 205 para EMA 200)
    b1 = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=205)
    df = pd.DataFrame(b1, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    # Radar 15m
    b15 = mexc.fetch_ohlcv(SYMBOL, timeframe='15m', limit=50)
    df15 = pd.DataFrame(b15, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df15['ema9'] = df15['close'].ewm(span=9, adjust=False).mean()
    
    curr_p = df.iloc[-1]['close']
    curr_rsi = df.iloc[-1]['rsi']
    curr_ema9 = df.iloc[-1]['ema9']
    curr_ema200 = df.iloc[-1]['ema200']
    radar_15_up = curr_p > df15.iloc[-1]['ema9']
    
    log_msg = "Analizando..." if bot_encendido else "SISTEMA EN PAUSA"
    
    # --- MOTOR DE TRADING ---
    if bot_encendido and len(state["posiciones"]) < 2:
        t_buy = None
        if curr_rsi < 40 and curr_p > curr_ema9 and not any(p['tipo']=="Abeja" for p in state["posiciones"]): t_buy = "Abeja"
        elif curr_rsi < 30 and curr_p > curr_ema9 and radar_15_up and not any(p['tipo']=="Cazadora" for p in state["posiciones"]): t_buy = "Cazadora"
        
        if t_buy:
            try:
                mexc.create_market_buy_order(SYMBOL, 4.95 / curr_p)
                state["posiciones"].append({"precio": curr_p, "monto": 4.95, "tipo": t_buy, "max_alc": curr_p})
                save_state(state)
                send_telegram_msg(f"🦁 *COMPRA {t_buy.upper()}*\nBTC: ${curr_p:,.2f}")
            except: pass

    nuevas_pos = []
    for pos in state["posiciones"]:
        neta = ((curr_p - pos['precio']) / pos['precio']) * 100
        if curr_p > pos.get('max_alc', pos['precio']): pos['max_alc'] = curr_p
        
        sl_val = 0.15 if neta >= 0.30 else (0.0 if neta >= 0.15 else -1.20)
        t_val = target_ab if pos['tipo'] == "Abeja" else target_cz
        se_agoto = (neta >= t_val and ((curr_p - pos['max_alc']) / pos['max_alc']) * 100 <= -0.02)
        
        if neta <= sl_val or se_agoto:
            try:
                mexc.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
                profit = (pos['monto'] * neta / 100)
                state["pnl_acumulado"] += profit
                state["history"].append({"Fecha": datetime.now().strftime('%d/%m %H:%M'), "Entrada": f"${pos['precio']:,.0f}", "Salida": f"${curr_p:,.0f}", "%": f"{neta:.2f}%", "Profit": f"${profit:.4f}"})
                save_state(state)
                send_telegram_msg(f"💰 *VENTA {pos['tipo'].upper()}*\nBTC: ${curr_p:,.2f}\nGANANCIA: ${profit:.4f}\nTOTAL: {neta:.2f}%")
            except: nuevas_pos.append(pos)
        else:
            nuevas_pos.append(pos)
            if bot_encendido: log_msg = f"Operando: {pos['tipo']} ({neta:.2f}%)"
    
    state["posiciones"] = nuevas_pos
    save_state(state)

    # --- 4. RENDERIZADO EN EL PLACEHOLDER ---
    with main_placeholder.container():
        st.markdown('<h1 style="font-family:Orbitron; color:#DC143C; margin-bottom:10px;">🦁 LEONOS BTC</h1>', unsafe_allow_html=True)
        
        c_inv = sum(float(p['monto']) for p in state["posiciones"])
        c_disp = (state["capital_asignado"] + state["pnl_acumulado"]) - c_inv
        
        # Dashboard
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.markdown(f'<div class="neon-panel" style="height:165px;"><div class="panel-header">PRECIO & EMA 9/200</div><div class="panel-content"><span class="price-main">${curr_p:,.0f}</span><div style="color:#FFFF00; font-size:12px; margin-top:5px;">EMA 9: ${curr_ema9:,.0f} | 200: ${curr_ema200:,.0f}</div><div style="font-size:11px; color:{"#00FF00" if radar_15_up else "#FF0000"}; font-weight:bold;">RADAR 15M: {"ALCISTA" if radar_15_up else "BAJISTA"}</div></div></div>', unsafe_allow_html=True)
        with col2: st.markdown(f'<div class="neon-panel" style="height:165px;"><div class="panel-header">ESTRATEGIA RSI</div><div class="panel-content"><span class="price-main">{curr_rsi:.2f}</span><div style="color:#FFFF00; font-size:11px; font-weight:bold; margin-top:15px;">ABEJA < 40 | CAZA < 30</div></div></div>', unsafe_allow_html=True)
        with col3: st.markdown(f'<div class="neon-panel" style="height:165px;"><div class="panel-header">SALDO LIBRE</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${c_disp:.3f}</span><div style="color:#FFFF00; font-size:12px; margin-top:15px;">CAPITAL INICIAL: $10.0</div></div></div>', unsafe_allow_html=True)
        with col4: st.markdown(f'<div class="neon-panel" style="height:165px;"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div style="color:#00FF00; font-size:12px; margin-top:15px;">PNL ACUMULADO</div></div></div>', unsafe_allow_html=True)

        # Operaciones
        if state["posiciones"]:
            st.markdown('<div style="text-align: center; margin-bottom: 20px;">', unsafe_allow_html=True)
            for pos in state["posiciones"]:
                n_now = ((curr_p - pos['precio']) / pos['precio']) * 100
                v_target = pos['precio'] * (1 + (target_ab if pos['tipo']=="Abeja" else target_cz)/100)
                st_target = pos['precio'] * (1 + (0.15 if n_now >= 0.30 else (0.0 if n_now >= 0.15 else -1.20))/100)
                st.markdown(f'<div class="burbuja b-compra">ENTRADA {pos["tipo"].upper()}: ${pos["precio"]:,.1f}</div><div class="burbuja b-venta">VENTA: ${v_target:,.1f}</div><div class="burbuja b-sl">ST: ${st_target:,.1f}</div><br>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="neon-panel"><div class="panel-header">ESTADO DEL MOTOR</div><div class="panel-content"><div style="color:white; font-style:italic; border-left:4px solid #FFFF00; padding-left:15px;">"{log_msg}"</div></div></div>', unsafe_allow_html=True)
        
        # Historial
        h_list = ""
        for h in reversed(state["history"][-10:]):
            h_c = "#00FF00" if "-" not in h["%"] else "#FF0000"
            h_list += f'<div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 0.8fr 1fr; padding:8px 0; border-bottom:1px solid #222; font-size:13px;"><div>{h["Fecha"]}</div><div>{h["Entrada"]}</div><div>{h["Salida"]}</div><div style="color:{h_c}; font-weight:bold;">{h["%"]}</div><div style="color:{h_c};">{h["Profit"]}</div></div>'
        st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMOS MOVIMIENTOS</div><div class="panel-content"><div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 0.8fr 1fr; color:#FFFF00; font-weight:bold; border-bottom:2px solid #DC143C; padding-bottom:8px;"><div>FECHA</div><div>ENTRADA</div><div>SALIDA</div><div>%</div><div>PROFIT</div></div>{h_list}</div></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")

time.sleep(10)
st.rerun()