import streamlit as st
import ccxt
import pandas as pd
import time
import json
import os
from datetime import datetime
import requests

# --- CONFIGURACIÓN ---
SYMBOL = 'BTC/USDT'
STATE_FILE = 'leonos_btc_state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"in_position": False, "compras": [], "monto_total": 0.0, "history": [], "pnl_acumulado": 0.0}

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

# --- DISEÑO ---
st.set_page_config(page_title="LEONOS BTC", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; font-family: 'Courier New'; color: #FFFFFF; }
    .neon-panel { border: 2px solid #FF8C00; border-radius: 12px; padding: 20px; background: #050505; margin-bottom: 20px; box-shadow: 0 0 15px rgba(255, 140, 0, 0.3); }
    .price-main { color: #FFFFFF; font-size: 42px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- DATOS ---
try:
    mexc = ccxt.mexc({'apiKey': 'mx0vgl09AkPKRbOGO0', 'secret': '39820e86675d494eb5fb0b5c3a184741', 'options': {'adjustForTimeDifference': True}})
    bars = mexc.fetch_ohlcv(SYMBOL, timeframe='1m', limit=100)
    df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    price = df['close'].iloc[-1]
    wallet = mexc.fetch_balance()['free']['USDT']
except Exception as e:
    st.error(f"Error de conexión: {e}")
    price, wallet = 0, 0

# --- PANTALLA ---
st.markdown('<h1 style="color:#FFD700;">🦁 LEONOS BOT BTC</h1>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown(f'<div class="neon-panel"><p>PRECIO BTC</p><span class="price-main">${price:.2f}</span></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="neon-panel"><p>BILLETERA</p><span class="price-main">${wallet:.2f}</span></div>', unsafe_allow_html=True)

st.write("Esperando señales de cacería...")

time.sleep(10)
st.rerun()