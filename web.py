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
BOT_NAME = "LEONOS BTC" 
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
        # CAPITAL ACTUALIZADO
        if not filas: return {"capital_asignado": 30.40, "pnl_acumulado": 0.0, "posiciones": [], "history": []}
        datos = filas[0]
        
        def safe_float(v, default=0.0):
            try: return float(str(v).replace(',', '.').strip()) if v not in [None, '', ' ', 'Ninguna'] else default
            except: return default

        state = {
            "capital_asignado": 30.40, 
            "pnl_acumulado": safe_float(datos.get('PNL_Acumulado'), 0.0),
            "posiciones": [], "history": []
        }
        
        # Cargar todas las posiciones activas de la hoja (soporta hasta 3 filas de posiciones si las hubiera)
        for fila in filas:
            pos_nombre = str(fila.get('Posicion_Abierta', "Ninguna")).strip()
            if pos_nombre and pos_nombre not in ["Ninguna", "0", "None", ""]:
                state["posiciones"].append({
                    "precio": safe_float(fila.get('Precio_Entrada')),
                    "monto": safe_float(fila.get('Monto_Invertido')),
                    "tipo": pos_nombre,
                    "max_alc": safe_float(fila.get('Max_Alcanzado'), safe_float(fila.get('Precio_Entrada'))),
                    "last_sl_msg": safe_float(fila.get('Last_SL', -2.0))
                })
        
        state["history"] = sh.worksheet("HISTORIAL").get_all_records()
        return state
    except:
        return {"capital_asignado": 30.40, "pnl_acumulado": 0.0, "posiciones": [], "history": []}

def save_state(state_data, venta_realizada=None):
    try:
        sh = conectar_gs()
        ws_e = sh.worksheet("ESTADO")
        
        # Limpiar filas anteriores para evitar datos fantasma
        ws_e.update('A2:G5', [["" for _ in range(7)] for _ in range(4)])
        
        filas_update = []
        if not state_data["posiciones"]:
            filas_update.append([float(state_data["capital_asignado"]), float(state_data["pnl_acumulado"]), "Ninguna", 0.0, 0.0, 0.0, -2.0])
        else:
            for p in state_data["posiciones"]:
                filas_update.append([float(state_data["capital_asignado"]), float(state_data["pnl_acumulado"]), str(p["tipo"]), float(p["precio"]), float(p["monto"]), float(p.get("max_alc", p["precio"])), float(p.get("last_sl_msg", -2.0))])
        
        ws_e.update('A2:G' + str(1 + len(filas_update)), filas_update, value_input_option='USER_ENTERED')
        
        if venta_realizada:
            ws_h = sh.worksheet("HISTORIAL")
            ws_h.append_row([str(x) for x in venta_realizada], value_input_option='USER_ENTERED')
        return True
    except:
        return False

def send_telegram_msg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except: pass

