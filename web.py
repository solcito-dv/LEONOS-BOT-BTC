import streamlit as st
import ccxt
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests

# --- 1. CONFIGURACIÓN TÉCNICA ---
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
        ws = sh.worksheet("ESTADO")
        filas = ws.get_all_records()
        # Ajuste a 30.40 como base
        if not filas: return {"capital_asignado": 30.40, "pnl_acumulado": 0.0, "posiciones": [], "history": []}
        datos = filas[0]
        
        # Limpieza de datos leídos (maneja ceros o "Ninguna" manual)
        def safe_float(v, default=0.0):
            try: return float(str(v).replace(',', '.').strip()) if v not in [None, '', ' ', 'Ninguna'] else default
            except: return default

        state = {
            "capital_asignado": safe_float(datos.get('Capital_Base'), 30.40),
            "pnl_acumulado": safe_float(datos.get('PNL_Acumulado'), 0.0),
            "posiciones": [], "history": []
        }
        
        pos_nombre = str(datos.get('Posicion_Abierta', "Ninguna")).strip()
        if pos_nombre and pos_nombre not in ["Ninguna", "0", "None", ""]:
            state["posiciones"].append({
                "precio": safe_float(datos.get('Precio_Entrada')),
                "monto": safe_float(datos.get('Monto_Invertido')),
                "tipo": pos_nombre,
                "max_alc": safe_float(datos.get('Max_Alcanzado'), safe_float(datos.get('Precio_Entrada')))
            })
        state["history"] = sh.worksheet("HISTORIAL").get_all_records()
        return state
    except:
        return {"capital_asignado": 30.40, "pnl_acumulado": 0.0, "posiciones": [], "history": []}

def save_state(state_data, venta_realizada=None):
    try:
        sh = conectar_gs()
        ws_e = sh.worksheet("ESTADO")
        
        # Preparar los datos asegurando que sean tipos compatibles con JSON
        pos_n = "Ninguna"
        pos_p, pos_m, pos_max = 0.0, 0.0, 0.0
        
        if state_data["posiciones"]:
            p = state_data["posiciones"][0]
            pos_n = str(p["tipo"])
            pos_p = float(p["precio"])
            pos_m = float(p["monto"])
            pos_max = float(p.get("max_alc", p["precio"]))
        
        # Datos para la fila 2 (A2:F2)
        valores = [[
            float(state_data["capital_asignado"]), 
            float(state_data["pnl_acumulado"]), 
            pos_n, 
            pos_p, 
            pos_m, 
            pos_max
        ]]
        
        # Usamos 'raw=False' para que Google interprete los números correctamente
        ws_e.update('A2:F2', valores, value_input_option='USER_ENTERED')
        
        if venta_realizada:
            ws_h = sh.worksheet("HISTORIAL")
            # Convertimos todo a string para el historial para evitar errores de API
            fila_historial = [str(x) for x in venta_realizada]
            ws_h.append_row(fila_historial, value_input_option='USER_ENTERED')
            
    except Exception as e:
        st.error(f"Error de escritura en Excel: {e}")

def send_telegram_msg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except: pass

