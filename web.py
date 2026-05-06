import streamlit as st
import ccxt
import pandas as pd
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import requests

# --- 1. CONFIGURACIÓN TÉCNICA ---
API_KEY_BTC = 'mx0vglJcyb3BIWHjDk'
SECRET_KEY_BTC = 'de1285d2de1945d2a66e502945c7324b'
SYMBOL = 'BTC/USDT'
BOT_NAME = "LEONOS BTC" 
TELEGRAM_TOKEN = '8763648952:AAEIva2htoqUUog2ieiTJND1cx4BWZr-qss'
TELEGRAM_CHAT_ID = '6458029736'

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
        if not filas: return {"pnl_acumulado": 0.0, "posiciones": [], "last_sell_time": None}
        
        datos_base = filas[0]
        def safe_float(v, default=0.0):
            try: return float(str(v).replace(',', '.').strip()) if v not in [None, '', ' ', 'Ninguna'] else default
            except: return default

        state = {"pnl_acumulado": safe_float(datos_base.get('PNL_Acumulado'), 0.0), "posiciones": [], "last_sell_time": None}
        
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
    except: return {"pnl_acumulado": 0.0, "posiciones": [], "last_sell_time": None}

def save_state(state_data, venta_realizada=None):
    try:
        sh = conectar_gs()
        ws_e = sh.worksheet("ESTADO")
        ws_e.update('A2:G6', [["" for _ in range(7)] for _ in range(5)])
        filas_a_subir = []
        if not state_data["posiciones"]:
            filas_a_subir.append([30.40, float(state_data["pnl_acumulado"]), "Ninguna", 0.0, 0.0, 0.0, -2.0])
        else:
            for p in state_data["posiciones"]:
                filas_a_subir.append([30.40, float(state_data["pnl_acumulado"]), str(p["tipo"]), float(p["precio"]), float(p["monto"]), float(p.get("max_alc", p["precio"])), float(p.get("last_sl_msg", -2.0))])
        ws_e.update('A2:G' + str(1 + len(filas_a_subir)), filas_a_subir, value_input_option='USER_ENTERED')
        if venta_realizada:
            sh.worksheet("HISTORIAL").append_row([str(x) for x in venta_realizada], value_input_option='USER_ENTERED')
        return True
    except: return False

def send_telegram_msg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}&parse_mode=Markdown"
        requests.get(url, timeout=5)
    except: pass

# --- UI & LOGIC ---
st.set_page_config(page_title=f"{BOT_NAME} | V36.9", layout="wide")
st.markdown("<style>.stApp { background-color: #000000; color: white; font-family: 'JetBrains Mono'; }</style>", unsafe_allow_html=True)

if 'last_sell_ts' not in st.session_state: st.session_state.last_sell_ts = datetime.now() - timedelta(minutes=10)

state = load_state()

with st.sidebar:
    st.title("🦁 CONFIG")
    bot_encendido = st.toggle('SISTEMA ACTIVO', value=True)
    target_ab = st.slider("Target Abeja (%)", 0.05, 0.50, 0.15)
    target_cz = st.slider("Target Cazadora (%)", 0.10, 1.5, 0.50)

try:
    mexc = ccxt.mexc({'apiKey': API_KEY_BTC, 'secret': SECRET_KEY_BTC, 'options': {'adjustForTimeDifference': True}})
    balance = mexc.fetch_balance(); usdt_real = balance.get('USDT', {}).get('free', 0.0)
    
    # Datos técnicos
    ohlcv = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
    df['ema9'] = df['c'].ewm(span=9, adjust=False).mean()
    delta = df['c'].diff(); g = delta.where(delta > 0, 0).rolling(14).mean(); l = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = 100 - (100 / (1 + (g / l))).iloc[-1]
    price = df['c'].iloc[-1]
    distancia_ema = abs((price - df['ema9'].iloc[-1]) / df['ema9'].iloc[-1]) * 100

    log_msg = "BUSCANDO ENTRADA..."
    if bot_encendido:
        # COOLDOWN CHECK
        minutos_desde_venta = (datetime.now() - st.session_state.last_sell_ts).total_seconds() / 60
        
        if minutos_desde_venta < 5:
            log_msg = f"⏱️ MODO COOLDOWN ({5 - int(minutos_desde_venta)}m restantes)"
        else:
            # 1. ENTRADA (Con Filtros de seguridad)
            if len(state["posiciones"]) < 2 and usdt_real >= 15.0:
                t_compra = None
                # Abeja: Filtro de distancia a la media para no comprar en el aire
                if rsi < 40 and distancia_ema < 0.08 and price > df['ema9'].iloc[-1]:
                    if not any(p['tipo'] == "Abeja" for p in state["posiciones"]): t_compra = "Abeja"
                
                if t_compra:
                    new_pos = {"precio": price, "monto": 15.10, "tipo": t_compra, "max_alc": price, "last_sl_msg": -1.20}
                    state["posiciones"].append(new_pos)
                    if save_state(state):
                        mexc.create_market_buy_order(SYMBOL, 15.10 / price)
                        send_telegram_msg(f"🦁 *{BOT_NAME} - ENTRADA*\n\n🔥 *{t_compra.upper()}*\n💵 *Precio:* `${price:,.2f}`\n📍 *Dist. Media:* `{distancia_ema:.3f}%`")

        # 2. SALIDA (Cierre de Hierro)
        nuevas_pos = []
        for pos in state["posiciones"]:
            neta = ((price - pos['precio']) / pos['precio']) * 100
            if price > pos['max_alc']: pos['max_alc'] = price
            
            # SL DINÁMICO (Aseguramiento de ganancias)
            sl_profesional = -1.20
            label_int = ""
            if neta >= 0.80: sl_profesional, label_int = 0.60, "ESCUDO +0.60%"
            elif neta >= 0.40: sl_profesional, label_int = 0.20, "ESCUDO +0.20%"
            elif neta >= 0.15: sl_profesional, label_int = 0.02, "BREAK EVEN"

            # TRAILING PROFIT (Si cae 0.03% desde el máximo después de tocar target)
            t_base = target_ab if pos['tipo'] == "Abeja" else target_cz
            caida_desde_max = ((price - pos['max_alc']) / pos['max_alc']) * 100
            
            # EJECUCIÓN DE VENTA
            if neta <= sl_profesional or (neta >= t_base and caida_desde_max <= -0.03):
                mexc.create_market_sell_order(SYMBOL, pos['monto'] / pos['precio'])
                profit = (pos['monto'] * neta / 100)
                state["pnl_acumulado"] += profit
                st.session_state.last_sell_ts = datetime.now()
                save_state(state, [datetime.now().strftime('%H:%M:%S'), "BTC", pos['tipo'], pos['precio'], price, f"{neta:.2f}%", f"{profit:.4f}"])
                send_telegram_msg(f"💰 *{BOT_NAME} - VENTA*\n\n📈 *Resultado:* `{neta:.2f}%`\n💵 *Profit:* `${profit:.4f} USDT`")
            else:
                nuevas_pos.append(pos)
                log_msg = f"OPERANDO: {pos['tipo']} ({neta:.2f}%) {label_int}"

        state["posiciones"] = nuevas_pos
        save_state(state)

    st.write(f"### {log_msg}")

except Exception as e: st.error(f"Error: {e}")
time.sleep(10); st.rerun()