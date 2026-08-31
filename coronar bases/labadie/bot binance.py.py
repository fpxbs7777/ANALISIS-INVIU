import uuid, websocket, json, numpy as np, requests, threading, time, argparse, hashlib, os
import hmac as hmac_lib
from collections import deque, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlencode
import math

# ==========================================
# PARÁMETROS GLOBALES Y TEORÍA HFT
# ==========================================
WINDOW_SIZE = 1500
WARMUP_TICKS = 1500
Z_SCORE_THRESHOLD = 1.8
DEPTH_LEVELS = 10
VWAP_WINDOW = 1000
VP_BINS = 50
VP_LOOKBACK = 500
COOLDOWN_SECONDS = 20
MIN_CTX_SECONDS = 10
SYMBOL = "BTCUSDT"
OBI_THRESHOLD = 0.10

# Ratios de Rentabilidad Asimétrica (Objetivo RR > 3 Neto)
ATR_MULTIPLIER_SL = 2.0
ATR_MULTIPLIER_TP = 7.0 
USE_MAKER_ORDERS = True     # Fuerza órdenes LIMIT Post-Only para salvar fees

# Parámetros del Filtro Probabilístico Empírico
PROBABILIDAD_MINIMA = 0.55  # Mínimo 55% de probabilidad para ejecutar
MONTE_CARLO_SIMULATIONS = 5000  # Número de simulaciones bootstrapping
BOOTSTRAP_SAMPLE_SIZE = 20  # Tamaño de muestra por simulación
ORDER_BOOK_SNAPSHOT_SIZE = 500  # Tamaño del historial de order book para bootstrapping

# Parámetros del Análisis Espectral (PCA del Order Book)
PCA_REFRESH_SECONDS = 60  # Recalcular PCA cada 60 segundos
PCA_NIVELES = 10  # Número de niveles del order book para PCA
PCA_HISTORIA_SIZE = 500  # Tamaño del historial para PCA

# ==========================================
# FUNCIONES MATEMÁTICAS AUXILIARES
# ==========================================
def normal_cdf(x):
    """
    Approximation of the standard normal CDF using the error function.
    Replaces scipy.stats.norm.cdf to avoid scipy dependency.
    """
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

# Gestión de Riesgo (Modo Hedge + Margen Cruzado)
RISK_PER_TRADE_PCT = 0.01  
CAPITAL_USDT_FALLBACK = 1000.0
LEVERAGE = 10               

# Comisiones (Se sobreescriben automáticamente al iniciar)
FEE_RATE = 0.0002           # Estimación MAKER (0.02%)
FEE_TOTAL_ROUND_TRIP = FEE_RATE * 2 * 100  

# API Keys (Demo Futures)
API_KEY = "S8MaQnsJqDXRq50YRrmcL3UDoAnbftVeATOvA7GS69IrK73ACvbu36Q3lLRQVwZd"
API_SECRET = "Xto9ilktNc9znjjaMQfptyWdybSaw0JAVtAifDMvQAebQBq6QYqhbQZfr74oYeBH"

BASE_URL = "https://demo-fapi.binance.com"
KLINES_URL = f"{BASE_URL}/fapi/v1/klines"
WS_URL = "wss://demo-stream.binance.com/stream"

# Variables de Estado Global
estado_mercado = {
    "trend_5m": "UNKNOWN", "vp_poc": None, "vp_val": None, "vp_vah": None,
    "obs": {"alcistas": [], "bajistas": []}, "ts": 0, "balance_usdt": CAPITAL_USDT_FALLBACK
}
estado_lock = threading.Lock()
step_size_cache = {}
tick_size_cache = {}

obi_history = deque(maxlen=WINDOW_SIZE)
vwap_prices = deque(maxlen=VWAP_WINDOW)
vwap_volumes = deque(maxlen=VWAP_WINDOW)
candle_closes = deque(maxlen=50)
candle_highs = deque(maxlen=50)
candle_lows = deque(maxlen=50)

# Historial completo para distribución empírica (Order Book + Volume Profile)
order_book_history = deque(maxlen=WINDOW_SIZE)  # Snapshots completos del order book
volume_profile_history = deque(maxlen=100)  # Historial de POC, VAH, VAL

last_signal_side = None
last_signal_time = 0
_señales_activas = {}
_trade_log = []  # Log estructurado para calibración: {z_score, prob, resultado, timestamp}