# --- 3. ESTILOS ---
st.set_page_config(page_title="LEONOS BTC | V35.2", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=JetBrains+Mono:wght@500;800&display=swap');
    .stApp { background-color: #000000; font-family: 'JetBrains Mono', monospace; color: #FFFFFF; }
    .neon-panel { border: 2px solid #DC143C; border-radius: 12px; background: #050505; margin-bottom: 15px; box-shadow: 0 0 15px rgba(220, 20, 60, 0.1); }
    .dash-panel { min-height: 160px; display: flex; flex-direction: column; }
    .panel-header { background: rgba(220, 20, 60, 0.2); padding: 10px; border-bottom: 1px solid #DC143C; color: #FFFF00 !important; font-family: 'Orbitron'; font-size: 13px; font-weight: 900; }
    .panel-content { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: center; }
    .price-main { color: #FFFFFF; font-size: 34px; font-weight: 900; font-family: 'Orbitron'; line-height: 1.1; }
    .info-sub { color: #FFFF00; font-size: 14px; font-weight: bold; margin-top: 5px; }
    /* BURBUJAS */
    .burbuja { padding: 4px 10px; border-radius: 15px; font-weight: 800; font-size: 10px; display: inline-block; }
    .b-entrada { background: #1E90FF; color: white; }
    .b-venta { background: #228B22; color: white; }
    .b-sl { background: #DC143C; color: white; }
    </style>
    """, unsafe_allow_html=True)

state = load_state()
ganancia_7d = sum(float(str(h.get('Profit', h.get('Ganancia_USD', 0))).replace('$', '').replace(',', '')) for h in state["history"][-50:])

with st.sidebar:
    st.markdown('<p style="color:#DC143C; font-family:Orbitron; font-size:18px; font-weight:900;">🦁 LEONOS CONTROL</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown(f"### 📊 Resumen Semanal\n**Profit 7d:** `${ganancia_7d:.4f} USD`")
    st.markdown("---")
    target_ab = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15, step=0.01)
    target_cz = st.slider("Target Cazadora (%)", 0.10, 1.5, 0.50, step=0.05)

st.markdown('<h2 style="font-family:Orbitron; color:#DC143C; margin-bottom:20px;">🦁 LEONOS BTC V35.2</h2>', unsafe_allow_html=True)

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

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel dash-panel"><div class="panel-header">INDICADORES (1M)</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div class="info-sub">EMA 9: {ema9:,.0f} | 200: {ema200:,.0f}</div><div style="color:{radar_col}; font-size:11px;">Radar 15m: {radar_txt}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel dash-panel"><div class="panel-header">ESTRATEGIA RSI</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div class="info-sub">ABEJA < 40 | CAZA < 35</div></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel dash-panel"><div class="panel-header">SALDO LIBRE</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${cap_disponible:.3f}</span><div class="info-sub">TOTAL: ${total_patrimonio:.2f}</div></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel dash-panel"><div class="panel-header">GANANCIA TOTAL</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div class="info-sub">PNL ACUMULADO</div></div></div>', unsafe_allow_html=True)

    log_msg = "SISTEMA EN PAUSA"
    if bot_encendido:
        log_msg = "Analizando..."
        # CAPITAL: Mitad de (30.40 + ganancias)
        monto_op = (total_patrimonio / 2) - 0.05
        
        if len(state["posiciones"]) < 2 and cap_disponible >= monto_op:
            t_compra = None
            if rsi < 40 and price > ema9 and not any(p['tipo'] == "Abeja" for p in state["posiciones"]): t_compra = "Abeja"
            elif rsi < 35 and radar_txt == "ALCISTA" and not any(p['tipo'] == "Cazadora" for p in state["posiciones"]): t_compra = "Cazadora"

            if t_compra:
                mexc.create_market_buy_order(SYMBOL, monto_op / price)
                state["posiciones"].append({"precio": price, "monto": monto_op, "tipo": t_compra, "max_alc": price})
                save_state(state)
                send_telegram_msg(f"🦁 *COMPRA {t_compra.upper()}*\n🔹 Entrada: `${price:,.2f}`")

        nuevas = []
        for pos in state["posiciones"]:
            neta = ((price - pos['precio']) / pos['precio']) * 100
            if price > pos.get('max_alc', pos['precio']): pos['max_alc'] = price
            t_obj = target_ab if pos['tipo'] == "Abeja" else target_cz
            caida_max = ((price - pos['max_alc']) / pos['max_alc']) * 100
            sl_din = -1.20
            if neta > 0.10: sl_din = -0.05

            if neta <= sl_din or (neta >= t_obj and caida_max <= -0.06) or (neta >= (t_obj * 0.8) and caida_max <= -0.04):
                mexc.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
                profit = (pos['monto'] * neta / 100)
                state["pnl_acumulado"] += profit
                save_state(state, [datetime.now().strftime('%H:%M:%S'), "BTC", pos['tipo'], pos['precio'], price, f"{neta:.2f}%", f"{profit:.4f}"])
                send_telegram_msg(f"💰 *VENTA {pos['tipo'].upper()}*\n📈 Resultado: `{neta:.2f}%` / `${profit:.4f}`")
            else:
                nuevas.append(pos); log_msg = f"Operando {pos['tipo']} ({neta:.2f}%)"
        state["posiciones"] = nuevas

    st.markdown(f'<div class="neon-panel"><div class="panel-header">MOTOR</div><div class="panel-content"><div style="color:white; font-style:italic;">"{log_msg}"</div></div></div>', unsafe_allow_html=True)

    # --- HISTORIAL CON BURBUJAS DE ENTRADA, VENTA Y SL ---
    hist_html = '<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; color: #FFFF00; font-weight: bold; border-bottom: 2px solid #DC143C; padding-bottom:5px; font-size: 13px;"><div>HORA</div><div>ENTRADA</div><div>SALIDA</div><div>%</div><div>PROFIT</div></div>'
    if state["history"]:
        for h in reversed(state["history"][-8:]):
            perc = str(h.get("%", "0%"))
            clase_b = "b-venta" if "-" not in perc else "b-sl"
            hist_html += f'''
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; padding: 8px 0; border-bottom: 1px solid #222; font-size: 11px; align-items: center;">
                <div>{h.get("Hora", "-")}</div>
                <div><span class="burbuja b-entrada">IN</span> {h.get("Entrada", "-")}</div>
                <div>{h.get("Salida", "-")}</div>
                <div style="color:{"#00FF00" if "-" not in perc else "#FF0000"}; font-weight:bold;">{perc}</div>
                <div><span class="burbuja {clase_b}">{h.get("Tipo", "Abeja")}</span> ${h.get("Profit", "0")}</div>
            </div>'''
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 MOVIMIENTOS RECIENTES</div><div class="panel-content">{hist_html}</div></div>', unsafe_allow_html=True)

except Exception as e: st.error(f"❌ Error: {e}")
time.sleep(10); st.rerun()