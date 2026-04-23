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
                data = json.load(f)
                if "posiciones" not in data: data["posiciones"] = []
                if "history" not in data: data["history"] = []
                # Actualizamos el capital asignado a 30 si el archivo tiene el valor viejo
                if data.get("capital_asignado", 0) < 30.0: data["capital_asignado"] = 30.0
                return data
        except: pass
    return {"capital_asignado": 30.0, "pnl_acumulado": 0.0, "posiciones": [], "history": []}

def save_state(state_data):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Error al guardar: {e}")

# --- 2. INTERFAZ ---
st.set_page_config(page_title="LEONOS BTC", layout="wide")

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
    </style>
    """, unsafe_allow_html=True)

state = load_state()

with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:20px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    target_ab = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15, step=0.01)
    target_cz = st.slider("Target Cazadora (%)", 0.10, 1.0, 0.40, step=0.05)

# --- 3. LÓGICA DE DATOS ---
try:
    mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
    
    b1 = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=205)
    df = pd.DataFrame(b1, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    b15 = mexc.fetch_ohlcv(SYMBOL, timeframe='15m', limit=50)
    df15 = pd.DataFrame(b15, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    ema9_15m = df15['close'].ewm(span=9, adjust=False).mean().iloc[-1]
    
    price = df.iloc[-1]['close']
    rsi = df.iloc[-1]['rsi']
    ema9 = df.iloc[-1]['ema9']
    ema200 = df.iloc[-1]['ema200']
    radar_up = price > ema9_15m

    # --- MOTOR ---
    log_msg = "Analizando..." if bot_encendido else "SISTEMA EN PAUSA"
    
    if bot_encendido and len(state["posiciones"]) < 2:
        tipo_c = None
        if rsi < 40 and price > ema9 and not any(p['tipo']=="Abeja" for p in state["posiciones"]): tipo_c = "Abeja"
        elif rsi < 30 and price > ema9 and radar_up and not any(p['tipo']=="Cazadora" for p in state["posiciones"]): tipo_c = "Cazadora"
        
        if tipo_c:
            # INTERÉS COMPUESTO: Capital Base + Ganancias, dividido en 2 posiciones
            saldo_disponible = state["capital_asignado"] + state["pnl_acumulado"]
            monto_operacion = (saldo_disponible / 2) - 0.05 # Margen para comisiones
            
            try:
                mexc.create_market_buy_order(SYMBOL, monto_operacion / price)
                state["posiciones"].append({"precio": price, "monto": monto_operacion, "tipo": tipo_c, "max_alc": price})
                save_state(state)
                send_telegram_msg(f"🦁 *COMPRA {tipo_c.upper()}*\nBTC: ${price:,.2f}\nMONTO: ${monto_operacion:.2f}")
            except: pass

    nuevas = []
    for pos in state["posiciones"]:
        neta = ((price - pos['precio']) / pos['precio']) * 100
        if price > pos.get('max_alc', pos['precio']): pos['max_alc'] = price
        
        sl_val = 0.15 if neta >= 0.30 else (0.0 if neta >= 0.15 else -1.20)
        t_obj = target_ab if pos['tipo'] == "Abeja" else target_cz
        se_agoto = (neta >= t_obj and ((price - pos['max_alc']) / pos['max_alc']) * 100 <= -0.02)
        
        if neta <= sl_val or se_agoto:
            try:
                mexc.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
                profit = (pos['monto'] * neta / 100)
                state["pnl_acumulado"] += profit
                state["history"].append({"Fecha": datetime.now().strftime('%d/%m %H:%M'), "Entrada": f"${pos['precio']:,.0f}", "Salida": f"${price:,.0f}", "%": f"{neta:.2f}%", "Profit": f"${profit:.4f}"})
                save_state(state)
                send_telegram_msg(f"💰 *VENTA {pos['tipo'].upper()}*\nBTC: ${price:,.2f}\nGANANCIA: ${profit:.4f}")
            except: nuevas.append(pos)
        else:
            nuevas.append(pos)
            log_msg = f"Operando: {pos['tipo']} ({neta:.2f}%)"
            
    state["posiciones"] = nuevas
    save_state(state)

    # --- DIBUJO ---
    st.markdown('<h1 style="font-family:Orbitron; color:#DC143C;">🦁 LEONOS BTC</h1>', unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel" style="height:165px;"><div class="panel-header">PRECIO & EMA 9/200</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div style="color:#FFFF00; font-size:12px; margin-top:5px;">EMA 9: ${ema9:,.0f} | 200: ${ema200:,.0f}</div><div style="font-size:11px; color:{"#00FF00" if radar_up else "#FF0000"}; font-weight:bold;">RADAR 15M: {"ALCISTA" if radar_up else "BAJISTA"}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel" style="height:165px;"><div class="panel-header">ESTRATEGIA RSI</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div style="color:#FFFF00; font-size:11px; font-weight:bold; margin-top:15px;">ABEJA < 40 | CAZA < 30</div></div></div>', unsafe_allow_html=True)
    with c3: 
        cap_total = state["capital_asignado"] + state["pnl_acumulado"]
        cap_inv = sum(p["monto"] for p in state["posiciones"])
        st.markdown(f'<div class="neon-panel" style="height:165px;"><div class="panel-header">SALDO LIBRE</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${cap_total - cap_inv:.3f}</span><div style="color:#FFFF00; font-size:12px; margin-top:15px;">CAPITAL BASE: $30.0</div></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel" style="height:165px;"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div style="color:#00FF00; font-size:12px; margin-top:15px;">PNL ACUMULADO</div></div></div>', unsafe_allow_html=True)

    if state["posiciones"]:
        st.markdown('<div style="text-align: center; margin-bottom: 20px;">', unsafe_allow_html=True)
        for pos in state["posiciones"]:
            n_cur = ((price - pos['precio']) / pos['precio']) * 100
            p_v = pos['precio'] * (1 + (target_ab if pos['tipo']=="Abeja" else target_cz)/100)
            p_s = pos['precio'] * (1 + (0.15 if n_cur >= 0.30 else (0.0 if n_cur >= 0.15 else -1.20))/100)
            st.markdown(f'<div class="burbuja b-compra">ENTRADA {pos["tipo"].upper()}: ${pos["precio"]:,.1f}</div><div class="burbuja b-venta">VENTA: ${p_v:,.1f}</div><div class="burbuja b-sl">ST: ${p_s:,.1f}</div><br>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="neon-panel"><div class="panel-header">ESTADO DEL MOTOR</div><div class="panel-content"><div style="color:white; font-style:italic; border-left:4px solid #FFFF00; padding-left:15px;">"{log_msg}"</div></div></div>', unsafe_allow_html=True)
    
    h_rows = "".join([f'<div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 0.8fr 1fr; padding:8px 0; border-bottom:1px solid #222; font-size:13px;"><div>{h["Fecha"]}</div><div>{h["Entrada"]}</div><div>{h["Salida"]}</div><div style="color:{"#00FF00" if "-" not in h["%"] else "#FF0000"}; font-weight:bold;">{h["%"]}</div><div>{h["Profit"]}</div></div>' for h in reversed(state["history"][-10:])])
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMOS MOVIMIENTOS</div><div class="panel-content"><div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 0.8fr 1fr; color:#FFFF00; font-weight:bold; border-bottom:2px solid #DC143C; padding-bottom:8px;"><div>FECHA</div><div>ENTRADA</div><div>SALIDA</div><div>%</div><div>PROFIT</div></div>{h_rows}</div></div>', unsafe_allow_html=True)

except Exception as e: st.error(f"Error: {e}")

time.sleep(10)
st.rerun()