# Cache PCA para análisis espectral del order book
autovalores_cache = None
autovectores_cache = None
ultimo_pca_ts = 0
pca_regimen = "DESCONOCIDO"
pca_ratio = 0.0

# ==========================================
# AUTO-CONFIGURACIÓN Y ENTORNO DE CUENTA
# ==========================================
def get_server_time():
    try:
        r = requests.get(f"{BASE_URL}/fapi/v1/time", timeout=5)
        return r.json()["serverTime"]
    except: return int(time.time() * 1000)

def configurar_entorno_cuenta(symbol, leverage):
    """Fuerza Hedge Mode, ajusta leverage y cambia a MARGEN CRUZADO (CROSSED)."""
    ts = get_server_time()
    
    # 1. Hedge Mode
    query_hedge = urlencode({"dualSidePosition": "true", "timestamp": str(ts)})
    sig_hedge = hmac_lib.new(API_SECRET.encode("utf-8"), query_hedge.encode("utf-8"), hashlib.sha256).hexdigest()
    res_hedge = requests.post(f"{BASE_URL}/fapi/v1/positionSide/dual?{query_hedge}&signature={sig_hedge}", headers={"X-MBX-APIKEY": API_KEY}).json()
    if "code" in res_hedge and res_hedge["code"] == -4059:
        print("  [AUTO-CONFIG] Hedge Mode ya estaba activado.")
    
    # 2. Leverage
    ts = get_server_time()
    query_lev = urlencode({"symbol": symbol.upper(), "leverage": leverage, "timestamp": str(ts)})
    sig_lev = hmac_lib.new(API_SECRET.encode("utf-8"), query_lev.encode("utf-8"), hashlib.sha256).hexdigest()
    requests.post(f"{BASE_URL}/fapi/v1/leverage?{query_lev}&signature={sig_lev}", headers={"X-MBX-APIKEY": API_KEY})
    
    # 3. Margen Cruzado (Evita liquidaciones prematuras antes de tocar SL)
    ts = get_server_time()
    query_mar = urlencode({"symbol": symbol.upper(), "marginType": "CROSSED", "timestamp": str(ts)})
    sig_mar = hmac_lib.new(API_SECRET.encode("utf-8"), query_mar.encode("utf-8"), hashlib.sha256).hexdigest()
    res_mar = requests.post(f"{BASE_URL}/fapi/v1/marginType?{query_mar}&signature={sig_mar}", headers={"X-MBX-APIKEY": API_KEY}).json()
    if "code" in res_mar and res_mar["code"] == -4046:
        print("  [AUTO-CONFIG] Margen Cruzado (CROSSED) ya estaba activado.")

