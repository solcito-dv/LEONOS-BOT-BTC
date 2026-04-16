import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime
import requests

# --- CONFIGURACIÓN DE TELEGRAM ---
def enviar_telegram_pro(titulo, e1, e2, prom, target, stop, estado):
    token = "8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss"
    chat_id = "6458029736"
    msg = (f"{titulo}\n"
           f"━━━━━━━━━━━━━━━\n"
           f"📍 Entrada 1: {e1}\n"
           f"📍 Entrada 2: {e2}\n"
           f"⚖️ Promedio: {prom}\n"
           f"🎯 Objetivo: {target}\n"
           f"🛑 Stop Loss: {stop}\n"
           f"📝 Estado: {estado}")
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}"
    try: requests.get(url)
    except: pass

def enviar_telegram_simple(mensaje):
    token = "8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss"
    chat_id = "6458029736"
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={mensaje}"
    try: requests.get(url)
    except: pass

# --- 1. CONFIGURACIÓN ---
API_KEY = 'mx0vgl09AkPKRbOGO0'
SECRET_KEY = '39820e86675d494eb5fb0b5c3a184741'
SYMBOL = 'SOL/USDT'
STATE_FILE = 'leonos_state.json'

def load_state():
    pnl_base = 0.1241
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: 
                state = json.load(f)
                if "pnl_acumulado" not in state: state["pnl_acumulado"] = pnl_base
                if not state.get("history"):
                    state["history"] = [{
                        "Fecha": "Ant.", "Entrada": "$84.63", "Salida": "$85.35", "Neto": "0.80%", "Profit": "$0.0416"
                    }]
                return state
        except: pass
    return {
        "in_position": False, 
        "compras": [], 
        "monto_total": 0.0, 
        "history": [{"Fecha": "Ant.", "Entrada": "$84.63", "Salida": "$85.35", "Neto": "0.80%", "Profit": "$0.0416"}], 
        "last_report_date": "", 
        "pnl_acumulado": pnl_base
    }

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

