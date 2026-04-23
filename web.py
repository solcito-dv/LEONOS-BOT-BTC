import streamlit as st
import ccxt
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import requests
import pytz

# --- 1. CONFIGURACIÓN ---
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

def get_arg_time():
    return datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))

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

def send_telegram_buy(tipo, precio, monto):
    msg = f"🦁 *NUEVA COMPRA*\n\n📈 *Par:* {SYMBOL}\n🐝 *Estrategia:* {tipo}\n📥 *Entrada:* ${precio:,.2f}\n💰 *Inversión:* ${monto:.2f}"
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}&parse_mode=Markdown")

def send_telegram_sell(tipo, p_ent, p_sal, neta, profit):
    emoji = "💰" if float(profit) > 0 else "🛑"
    msg = f"{emoji} *VENTA REALIZADA*\n\n📈 *Par:* {SYMBOL}\n🐝 *Tipo:* {tipo}\n📥 *Entrada:* ${p_ent:,.2f}\n📤 *Salida:* ${p_sal:,.2f}\n📊 *Resultado:* {neta} ({profit} USD)"
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}&parse_mode=Markdown")

# --- 3. INTERFAZ ---
st.set_page_config(page_title="LEONOS BTC PRO", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    .neon-panel { border: 2px solid #DC143C; border-radius: 12px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(220, 20, 60, 0.2); }
    .panel-header { background: rgba(220, 20, 60, 0.2); padding: 12px; border-bottom: 1px solid #DC143C; color: #FFFF00 !important; font-family: 'Orbitron'; font-size: 14px; font-weight: 900; }
    .panel-content { padding: 15px; }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: 900; font-family: 'Orbitron'; line-height: 1; }
    .card-pos { background: #111; border-left: 4px solid #1E90FF; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .stat-label { color: #888; font-size: 10px; text-transform: uppercase; }
    .stat-val { color: #00FF00; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

state = load_state()

with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:20px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    target_ab = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15, step=0.01)
    target_cz = st.slider("Target Cazadora (%)", 0.10, 1.5, 0.50, step=0.05)

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
    tendencia_alcista = price > ema200_15

    # Lógica Compra/Venta igual a la anterior (mantenida)
    if bot_encendido and len(state["posiciones"]) < 2:
        tipo_c = None
        if rsi < 40 and price > ema9 and not any(p['tipo']=="Abeja" for p in state["posiciones"]): tipo_c = "Abeja"
        elif rsi < 35 and tendencia_alcista and not any(p['tipo']=="Cazadora" for p in state["posiciones"]): tipo_c = "Cazadora"
        if tipo_c:
            monto_op = ((state["capital_asignado"] + state["pnl_acumulado"]) / 2) - 0.06
            mexc.create_market_buy_order(SYMBOL, monto_op / price)
            state["posiciones"].append({"precio": price, "monto": monto_op, "tipo": tipo_c, "max_alc": price})
            save_state(state); send_telegram_buy(tipo_c, price, monto_op)

    nuevas = []
    for pos in state["posiciones"]:
        neta = ((price - pos['precio']) / pos['precio']) * 100
        if price > pos['max_alc']: pos['max_alc'] = price
        t_obj = target_ab if pos['tipo'] == "Abeja" else target_cz
        dist_max = ((price - pos['max_alc']) / pos['max_alc']) * 100
        
        vender = False
        if neta <= -1.20: vender = True
        elif neta >= t_obj and dist_max <= -0.06: vender = True
        elif neta >= (t_obj * 0.8) and dist_max <= -0.03: vender = True
        
        if vender:
            mexc.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
            profit = (pos['monto'] * neta / 100)
            state["pnl_acumulado"] += profit
            save_state(state, [get_arg_time().strftime('%d/%m %H:%M'), "BTC", pos['tipo'], pos['precio'], price, f"{neta:.2f}%", f"{profit:.4f}"])
            send_telegram_sell(pos['tipo'], pos['precio'], price, f"{neta:.2f}%", f"{profit:.4f}")
        else: nuevas.append(pos)
    state["posiciones"] = nuevas

    # --- 5. DIBUJO RESTAURADO ---
    st.markdown(f'<h1 style="font-family:Orbitron; color:#DC143C; margin-bottom:0;">🦁 LEONOS BTC <span style="font-size:12px; color:white;">{get_arg_time().strftime("%H:%M:%S")} AR</span></h1>', unsafe_allow_html=True)
    
    # Fila 1: Indicadores
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel"><div class="panel-header">PRECIO</div><div class="panel-content"><span class="price-main">${price:,.0f}</span></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel"><div class="panel-header">RSI (1M)</div><div class="panel-content"><span class="price-main" style="color:{"#FF4500" if rsi < 35 else "#FFFFFF"}">{rsi:.1f}</span></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel"><div class="panel-header">EMA 200 (15M)</div><div class="panel-content"><span class="price-main" style="color:{"#00FF00" if tendencia_alcista else "#DC143C"}">${ema200_15:,.0f}</span></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel"><div class="panel-header">PNL TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span></div></div>', unsafe_allow_html=True)

    # Fila 2: Estado de Operaciones y Parámetros
    col_izq, col_der = st.columns([2, 1])
    with col_izq:
        st.markdown('<p style="font-family:Orbitron; color:#FFFF00; font-size:14px;">⚡ POSICIONES ACTIVAS</p>', unsafe_allow_html=True)
        if not state["posiciones"]: st.info("Buscando señales...")
        for p in state["posiciones"]:
            neta_p = ((price - p['precio']) / p['precio']) * 100
            st.markdown(f"""<div class="card-pos">
                <div style="display:flex; justify-content:space-between;">
                    <b>{p['tipo']} BTC</b> <span style="color:{"#00FF00" if neta_p > 0 else "#DC143C"}">{neta_p:.3f}%</span>
                </div>
                <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; margin-top:10px;">
                    <div><span class="stat-label">Entrada</span><br>${p['precio']:,.1f}</div>
                    <div><span class="stat-label">Inversión</span><br>${p['monto']:.2f}</div>
                    <div><span class="stat-label">Max. Alc</span><br>${p['max_alc']:,.1f}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    with col_der:
        st.markdown('<p style="font-family:Orbitron; color:#FFFF00; font-size:14px;">🎯 OBJETIVOS DINÁMICOS</p>', unsafe_allow_html=True)
        st.write(f"**Abeja:** Obj: {target_ab}% | Defensa: {target_ab*0.8:.2f}%")
        st.write(f"**Cazadora:** Obj: {target_cz}% | Defensa: {target_cz*0.8:.2f}%")
        st.write(f"**Trend 15m:** {'ALCISTA 📈' if tendencia_alcista else 'BAJISTA 📉'}")

    # Historial
    h_rows = "".join([f'<div style="display: grid; grid-template-columns: 1fr 0.5fr 1fr 1fr 0.5fr 0.8fr; padding:8px 0; border-bottom:1px solid #222; font-size:12px;"><div>{h.get("Fecha")}</div><div>{h.get("Tipo")}</div><div>${float(h.get("Precio_Entrada",0)):,.1f}</div><div>${float(h.get("Precio_Salida",0)):,.1f}</div><div style="color:#00FF00;">{h.get("Porcentaje_Neto")}</div><div>${h.get("Ganancia_USD")}</div></div>' for h in reversed(state["history"][-8:])])
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 ÚLTIMOS 8 MOVIMIENTOS</div><div class="panel-content">{h_rows}</div></div>', unsafe_allow_html=True)

except Exception as e: st.error(f"Error de Motor: {e}")
time.sleep(10); st.rerun()