# --- 3. ESTILOS ---
st.set_page_config(page_title=f"{BOT_NAME} | V36.6", layout="wide")
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
    .burbuja { padding: 4px 10px; border-radius: 15px; font-weight: 800; font-size: 10px; display: inline-block; margin-right: 5px; }
    .b-entrada { background: #1E90FF; color: white; }
    .b-venta { background: #228B22; color: white; }
    .b-sl { background: #DC143C; color: white; }
    </style>
    """, unsafe_allow_html=True)

state = load_state()

with st.sidebar:
    st.markdown(f'<p style="color:#DC143C; font-family:Orbitron; font-size:18px; font-weight:900;">🦁 {BOT_NAME}</p>', unsafe_allow_html=True)
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    st.markdown("---")
    target_ab = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15, step=0.01)
    target_cz = st.slider("Target Cazadora (%)", 0.10, 1.5, 0.50, step=0.05)

st.markdown(f'<h2 style="font-family:Orbitron; color:#DC143C; margin-bottom:20px;">🦁 {BOT_NAME} V36.6</h2>', unsafe_allow_html=True)

# --- 4. MOTOR ---
try:
    mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
    
    # Obtener saldo real de MEXC para evitar errores de capital
    balance = mexc.fetch_balance()
    usdt_real = balance.get('USDT', {}).get('free', 0.0)
    
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

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="neon-panel dash-panel"><div class="panel-header">INDICADORES (1M)</div><div class="panel-content"><span class="price-main">${price:,.0f}</span><div class="info-sub">EMA 9: {ema9:,.0f} | 200: {ema200:,.0f}</div><div style="color:{radar_col}; font-size:11px; font-weight:bold;">RADAR 15M: {radar_txt}</div></div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="neon-panel dash-panel"><div class="panel-header">ESTRATEGIA RSI</div><div class="panel-content"><span class="price-main">{rsi:.2f}</span><div class="info-sub">ABEJA < 40 | CAZA < 35</div></div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="neon-panel dash-panel"><div class="panel-header">SALDO MEXC</div><div class="panel-content"><span class="price-main" style="color:#FFFF00;">${usdt_real:.2f}</span><div class="info-sub">DISPONIBLE REAL</div></div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="neon-panel dash-panel"><div class="panel-header">PNL ACUMULADO</div><div class="panel-content"><span class="price-main" style="color:#00FF00;">${state["pnl_acumulado"]:.4f}</span><div class="info-sub">USD GANADOS</div></div></div>', unsafe_allow_html=True)

    log_msg = "SISTEMA EN PAUSA"
    if bot_encendido:
        log_msg = "Buscando entrada..."
        monto_op = (30.40 / 2) - 0.05
        
        # Solo entra si el capital REAL en MEXC es suficiente
        if len(state["posiciones"]) < 2 and usdt_real >= monto_op:
            t_compra = None
            if rsi < 40 and price > ema9 and not any(p['tipo'] == "Abeja" for p in state["posiciones"]):
                t_compra = "Abeja"
            elif rsi < 35 and radar_txt == "ALCISTA" and not any(p['tipo'] == "Cazadora" for p in state["posiciones"]):
                t_compra = "Cazadora"

            if t_compra:
                new_pos = {"precio": price, "monto": monto_op, "tipo": t_compra, "max_alc": price, "last_sl_msg": -1.20}
                state["posiciones"].append(new_pos)
                if save_state(state):
                    mexc.create_market_buy_order(SYMBOL, monto_op / price)
                    send_telegram_msg(f"🦁 *{BOT_NAME} - ENTRADA*\n\n🔥 *Estrategia:* {t_compra.upper()}\n💵 *Precio:* `${price:,.2f}`")

        nuevas_pos = []
        status_ops = []
        for pos in state["posiciones"]:
            neta = ((price - pos['precio']) / pos['precio']) * 100
            if price > pos.get('max_alc', pos['precio']): pos['max_alc'] = price
            
            # --- PROTECCIÓN DE SUBIDAS (ESCALONES) ---
            sl_din = -1.20
            label_escudo = ""
            if neta >= 0.80: sl_din, label_escudo = 0.60, "🛡️ Escudo +0.60%"
            elif neta >= 0.50: sl_din, label_escudo = 0.35, "🛡️ Escudo +0.35%"
            elif neta >= 0.30: sl_din, label_escudo = 0.15, "🛡️ Escudo +0.15%"
            elif neta >= 0.12: sl_din, label_escudo = 0.00, "🛡️ Break Even (0.00%)"

            if label_escudo and sl_din > pos.get('last_sl_msg', -1.20):
                pos['last_sl_msg'] = sl_din
                send_telegram_msg(f"🦁 *{BOT_NAME} - PROTECCIÓN*\n\n📈 *{pos['tipo']}:* {label_escudo}\n💰 *Neta Actual:* `{neta:.2f}%`")

            # --- MEJORA: VENTA AGRESIVA EN PICO ---
            t_base = target_ab if pos['tipo'] == "Abeja" else target_cz
            # Si el RSI es muy alto (>75), vendemos al tocar el target sin esperar nada
            if neta >= t_base and rsi > 75:
                vender_ya = True
            else:
                # Si no, usamos el aire tradicional
                caida_tol = -0.10 if radar_txt == "ALCISTA" else -0.03
                caida_max = ((price - pos['max_alc']) / pos['max_alc']) * 100
                vender_ya = (neta >= t_base and caida_max <= caida_tol) or (neta <= sl_din)

            if vender_ya:
                mexc.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
                profit = (pos['monto'] * neta / 100)
                state["pnl_acumulado"] += profit
                tipo_etiq = pos['tipo'] if neta > 0 else f"SL-{pos['tipo']}"
                if save_state(state, [datetime.now().strftime('%H:%M:%S'), "BTC", tipo_etiq, pos['precio'], price, f"{neta:.2f}%", f"{profit:.4f}"]):
                    send_telegram_msg(f"💰 *{BOT_NAME} - VENTA*\n\n📊 *Resultado:* `{neta:.2f}%` ({pos['tipo']})\n💵 *Profit:* `${profit:.4f} USDT`")
            else:
                nuevas_pos.append(pos)
                color_n = "#00FF00" if neta > 0 else "#FF0000"
                status_ops.append(f'<span style="color:{color_n};">{pos["tipo"]}: {neta:.2f}%</span>')
        
        state["posiciones"] = nuevas_pos
        if status_ops: log_msg = " | ".join(status_ops)
        save_state(state)

    st.markdown(f'<div class="neon-panel"><div class="panel-header">MOTOR</div><div class="panel-content"><div>{log_msg}</div></div></div>', unsafe_allow_html=True)

    # --- HISTORIAL ---
    hist_html = '<div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 1fr 1fr; color: #FFFF00; font-weight: bold; border-bottom: 2px solid #DC143C; padding-bottom:5px; font-size: 12px;"><div>HORA</div><div>DETALLE</div><div>ENTRADA</div><div>SALIDA</div><div>PROFIT</div></div>'
    if state["history"]:
        vistas = set()
        for h in reversed(state["history"]):
            id_fila = f"{h.get('Hora')}-{h.get('Profit')}"
            if id_fila in vistas or not h.get("Hora"): continue
            vistas.add(id_fila)
            p_usd = str(h.get("Profit", "0"))
            tipo_h = str(h.get("Tipo", "Abeja"))
            es_sl = "SL" in tipo_h or "-" in str(h.get("%", ""))
            clase_b = "b-sl" if es_sl else "b-venta"
            color_p = "#FF0000" if es_sl else "#00FF00"
            hist_html += f'''
            <div style="display: grid; grid-template-columns: 1.2fr 1fr 1fr 1fr 1fr; padding: 8px 0; border-bottom: 1px solid #222; font-size: 11px; align-items: center;">
                <div>{h.get("Hora", "-")}</div>
                <div><span class="burbuja b-entrada">IN</span><span class="burbuja {clase_b}">{tipo_h}</span></div>
                <div>${h.get("Entrada", "-")}</div>
                <div>${h.get("Salida", "-")}</div>
                <div style="color:{color_p}; font-weight:bold;">${p_usd}</div>
            </div>'''
            if len(vistas) >= 8: break
    st.markdown(f'<div class="neon-panel"><div class="panel-header">📜 HISTORIAL DE OPERACIONES</div><div class="panel-content">{hist_html}</div></div>', unsafe_allow_html=True)

except Exception as e: st.error(f"❌ Error: {e}")
time.sleep(10); st.rerun()