def get_commission_rate(symbol):
    global FEE_RATE, FEE_TOTAL_ROUND_TRIP
    try:
        ts = get_server_time()
        query = urlencode({"symbol": symbol.upper(), "timestamp": str(ts)})
        sig = hmac_lib.new(API_SECRET.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        url = f"{BASE_URL}/fapi/v1/commissionRate?{query}&signature={sig}"
        r = requests.get(url, headers={"X-MBX-APIKEY": API_KEY}, timeout=5).json()
        if "makerCommissionRate" in r:
            FEE_RATE = float(r["makerCommissionRate"]) if USE_MAKER_ORDERS else float(r["takerCommissionRate"])
            FEE_TOTAL_ROUND_TRIP = FEE_RATE * 2 * 100
            tipo = "MAKER" if USE_MAKER_ORDERS else "TAKER"
            print(f"  [AUTO-CONFIG] Comisión {tipo} detectada: {FEE_RATE*100:.4f}%")
    except Exception: pass

def cargar_filtros_simbolo(symbol):
    try:
        r = requests.get(f"{BASE_URL}/fapi/v1/exchangeInfo", timeout=5).json()
        for s in r.get("symbols", []):
            if s["symbol"] == symbol.upper():
                for f in s.get("filters", []):
                    if f["filterType"] == "LOT_SIZE": step_size_cache[symbol] = float(f["stepSize"])
                    if f["filterType"] == "PRICE_FILTER": tick_size_cache[symbol] = float(f["tickSize"])
    except:
        step_size_cache[symbol] = 0.001
        tick_size_cache[symbol] = 0.1

def format_number(symbol, number, cache_dict, default):
    step = cache_dict.get(symbol, default)
    precision = max(0, int(round(-np.log10(step))))
    val = np.floor(number / step) * step if default == 0.001 else round(number / step) * step
    return f"{val:.{precision}f}"

# ==========================================
# MOTOR DE ÓRDENES NATIVAS Y RECOLECTOR
# ==========================================
def colocar_orden_nativa(symbol, side, position_side, quantity, order_type="MARKET", price=None, stop_price=None, reduce_only=False):
    ts = get_server_time()
    qty_str = format_number(symbol, quantity, step_size_cache, 0.001)
    
    params = {
        "symbol": symbol.upper(),
        "side": side,
        "positionSide": position_side,
        "type": order_type,
        "quantity": qty_str,
        "timestamp": str(ts)
    }
    
    if order_type == "LIMIT":
        params["price"] = format_number(symbol, price, tick_size_cache, 0.1)
        params["timeInForce"] = "GTX" # GTX = Post-Only MAKER
    elif order_type in ["STOP_MARKET", "TAKE_PROFIT_MARKET"]:
        params["timeInForce"] = "GTC"
    
    if stop_price: params["stopPrice"] = format_number(symbol, stop_price, tick_size_cache, 0.1)
    if reduce_only: params["reduceOnly"] = "true"
        
    query = urlencode(params)
    sig = hmac_lib.new(API_SECRET.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}/fapi/v1/order?{query}&signature={sig}"
    
    r = requests.post(url, headers={"X-MBX-APIKEY": API_KEY}, timeout=5)
    return r.json()

def cancelar_orden_nativa(symbol, order_id):
    """Cancela una orden huérfana en Binance para no interferir con otros scripts."""
    if not order_id: return
    try:
        ts = get_server_time()
        query = urlencode({"symbol": symbol.upper(), "orderId": order_id, "timestamp": str(ts)})
        sig = hmac_lib.new(API_SECRET.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
        url = f"{BASE_URL}/fapi/v1/order?{query}&signature={sig}"
        requests.delete(url, headers={"X-MBX-APIKEY": API_KEY}, timeout=5)
    except Exception as e:
        print(f"  [ERROR] No se pudo cancelar la orden huérfana {order_id}: {e}")

# ==========================================
# EJECUCIÓN ESTADÍSTICA DE SEÑALES
# ==========================================
def registrar_señal(raw_signal, entry, atr_usd, ctx_data, signal_id=None):
    balance_usdt = 1000.0 # Simplificado para demo
    riesgo_usdt = balance_usdt * RISK_PER_TRADE_PCT
    sl_distancia = atr_usd * ATR_MULTIPLIER_SL
    
    quantity = max(riesgo_usdt / sl_distancia, 0.001) if sl_distancia > 0 else 0.001
    
    position_side = "LONG" if raw_signal == "COMPRA" else "SHORT"
    entry_side = "BUY" if raw_signal == "COMPRA" else "SELL"
    exit_side = "SELL" if raw_signal == "COMPRA" else "BUY"
    
    order_type = "LIMIT" if USE_MAKER_ORDERS else "MARKET"
    
    # 1. Enviar orden de entrada
    resultado = colocar_orden_nativa(SYMBOL, entry_side, position_side, quantity, order_type=order_type, price=entry)
    if "code" in resultado and resultado["code"] < 0:
        print(f"  [RECHAZO] Orden MAKER rechazada (mercado muy rápido): {resultado['msg']}")
        return

    real_entry = entry
    if "avgPrice" in resultado and float(resultado["avgPrice"]) > 0:
        real_entry = float(resultado["avgPrice"])

    # 2. Calcular SL y TP (Ratios asimétricos)
    if raw_signal == "COMPRA":
        sl = round(real_entry - sl_distancia, 2)
        tp1 = round(real_entry + (atr_usd * ATR_MULTIPLIER_TP), 2)
    else:
        sl = round(real_entry + sl_distancia, 2)
        tp1 = round(real_entry - (atr_usd * ATR_MULTIPLIER_TP), 2)

    # 3. Colocar Stop Loss y Take Profit Nativo (reduceOnly) y guardar sus IDs
    sl_res = colocar_orden_nativa(SYMBOL, exit_side, position_side, quantity, "STOP_MARKET", stop_price=sl, reduce_only=True)
    tp_res = colocar_orden_nativa(SYMBOL, exit_side, position_side, quantity, "TAKE_PROFIT_MARKET", stop_price=tp1, reduce_only=True)

    print(f"  [TRADE HEDGE] {position_side} Qty: {quantity:.3f} | Ejecución: {order_type} @ {real_entry} | SL: {sl} | TP: {tp1}")

    # GUARDAR IDs en memoria para el recolector de basura
    _señales_activas[signal_id] = {
        "ts_epoch": time.time(), "raw_signal": raw_signal, "entry": real_entry, 
        "tp1": tp1, "sl": sl, "quantity": quantity, "symbol": SYMBOL, 
        "position_side": position_side, "mfe_price": real_entry, "mae_price": real_entry,
        "sl_order_id": sl_res.get("orderId"), 
        "tp_order_id": tp_res.get("orderId")
    }

def actualizar_precio(micro_price):
    """Monitor local que actúa como Recolector de Basura (OCO Tracker)."""
    cerrar = []
    for sid, s in list(_señales_activas.items()):
        # Rastrear MFE y MAE
        if s["raw_signal"] == "COMPRA":
            s["mfe_price"] = max(s["mfe_price"], micro_price)
            s["mae_price"] = min(s["mae_price"], micro_price)
        else:
            s["mfe_price"] = min(s["mfe_price"], micro_price)
            s["mae_price"] = max(s["mae_price"], micro_price)

        # Detectar si se alcanzó el TP o el SL en base al precio actual
        tp_hit = (s["raw_signal"] == "COMPRA" and micro_price >= s["tp1"]) or \
                 (s["raw_signal"] == "VENTA" and micro_price <= s["tp1"])
        sl_hit = (s["raw_signal"] == "COMPRA" and micro_price <= s["sl"]) or \
                 (s["raw_signal"] == "VENTA" and micro_price >= s["sl"])
                 
        if tp_hit:
            # Tocó TP -> Cancelar el Stop Loss de Binance
            cancelar_orden_nativa(s["symbol"], s["sl_order_id"])
            cerrar.append((sid, "WIN", s["tp1"]))
            
        elif sl_hit:
            # Tocó SL -> Cancelar el Take Profit de Binance
            cancelar_orden_nativa(s["symbol"], s["tp_order_id"])
            cerrar.append((sid, "LOSS", s["sl"]))
            
    for sid, resultado, precio_cierre in cerrar:
        s = _señales_activas.pop(sid, None)
        if s:
            print(f"  [TRADE CERRADO] {s['position_side']} | Res: {resultado} @ {precio_cierre} | Recolector de Basura activado: Órdenes huérfanas borradas.")
            
            # Actualizar log de calibración con resultado final
            for log_entry in _trade_log:
                if log_entry.get("signal_id") == sid and log_entry["resultado"] == "PENDIENTE":
                    log_entry["resultado"] = resultado
                    log_entry["precio_cierre"] = precio_cierre
                    break

# ==========================================
# CÁLCULOS MATEMÁTICOS DE MICROESTRUCTURA
# ==========================================
def calcular_obi_y_microprice(bids, asks, niveles=DEPTH_LEVELS):
    best_bid, best_ask = float(bids[0][0]), float(asks[0][0])
    spread = best_ask - best_bid
    
    bid_pressure = sum(float(b[1]) / (1 + (best_bid - float(b[0])) / spread) for b in bids[:niveles])
    ask_pressure = sum(float(a[1]) / (1 + (float(a[0]) - best_ask) / spread) for a in asks[:niveles])
    
    total_pressure = bid_pressure + ask_pressure
    if total_pressure == 0: return 0, (best_bid + best_ask) / 2
    
    obi = (bid_pressure - ask_pressure) / total_pressure
    micro_price = (best_bid * ask_pressure + best_ask * bid_pressure) / total_pressure
    return obi, micro_price

def calcular_atr(highs, lows, closes, period=14):
    """
    Calcula ATR en USD (no porcentaje) para distancias de SL/TP correctas.
    """
    if len(closes) < 15: return 0.002
    trs = []
    c_list, h_list, l_list = list(closes), list(highs), list(lows)
    for i in range(1, len(c_list)):
        h, l, pc = h_list[i], l_list[i], c_list[i-1]
        # True Range en USD absoluto, no porcentaje
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return max(float(np.mean(trs[-period:])), 0.002)

def actualizar_candles_loop(symbol, intervalo=60):
    while True:
        try:
            r = requests.get(KLINES_URL, params={"symbol": symbol.upper(), "interval": "1m", "limit": 50}, timeout=5)
            data = r.json()
            candle_closes.clear(); candle_closes.extend([float(k[4]) for k in data])
            candle_highs.clear(); candle_highs.extend([float(k[2]) for k in data])
            candle_lows.clear(); candle_lows.extend([float(k[3]) for k in data])
        except Exception: pass
        time.sleep(intervalo)

def actualizar_volume_profile_loop(symbol, intervalo=60):
    """Actualiza el historial de Volume Profile para el filtro probabilístico."""
    while True:
        try:
            vp = build_volume_profile(symbol, interval="1m", lookback=VP_LOOKBACK, bins=VP_BINS)
            if vp:
                volume_profile_history.append(vp)
        except Exception: pass
        time.sleep(intervalo)

# ==========================================
# ANÁLISIS ESPECTRAL DEL ORDER BOOK (PCA)
# ==========================================
def pca_order_book(order_book_history, n_niveles=10):
    """
    Aplica el Teorema Espectral a la matriz de covarianza del OB.
    Los autovectores son los 'modos' de desequilibrio dominantes.
    """
    if len(order_book_history) < 100:
        return None, None
    
    # Construir matriz de features: [bid_vol_1, ..., bid_vol_N, ask_vol_1, ..., ask_vol_N]
    features = []
    for snap in list(order_book_history)[-PCA_HISTORIA_SIZE:]:
        bids = [snap["bids"][i][1] if i < len(snap["bids"]) else 0 
                for i in range(n_niveles)]
        asks = [snap["asks"][i][1] if i < len(snap["asks"]) else 0 
                for i in range(n_niveles)]
        features.append(bids + asks)
    
    X = np.array(features)
    X_centrado = X - np.mean(X, axis=0)
    
    # Matriz de covarianza: simétrica → autoadjunta → Teorema Espectral aplica
    cov_matrix = np.cov(X_centrado.T)
    
    # Descomposición espectral (numpy usa el teorema implícitamente)
    autovalores, autovectores = np.linalg.eigh(cov_matrix)
    
    # Ordenar de mayor a menor varianza explicada
    idx = np.argsort(autovalores)[::-1]
    autovalores = autovalores[idx]
    autovectores = autovectores[:, idx]
    
    return autovalores, autovectores

def proyectar_snapshot_actual(snap_actual, autovectores, order_book_history, n_niveles=10):
    """
    Proyecta el estado actual del libro sobre los autovectores dominantes.
    La proyección sobre el primer autovector es el 'OBI estructural'.
    """
    bids = [snap_actual["bids"][i][1] if i < len(snap_actual["bids"]) else 0 
            for i in range(n_niveles)]
    asks = [snap_actual["asks"][i][1] if i < len(snap_actual["asks"]) else 0 
            for i in range(n_niveles)]
    x = np.array(bids + asks)
    
    # Centrar respecto a la historia
    features_hist = []
    for snap in list(order_book_history)[-PCA_HISTORIA_SIZE:]:
        b = [snap["bids"][i][1] if i < len(snap["bids"]) else 0 
             for i in range(n_niveles)]
        a = [snap["asks"][i][1] if i < len(snap["asks"]) else 0 
             for i in range(n_niveles)]
        features_hist.append(b + a)
    
    media = np.mean(features_hist, axis=0)
    x_centrado = x - media
    
    # Proyecciones sobre los primeros 3 autovectores (Prop. 9 de Labadie)
    proyecciones = [np.dot(x_centrado, autovectores[:, i]) for i in range(3)]
    
    return proyecciones

def calcular_obi_espectral(proyecciones, autovalores):
    """
    OBI ponderado por varianza explicada de cada modo.
    El primer autovalor domina si el libro tiene estructura clara.
    """
    varianza_total = np.sum(autovalores[:3])
    if varianza_total == 0:
        return 0
    
    # Proyección ponderada por varianza explicada
    pesos = autovalores[:3] / varianza_total
    obi_espectral = np.dot(proyecciones, pesos)
    
    return obi_espectral

def detectar_regimen_libro(autovalores, n_componentes=3):
    """
    Usa la descomposición espectral para clasificar el régimen del mercado.
    Basado en Prop. 11 de Labadie: si un autoespacio domina, hay estructura.
    """
    varianza_explicada = autovalores[:n_componentes] / np.sum(autovalores)
    
    ratio_primer_modo = varianza_explicada[0]
    
    if ratio_primer_modo > 0.65:
        return "ESTRUCTURADO", ratio_primer_modo   # Señales más confiables
    elif ratio_primer_modo > 0.45:
        return "MIXTO", ratio_primer_modo           # Señales moderadas
    else:
        return "RUIDOSO", ratio_primer_modo         # Evitar operar

def actualizar_pca_loop():
    """Loop en background para actualizar PCA del order book."""
    global autovalores_cache, autovectores_cache, ultimo_pca_ts, pca_regimen, pca_ratio
    
    while True:
        try:
            if len(order_book_history) >= 100:
                avals, avecs = pca_order_book(order_book_history, PCA_NIVELES)
                if avals is not None:
                    autovalores_cache = avals
                    autovectores_cache = avecs
                    regimen, ratio = detectar_regimen_libro(avals)
                    pca_regimen = regimen
                    pca_ratio = ratio
                    print(f"  [PCA] Régimen: {regimen} | Varianza modo 1: {ratio:.2%}")
        except Exception as e:
            print(f"  [PCA ERROR] {e}")
        time.sleep(PCA_REFRESH_SECONDS)

def extraer_retornos_empiricos(order_book_history):
    """Extrae retornos tick-a-tick del micro_price histórico."""
    if len(order_book_history) < 50:
        return []
    micro_prices = [snap["micro_price"] for snap in list(order_book_history)]
    retornos = np.diff(micro_prices) / np.array(micro_prices[:-1])
    return retornos.tolist()

def ajustar_retornos_por_vp(retornos, entry, vp_poc, vp_val, vp_vah):
    """
    Ajuste de retornos según Volume Profile (Labadie mean-reversion).
    Cerca del POC: el mercado revierte → sesgar retornos hacia la media.
    Fuera del VA: el mercado tiende a volver → sesgar hacia el interior.
    """
    if vp_poc is None:
        return retornos
    
    dist_al_poc = (entry - vp_poc) / vp_poc  # positivo = por encima
    
    # Si estás muy lejos del POC, el mercado tiene presión de reversión
    # Esto sesga empíricamente la distribución de retornos
    factor_sesgo = np.clip(-dist_al_poc * 5, -0.3, 0.3)
    
    return retornos + factor_sesgo * np.std(retornos)

def calcular_prob_bs_empirico(raw_signal, entry, tp, sl, 
                               retornos_empiricos, atr_pct,
                               n_sims=3000, pasos=150):
    """
    Híbrido: usa la estructura matemática de Black-Scholes (Euler + Monte Carlo)
    pero con distribución empírica en lugar de Normal.
    
    Documentos de Labadie usados:
    - Esquema de Euler (doc 4: procesos estocásticos)
    - Bootstrapping empírico (doc 2: stat arb)
    - N(d2) como probabilidad baseline (Black-Scholes)
    """
    
    if len(retornos_empiricos) < 100:
        return 0.50, 0.50, 0.50
    
    dist_tp = abs(tp - entry) / entry   # en % del precio
    dist_sl = abs(sl - entry) / entry
    
    # ---- MÉTODO 1: Black-Scholes Analítico (Baseline) ----
    # Usa la estructura de N(d2) pero con sigma empírico (ATR)
    T = pasos / 1500  # tiempo normalizado por ticks
    sigma = atr_pct * np.sqrt(1500)  # sigma anualizado aproximado
    
    if raw_signal == "COMPRA":
        d2 = (np.log(entry / tp) + (-0.5 * sigma**2) * T) / (sigma * np.sqrt(T) + 1e-10)
        prob_analitica = 1 - normal_cdf(d2)  # P(S_T > TP)
    else:
        d2 = (np.log(tp / entry) + (-0.5 * sigma**2) * T) / (sigma * np.sqrt(T) + 1e-10)
        prob_analitica = 1 - normal_cdf(d2)
    
    # ---- MÉTODO 2: Monte Carlo Empírico (Euler con distribución real) ----
    retornos = np.array(retornos_empiricos)
    direccion = 1 if raw_signal == "COMPRA" else -1
    exitos = 0
    
    for _ in range(n_sims):
        precio = entry
        # Esquema de Euler con epsilon empírico (no gaussiano)
        epsilons = np.random.choice(retornos, size=pasos, replace=True)
        resultado = None
        
        for eps in epsilons:
            # dS = sigma * dW → aquí dW ~ distribución empírica
            precio *= (1 + eps * direccion)
            movimiento_pct = (precio - entry) / entry * direccion
            
            if movimiento_pct >= dist_tp:
                resultado = "WIN"
                break
            elif movimiento_pct <= -dist_sl:
                resultado = "LOSS"
                break
        
        if resultado == "WIN":
            exitos += 1
    
    prob_empirica = exitos / n_sims
    
    # ---- COMBINACIÓN: Promedio ponderado ----
    # BS como prior, empírico como likelihood (estilo Bayesiano)
    peso_bs = 0.3      # El modelo teórico aporta estructura
    peso_emp = 0.70    # Los datos reales dominan
    prob_final = peso_bs * prob_analitica + peso_emp * prob_empirica
    
    return prob_final, prob_empirica, prob_analitica

# ==========================================
# MOTOR WEBSOCKET EN VIVO
# ==========================================
def on_message(ws, message):
    global last_signal_time, last_signal_side
    data = json.loads(message)
    payload = data.get('data', data)
    if 'bids' not in payload: return
    bids, asks = payload['bids'], payload['asks']
    if not bids or not asks: return
    
    obi_actual, micro_price = calcular_obi_y_microprice(bids, asks)
    obi_history.append(obi_actual)
    
    # Guardar snapshot completo del order book para distribución empírica
    order_book_snapshot = {
        "bids": [[float(b[0]), float(b[1])] for b in bids[:DEPTH_LEVELS]],
        "asks": [[float(a[0]), float(a[1])] for a in asks[:DEPTH_LEVELS]],
        "obi": obi_actual,
        "micro_price": micro_price,
        "timestamp": time.time()
    }
    order_book_history.append(order_book_snapshot)
    
    # Evaluar precios para el Recolector de Basura
    actualizar_precio(micro_price)

    if len(obi_history) < WARMUP_TICKS:
        if len(obi_history) % 150 == 0:
            restantes = WARMUP_TICKS - len(obi_history)
            print(f"  [WARMUP Z-SCORE] Extrayendo order book... {len(obi_history)}/{WARMUP_TICKS} ticks (Faltan ~{restantes * 0.1:.0f}s)")
        return

    obi_array = np.array(obi_history)
    std_obi = np.std(obi_array)
    if std_obi == 0: return
    z_score = (obi_actual - np.mean(obi_array)) / std_obi

    raw_signal = None
    if z_score >= Z_SCORE_THRESHOLD: raw_signal = "COMPRA"
    elif z_score <= -Z_SCORE_THRESHOLD: raw_signal = "VENTA"
    
    if raw_signal is None: return
    if raw_signal == last_signal_side and (time.time() - last_signal_time) < COOLDOWN_SECONDS: return
    
    # Filtro espectral de régimen (PCA del Order Book)
    if autovalores_cache is not None and autovectores_cache is not None:
        regimen, ratio = detectar_regimen_libro(autovalores_cache)
        
        if regimen == "RUIDOSO":
            print(f"  [FILTRO ESPECTRAL] Régimen RUIDOSO (ratio: {ratio:.2%}) → No operar")
            return  # Libro sin estructura → no operar
        
        # OBI espectral como señal complementaria
        proyecciones = proyectar_snapshot_actual(
            order_book_snapshot, autovectores_cache, order_book_history, PCA_NIVELES
        )
        obi_espectral = calcular_obi_espectral(proyecciones, autovalores_cache[:3])
        
        # Confirmar que OBI clásico y OBI espectral apuntan en la misma dirección
        if raw_signal == "COMPRA" and obi_espectral < 0:
            print(f"  [FILTRO ESPECTRAL] OBI espectral ({obi_espectral:.3f}) contradice señal COMPRA → descartado")
            return
        elif raw_signal == "VENTA" and obi_espectral > 0:
            print(f"  [FILTRO ESPECTRAL] OBI espectral ({obi_espectral:.3f}) contradice señal VENTA → descartado")
            return
    
    atr_pct = calcular_atr(candle_highs, candle_lows, candle_closes, period=14)
    best_bid, best_ask = float(bids[0][0]), float(asks[0][0])
    
    # Asignación de precio de entrada (MAKER vs TAKER)
    if USE_MAKER_ORDERS:
        entry = best_bid if raw_signal == "COMPRA" else best_ask 
    else:
        spread = best_ask - best_bid
        entry = round(best_ask - (spread * 0.3), 2) if raw_signal == "COMPRA" else round(best_bid + (spread * 0.3), 2)

    atr_usd = entry * atr_pct
    
    # Calcular SL y TP para el filtro probabilístico
    sl_distancia = atr_usd * ATR_MULTIPLIER_SL
    if raw_signal == "COMPRA":
        sl = round(entry - sl_distancia, 2)
        tp1 = round(entry + (atr_usd * ATR_MULTIPLIER_TP), 2)
    else:
        sl = round(entry + sl_distancia, 2)
        tp1 = round(entry - (atr_usd * ATR_MULTIPLIER_TP), 2)
    
    # Filtro Probabilístico Híbrido (Black-Scholes + Monte Carlo Empírico)
    retornos = extraer_retornos_empiricos(list(order_book_history))
    
    prob_final, prob_empirica, prob_analitica = calcular_prob_bs_empirico(
        raw_signal=raw_signal,
        entry=entry,
        tp=tp1,
        sl=sl,
        retornos_empiricos=retornos,
        atr_pct=atr_pct,
        n_sims=2000,   # Reducido para latencia (≈ 0.3 seg)
        pasos=150
    )
    
    if prob_final < PROBABILIDAD_MINIMA:
        print(f"  [FILTRO BS+EMPIRICO] Descartado | BS: {prob_analitica:.2%} | Empírico: {prob_empirica:.2%} | Final: {prob_final:.2%}")
        # Loguear señal rechazada para calibración
        _trade_log.append({
            "z_score": z_score,
            "prob_bs": prob_analitica,
            "prob_emp": prob_empirica,
            "prob_final": prob_final,
            "resultado": "RECHAZADO",
            "timestamp": time.time(),
            "raw_signal": raw_signal
        })
        return  # EL BOT NO OPERA SI LA ESTADÍSTICA NO ACOMPAÑA
    
    print(f"  [PROB APROBADA] BS: {prob_analitica:.2%} | Empírico: {prob_empirica:.2%} | Final: {prob_final:.2%} | Z-Score: {z_score:.2f}")
    
    last_signal_side = raw_signal
    last_signal_time = time.time()
    
    signal_id = str(uuid.uuid4())
    # Loguear señal aprobada para calibración
    _trade_log.append({
        "z_score": z_score,
        "prob_bs": prob_analitica,
        "prob_emp": prob_empirica,
        "prob_final": prob_final,
        "resultado": "PENDIENTE",
        "timestamp": time.time(),
        "raw_signal": raw_signal,
        "signal_id": signal_id
    })
    
    registrar_señal(raw_signal, entry, atr_usd, {"ctx_z_score": z_score, "ctx_prob": prob_final, "ctx_prob_bs": prob_analitica, "ctx_prob_emp": prob_empirica}, signal_id)

def on_error(ws, error): print(f"Error: {error}", flush=True)
def on_close(ws, *args): print("Desconectado.", flush=True)
def on_open(ws):
    print("=" * 65)
    print(f"  Scalping OBI HFT - Futuros {SYMBOL} - Demo Mode")
    print("  Entorno: HEDGE MODE | MARGEN CRUZADO (CROSSED)")
    print(f"  Ejecución: {'MAKER (Post-Only LIMIT)' if USE_MAKER_ORDERS else 'TAKER (MARKET)'}")
    print(f"  Ratios: SL = {ATR_MULTIPLIER_SL} ATR | TP = {ATR_MULTIPLIER_TP} ATR (RR Bruto: {ATR_MULTIPLIER_TP/ATR_MULTIPLIER_SL:.2f})")
    print("  Filtro Probabilístico: Black-Scholes + Monte Carlo Empírico (Labadie)")
    print(f"  Combinación: 30% BS (N(d2)) + 70% Empírico (Euler scheme)")
    print(f"  Probabilidad Mínima: {PROBABILIDAD_MINIMA:.0%}")
    print("=" * 65, flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    args = parser.parse_args()

    print("Configurando entorno automáticamente...")
    cargar_filtros_simbolo(SYMBOL)
    get_commission_rate(SYMBOL)
    configurar_entorno_cuenta(SYMBOL, LEVERAGE)

    print("Inicializando Hilos de Contexto...")
    threading.Thread(target=actualizar_candles_loop, args=(SYMBOL, 60), daemon=True).start()
    threading.Thread(target=actualizar_volume_profile_loop, args=(SYMBOL, 60), daemon=True).start()
    threading.Thread(target=actualizar_pca_loop, daemon=True).start()

    stream_url = f"{WS_URL}?streams={SYMBOL.lower()}@depth20@100ms"
    ws = websocket.WebSocketApp(stream_url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.run_forever()