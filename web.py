import streamlit as st
import ccxt
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN TÉCNICA (MODERNA) ---
API_KEY_BTC = 'mx0vglJcyb3BIWHjDk'
SECRET_KEY_BTC = 'de1285d2de1945d2a66e502945c7324b'
SYMBOL = 'BTC/USDT'

TELEGRAM_TOKEN = '8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss'
TELEGRAM_CHAT_ID = '6458029736'

# --- 2. CONEXIÓN GOOGLE SHEETS ---
def conectar_gs():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("BTC_TRADING_DATA")

def load_state():
    try:
        sh = conectar_gs()
        ws = sh.worksheet("Estado")
        datos = ws.get_all_records()[0]
        state = {
            "capital_asignado": float(datos.get('Capital_Base', 30.0)),
            "pnl_acumulado": float(datos.get('PNL_Acumulado', 0.0)),
            "posiciones": [], "history": []
        }
        if datos.get('Posicion_Abierta') != "Ninguna":
            state["posiciones"].append({
                "precio": float(datos['Precio_Entrada']),
                "monto": float(datos['Monto_Invertido']),
                "tipo": datos['Posicion_Abierta'],
                "max_alc": float(datos.get('Max_Alcanzado', datos['Precio_Entrada']))
            })
        ws_h = sh.worksheet("Historial")
        state["history"] = ws_h.get_all_records()
        return state
    except:
        return {"capital_asignado": 30.0, "pnl_acumulado": 0.0, "posiciones": [], "history": []}

def save_state(state_data, venta_realizada=None):
    try:
        sh = conectar_gs()
        ws_e = sh.worksheet("Estado")
        pos_n, pos_p, pos_m, pos_max = "Ninguna", 0, 0, 0
        if state_data["posiciones"]:
            p = state_data["posiciones"][0]
            pos_n, pos_p, pos_m, pos_max = p["tipo"], p["precio"], p["monto"], p["max_alc"]
        
        ws_e.update('A2:F2', [[state_data["capital_asignado"], state_data["pnl_acumulado"], pos_n, pos_p, pos_m, pos_max]])
        if venta_realizada:
            sh.worksheet("Historial").append_row(venta_realizada)
    except: pass

def send_telegram_msg(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}&parse_mode=Markdown"
    requests.get(url, timeout=5)