# --- 2. DISEÑO NEÓN (RESTAURADO) ---
st.set_page_config(page_title="LEONOS BOT SOL", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    .neon-panel { border: 2px solid #8A2BE2; border-radius: 12px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(138, 43, 226, 0.3); }
    .panel-header { background: rgba(138, 43, 226, 0.2); padding: 12px; border-bottom: 1px solid #8A2BE2; color: #FFD700; font-family: 'Orbitron'; font-size: 14px; text-transform: uppercase; }
    .panel-content { padding: 20px; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1.1; }
    .status-msg { color: #FFD700; font-style: italic; font-size: 15px; border-left: 4px solid #8A2BE2; padding-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MOTOR DE DATOS ---
def fetch_all():
    try:
        mexc = ccxt.mexc({'apiKey': API_KEY, 'secret': SECRET_KEY, 'options': {'defaultType': 'spot', 'adjustForTimeDifference': True}})
        bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        delta = df['close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        df['std'] = df['close'].rolling(20).std(); df['sma20'] = df['close'].rolling(20).mean()
        df['lower_b'] = df['sma20'] - (df['std'] * 2)
        balance = mexc.fetch_balance()
        return df.iloc[-1], balance['free']['USDT'], mexc
    except: return None, 0, None

state = load_state()
data, wallet, exchange = fetch_all()

# CABECERA
col_t, col_b = st.columns([4, 1])
with col_t:
    st.markdown('<h1 style="font-family:Orbitron; color:#FFD700; margin:0;">🦁 LEONOS BOT SOL</h1>', unsafe_allow_html=True)
with col_b:
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)

if data is not None:
    price, rsi, ema200, lower_b = data['close'], data['rsi'], data['ema200'], data['lower_b']
    limite_rsi = 35 if price > ema200 else 28
    
    pnl_historial = sum([float(op['Profit'].replace('$', '')) for op in state['history'] if op['Profit'] != 'N/A']) if state['history'] else 0.0
    total_pnl = state.get("pnl_acumulado", 0.0) + pnl_historial

    # DASHBOARD (RESTAURADO)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA200</div><div class="panel-content"><span class="price-main">${price:.2f}</span><br><small>TENDENCIA: ${ema200:.2f}</small></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI ACTUAL</div><div class="panel-content"><span class="price-main" style="color:#28a745;">{rsi:.2f}</span><br><small>OBJETIVO: < {limite_rsi}</small></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">BILLETERA USDT</div><div class="panel-content"><span class="price-main" style="color:#FFD700;">${wallet:.2f}</span><br><small>DISPONIBLE</small></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${total_pnl:.4f}</span><br><small>HISTÓRICO TOTAL</small></div></div>', unsafe_allow_html=True)

    log_msg = "Analizando mercado..."
    if not bot_encendido:
        log_msg = "SISTEMA EN PAUSA"
    else:
        if not state["in_position"]:
            monto_op = (wallet / 2) - 0.01
            if rsi < limite_rsi and price <= (lower_b * 1.001) and monto_op >= 5.0:
                try:
                    exchange.create_limit_buy_order(SYMBOL, monto_op / price, price)
                    tp, sl = price * 1.0102, price * 0.97
                    state.update({"in_position": True, "compras": [price], "monto_total": monto_op})
                    save_state(state)
                    enviar_telegram_pro("🦁 COMPRA EJECUTADA", f"${price:.2f}", "Esperando...", f"${price:.2f}", f"${tp:.2f}", f"${sl:.2f}", "Buscando Target")
                except Exception as e: log_msg = f"❌ ERROR COMPRA: {e}"
        else:
            cant = len(state["compras"])
            promedio = sum(state["compras"]) / cant
            neta = (((price - promedio) / promedio) * 100) - 0.22
            tp, sl = promedio * 1.0102, promedio * 0.97
            
            st.markdown(f"""
                <div style="display: flex; gap: 10px; margin-bottom: 5px; justify-content: center; flex-wrap: wrap;">
                    <span style="background: #FFD70022; color: #FFD700; padding: 5px 15px; border-radius: 20px; border: 1px solid #FFD700; font-size: 12px;"><b>COMPRA:</b> ${promedio:.2f}</span>
                    <span style="background: #00FF0022; color: #00FF00; padding: 5px 15px; border-radius: 20px; border: 1px solid #00FF00; font-size: 12px;"><b>VENTA EN:</b> ${tp:.2f}</span>
                </div>
            """, unsafe_allow_html=True)

            if cant == 1 and neta <= -1.5 and rsi < (limite_rsi - 3) and wallet >= 5.0:
                try:
                    monto_ref = wallet - 0.01
                    exchange.create_limit_buy_order(SYMBOL, monto_ref / price, price)
                    state["compras"].append(price)
                    state["monto_total"] += monto_ref
                    save_state(state)
                except: pass

            if neta >= 0.8 or neta <= -3.0:
                try:
                    exchange.create_limit_sell_order(SYMBOL, state['monto_total'] / promedio, price)
                    prof = (state['monto_total'] * neta / 100)
                    fecha_ahora = datetime.now().strftime("%d/%m %H:%M")
                    state["history"].append({
                        "Fecha": fecha_ahora, "Entrada": f"${promedio:.2f}",
                        "Salida": f"${price:.2f}", "Neto": f"{neta:.2f}%", "Profit": f"${prof:.4f}"
                    })
                    state.update({"in_position": False, "compras": [], "monto_total": 0.0})
                    save_state(state)
                except Exception as e: log_msg = f"❌ ERROR VENTA: {e}"
            else:
                log_msg = f"DENTRO: {neta:.2f}% neto ({cant} entradas)."

    st.markdown(f'<div class="neon-panel"><div class="panel-header">SITUACIÓN ACTUAL</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # HISTORIAL (UN SOLO RECUADRO CON FECHA)
    contenido = '<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; color: #FFD700; font-weight: bold; border-bottom: 1px solid #8A2BE2; padding-bottom:5px;"><div>FECHA</div><div>COMPRA</div><div>VENTA</div><div>NETO</div><div>GANANCIA</div></div>'
    for op in state["history"][-10:]:
        contenido += f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; padding: 8px 0; border-bottom: 1px solid #333; color: white;"><div>{op["Fecha"]}</div><div>{op["Entrada"]}</div><div>{op["Salida"]}</div><div>{op["Neto"]}</div><div>{op["Profit"]}</div></div>'
    
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMAS OPERACIONES</div><div class="panel-content">{contenido}</div></div>', unsafe_allow_html=True)

time.sleep(10)
st.rerun()