# --- 3. ESTILOS ---
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
    .burbuja { padding: 12px 20px; border-radius: 30px; font-weight: 800; font-size: 11px; display: inline-block; margin: 5px; border: 1px solid rgba(255,255,255,0.2); }
    .b-entrada { background: #1E90FF; color: white; }
    .b-venta { background: #228B22; color: white; }
    .b-sl { background: #DC143C; color: white; }
    </style>
    """, unsafe_allow_html=True)

state = load_state()

# Resumen Semanal
ganancia_7d = sum(float(str(h.get('Profit', h.get('Ganancia_USD', 0))).replace('$', '')) for h in state["history"][-50:])

with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:20px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown(f"### 📊 Resumen Semanal\n**Profit:** `${ganancia_7d:.4f} USD`")
    if st.button("Enviar Resumen"):
        send_telegram_msg(f"🔥 *RESUMEN SEMANAL*\nProfit: ${ganancia_7d:.4f} USD")
    st.markdown("---")
    target_ab = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15, step=0.01)
    target_cz = st.slider("Target Cazadora (%)", 0.10, 1.5, 0.50, step=0.05)

st.markdown('<h1 style="font-family:Orbitron; color:#DC143C;">🦁 LEONOS BTC V34.3</h1>', unsafe_allow_html=True)

# --- 4. MOTOR ---
try:
    mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
    b1 = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=205)
    df = pd.DataFrame(b1, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    delta = df['close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    
    b15 = mexc.fetch_ohlcv(SYMBOL, timeframe='15m', limit=50)
    df15 = pd.DataFrame(b15, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    ema200_15 = df15['close'].ewm(span=200, adjust=False).mean().iloc[-1]
    
    price, rsi, ema9, ema200 = df.iloc[-1]['close'], df.iloc[-1]['rsi'], df.iloc[-1]['ema9'], df.iloc[-1]['ema200']
    radar_txt = "ALCISTA" if price > ema200_15 else "BAJISTA"
    radar_col = "#00FF00" if radar_txt == "ALCISTA" else "#FF0000"

    total_patrimonio = state["capital_asignado"] + state["pnl_acumulado"]
    cap_disponible = total_patrimonio - sum(p['monto'] for p in state["posiciones"])

    # Dashboard
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO & EMA 9/200</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div style="color:#FFFF00; font-size:12px;">EMA 9: ${ema9:,.0f}</div><div style="font-size:10px; color:{radar_col};">Radar 15m: {radar_txt}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">ESTRATEGIA RSI</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div style="color:#FFFF00; font-size:11px;">ABEJA < 40 | CAZA < 35</div></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">SALDO LIBRE</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${cap_disponible:.3f}</span></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span></div></div>', unsafe_allow_html=True)

    # Burbujas
    if state["posiciones"]:
        st.markdown('<div style="text-align: center; margin-bottom: 20px;">', unsafe_allow_html=True)
        for p in state["posiciones"]:
            t_obj = target_ab if p['tipo'] == "Abeja" else target_cz
            st.markdown(f'<div class="burbuja b-entrada">ENTRADA: ${p["precio"]:,.1f}</div><div class="burbuja b-venta">TARGET: {t_obj}%</div><div class="burbuja b-sl">SL: -1.2%</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Lógica Trading
    log_msg = "Analizando mercado..."
    if bot_encendido:
        if len(state["posiciones"]) < 2:
            t_compra = None
            if rsi < 40 and price > ema9 and not any(p['tipo'] == "Abeja" for p in state["posiciones"]): t_compra = "Abeja"
            elif rsi < 35 and radar_txt == "ALCISTA" and not any(p['tipo'] == "Cazadora" for p in state["posiciones"]): t_compra = "Cazadora"
            if t_compra:
                monto_op = (total_patrimonio / 2) - 0.06
                mexc.create_market_buy_order(SYMBOL, monto_op / price)
                state["posiciones"].append({"precio": price, "monto": monto_op, "tipo": t_compra, "max_alc": price})
                save_state(state); send_telegram_msg(f"🦁 COMPRA {t_compra}: ${price:,.2f}")

        # VENTA PILLA QUIRÚRGICA
        nuevas = []
        for pos in state["posiciones"]:
            neta = ((price - pos['precio']) / pos['precio']) * 100
            if price > pos.get('max_alc', pos['precio']): pos['max_alc'] = price
            
            t_obj = target_ab if pos['tipo'] == "Abeja" else target_cz
            caida_desde_max = ((price - pos['max_alc']) / pos['max_alc']) * 100
            
            # SL Dinámico
            sl_dinamico = -1.20
            if neta > 0.10: sl_dinamico = -0.05 
            
            vender = False
            if neta <= sl_dinamico: vender = True
            elif neta >= (t_obj * 0.8) and neta < t_obj and caida_desde_max <= -0.03: vender = True # Defensa 0.03%
            elif neta >= t_obj and caida_desde_max <= -0.06: vender = True # Maximizar 0.06%
            
            if vender:
                mexc.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
                profit = (pos['monto'] * neta / 100)
                state["pnl_acumulado"] += profit
                save_state(state, [datetime.now().strftime('%H:%M:%S'), "BTC", pos['tipo'], pos['precio'], price, f"{neta:.2f}%", f"{profit:.4f}"])
                send_telegram_msg(f"💰 VENTA {pos['tipo']}: {neta:.2f}%")
            else:
                nuevas.append(pos)
                log_msg = f"Operando {pos['tipo']} ({neta:.2f}%)"
        state["posiciones"] = nuevas

    # Paneles Finales
    st.markdown(f'<div class="neon-panel"><div class="panel-header">ESTADO DEL MOTOR</div><div class="panel-content"><div class="status-msg">"{log_msg}"</div></div></div>', unsafe_allow_html=True)
    hist_html = '<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; color: #FFFF00; font-weight: bold; border-bottom: 2px solid #DC143C; padding-bottom:8px;"><div>HORA</div><div>ENTRADA</div><div>SALIDA</div><div>%</div><div>PROFIT</div></div>'
    for h in reversed(state["history"][-10:]):
        color = "#00FF00" if "-" not in str(h.get("%", h.get("Porcentaje_Neto", ""))) else "#FF0000"
        hist_html += f'<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; padding: 8px 0; border-bottom: 1px solid #222;"><div>{h.get("Fecha")}</div><div>{h.get("Entrada", h.get("Precio_Entrada"))}</div><div>{h.get("Salida", h.get("Precio_Salida"))}</div><div style="color:{color}; font-weight:bold;">{h.get("%", h.get("Porcentaje_Neto"))}</div><div>{h.get("Profit", h.get("Ganancia_USD"))}</div></div>'
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 MOVIMIENTOS</div><div class="panel-content">{hist_html}</div></div>', unsafe_allow_html=True)

except Exception as e: st.error(f"Error: {e}")
time.sleep(10); st.rerun()