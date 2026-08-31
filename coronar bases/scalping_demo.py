import uuid, websocket, json, numpy as np, requests, threading, time, argparse, hmac, hashlib, os
from collections import deque, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv("capital-navigator-main/.env")

# ─────────────────────────────────────────────
#  PARÁMETROS GLOBALES
# ─────────────────────────────────────────────
WINDOW_SIZE        = 500
Z_SCORE_THRESHOLD  = 2.2
DEPTH_LEVELS       = 10
VWAP_WINDOW        = 500
VP_BINS            = 50
VP_LOOKBACK        = 300
TIMEOUT_SEG        = 180
COOLDOWN_SECONDS   = 60
MIN_CTX_SECONDS    = 15
QUANTITY           = 0.001
SYMBOL             = "BTCUSDT"
OBI_THRESHOLD      = 0.15
ATR_MULTIPLIER_SL  = 1.0
ATR_MULTIPLIER_TP  = 2.5
MAX_SIGNALS_ACTIVOS = 1

# Variables globales para ajuste dinámico (modificables en runtime)
current_z_threshold = Z_SCORE_THRESHOLD
current_obi_threshold = OBI_THRESHOLD
threshold_lock = threading.Lock()

# ─────────────────────────────────────────────
#  ENDPOINTS DEMO  (demo-api.binance.com)
# ─────────────────────────────────────────────
BASE_URL        = "https://demo-api.binance.com"
WS_BASE_URL     = "wss://demo-api.binance.com"
# Klines y datos de mercado públicos siguen viniendo de la API real
MARKET_API_URL  = "https://api.binance.com"

API_KEY    = ""
API_SECRET = ""


# ─────────────────────────────────────────────
#  HELPERS DE FIRMA Y ÓRDENES
# ─────────────────────────────────────────────
def get_server_time() -> int:
    r = requests.get(f"{BASE_URL}/api/v3/time", timeout=5)
    r.raise_for_status()
    return r.json()["serverTime"]


def _sign(params: dict) -> str:
    query = urlencode(params)
    return hmac.new(
        API_SECRET.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def colocar_orden(symbol: str, side: str, quantity: float, order_type: str = "MARKET") -> dict:
    ts = get_server_time()
    qty_str = f"{quantity:.8f}".rstrip("0").rstrip(".")
    params = {
        "symbol":    symbol.upper(),
        "side":      side,
        "type":      order_type,
        "quantity":  qty_str,
        "timestamp": str(ts),
    }
    sig = _sign(params)
    url = f"{BASE_URL}/api/v3/order?{urlencode(params)}&signature={sig}"
    r = requests.post(url, headers={"X-MBX-APIKEY": API_KEY}, timeout=5)
    j = r.json()
    if "code" in j:
        print(f"  [ORDER ERROR] {j}", flush=True)
    return j


def cerrar_posicion(symbol: str, side_actual: str, quantity: float) -> dict:
    side_cierre = "SELL" if side_actual == "COMPRA" else "BUY"
    return colocar_orden(symbol, side_cierre, quantity)


# ─────────────────────────────────────────────
#  ESTADO GLOBAL
# ─────────────────────────────────────────────
estado_mercado = {
    "trend_5m": "UNKNOWN",
    "vp_poc": None, "vp_val": None, "vp_vah": None,
    "obs": {"alcistas": [], "bajistas": []},
    "ts": 0,
}
estado_lock      = threading.Lock()
obi_history      = deque(maxlen=WINDOW_SIZE)
price_history    = deque(maxlen=50)
vwap_prices      = deque(maxlen=VWAP_WINDOW)
vwap_volumes     = deque(maxlen=VWAP_WINDOW)
last_signal      = None
last_signal_side = None
last_signal_time = 0.0
candle_closes    = deque(maxlen=50)
_señales_activas: dict = {}


# ─────────────────────────────────────────────
#  GESTIÓN DE SEÑALES ACTIVAS
# ─────────────────────────────────────────────
def actualizar_precio(micro_price: float) -> None:
    cerrar = []
    for sid, s in list(_señales_activas.items()):
        elapsed = time.time() - s["ts_epoch"]
        tp_hit = (s["raw_signal"] == "COMPRA" and micro_price >= s["tp1"]) or \
                 (s["raw_signal"] == "VENTA"  and micro_price <= s["tp1"])
        sl_hit = (s["raw_signal"] == "COMPRA" and micro_price <= s["sl"]) or \
                 (s["raw_signal"] == "VENTA"  and micro_price >= s["sl"])
        if tp_hit:               cerrar.append((sid, "WIN",     micro_price, elapsed))
        elif sl_hit:             cerrar.append((sid, "LOSS",    micro_price, elapsed))
        elif elapsed > TIMEOUT_SEG: cerrar.append((sid, "TIMEOUT", micro_price, elapsed))
    for sid, resultado, precio, dur in cerrar:
        _cerrar_señal(sid, resultado, precio, dur)


def _cerrar_señal(signal_id: str, resultado: str, precio_cierre: float, duracion_seg: float) -> None:
    s = _señales_activas.pop(signal_id, None)
    if s is None:
        return
    entry = s["entry"]
    if API_KEY and API_SECRET:
        cerrar_posicion(s["symbol"], s["raw_signal"], s["quantity"])
    pnl = ((precio_cierre - entry) / entry * 100) if s["raw_signal"] == "COMPRA" \
          else ((entry - precio_cierre) / entry * 100)
    print(
        f"  [{resultado}] {s['raw_signal']}  "
        f"entry={entry:.2f} -> cierre={precio_cierre:.2f}  "
        f"PnL={pnl:+.2f}%  ({duracion_seg:.0f}s)",
        flush=True,
    )


def registrar_señal(
    raw_signal: str, entry: float, tp1: float, sl: float,
    signal_id: str | None = None, quantity: float = QUANTITY
) -> None:
    _señales_activas[signal_id] = {
        "ts":        datetime.now(timezone.utc).isoformat(),
        "ts_epoch":  time.time(),
        "raw_signal": raw_signal,
        "entry":     entry,
        "tp1":       tp1,
        "sl":        sl,
        "signal_id": signal_id,
        "quantity":  quantity,
        "symbol":    SYMBOL,
    }
    if API_KEY and API_SECRET:
        side = "BUY" if raw_signal == "COMPRA" else "SELL"
        resultado = colocar_orden(SYMBOL, side, quantity)
        order_id = resultado.get("orderId", "ERROR")
        status   = resultado.get("status", resultado.get("msg", "?"))
        print(f"  [ORDER] {side} qty={quantity} orderId={order_id} status={status}", flush=True)
        _señales_activas[signal_id]["order_id"] = order_id


# ─────────────────────────────────────────────
#  CONTEXTO DE MERCADO  (usa API pública real)
# ─────────────────────────────────────────────
def get_trend_5min(symbol: str = "BTCUSDT") -> str:
    for attempt in range(3):
        try:
            r = requests.get(
                f"{MARKET_API_URL}/api/v3/klines",
                params={"symbol": symbol.upper(), "interval": "5m", "limit": 4},
                timeout=5,
            )
            closes = [float(c[4]) for c in r.json()]
            if   closes[-1] > closes[-2] > closes[-3]: return "UP"
            elif closes[-1] < closes[-2] < closes[-3]: return "DOWN"
            return "FLAT"
        except Exception:
            if attempt < 2: time.sleep(2 ** attempt)
    return "UNKNOWN"


def build_volume_profile(
    symbol: str = "BTCUSDT", interval: str = "1m",
    lookback: int = VP_LOOKBACK, bins: int = VP_BINS
) -> dict | None:
    for attempt in range(3):
        try:
            r = requests.get(
                f"{MARKET_API_URL}/api/v3/klines",
                params={"symbol": symbol.upper(), "interval": interval, "limit": lookback},
                timeout=5,
            )
            klines = r.json()
            price_vol: dict[float, float] = defaultdict(float)
            price_min, price_max = float("inf"), float("-inf")
            for k in klines:
                high, low, vol = float(k[2]), float(k[3]), float(k[5])
                mid = (high + low) / 2
                price_vol[round(mid, 0)] += vol
                price_min = min(price_min, low)
                price_max = max(price_max, high)
            if not price_vol or price_min == price_max:
                return None
            bin_edges   = np.linspace(price_min, price_max, bins + 1)
            bin_vols    = np.zeros(bins)
            bin_centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(bins)]
            for price, vol in price_vol.items():
                for i in range(bins):
                    if bin_edges[i] <= price < bin_edges[i + 1]:
                        bin_vols[i] += vol
                        break
            total_vol = np.sum(bin_vols)
            if total_vol == 0:
                return None
            poc_idx = int(np.argmax(bin_vols))
            poc     = bin_centers[poc_idx]
            target  = total_vol * 0.70
            acum    = bin_vols[poc_idx]
            lo_idx = hi_idx = poc_idx
            while acum < target:
                up = hi_idx + 1 < bins
                dn = lo_idx - 1 >= 0
                if not up and not dn:
                    break
                vu = bin_vols[hi_idx + 1] if up else -1.0
                vd = bin_vols[lo_idx - 1] if dn else -1.0
                if vu >= vd:
                    hi_idx += 1; acum += bin_vols[hi_idx]
                else:
                    lo_idx -= 1; acum += bin_vols[lo_idx]
            return {"poc": poc, "val": bin_centers[lo_idx], "vah": bin_centers[hi_idx]}
        except Exception:
            if attempt < 2: time.sleep(2 ** attempt)
    return None


def detectar_order_blocks(
    symbol: str = "BTCUSDT", interval: str = "1m", lookback: int = 50
) -> dict:
    for attempt in range(3):
        try:
            r = requests.get(
                f"{MARKET_API_URL}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "limit": lookback},
                timeout=5,
            )
            klines  = r.json()
            alcistas, bajistas = [], []
            cuerpos = [abs(float(k[4]) - float(k[1])) for k in klines]
            cp_mean = np.mean(cuerpos)
            for i in range(1, len(klines) - 1):
                op_  = float(klines[i][1]);  hp_  = float(klines[i][2])
                lp_  = float(klines[i][3]);  cp_  = float(klines[i][4])
                vp_  = float(klines[i][5])
                on_  = float(klines[i + 1][1]); cn_ = float(klines[i + 1][4])
                vn_  = float(klines[i + 1][5])
                body = abs(cn_ - on_)
                if cp_ < op_ and cn_ > on_ and body >= cp_mean * 2 and vn_ > vp_:
                    alcistas.append({"tipo": "OB_ALCISTA", "high": hp_, "low": lp_,
                                     "mid": (hp_ + lp_) / 2, "activo": True})
                if cp_ > op_ and cn_ < on_ and body >= cp_mean * 2 and vn_ > vp_:
                    bajistas.append({"tipo": "OB_BAJISTA", "high": hp_, "low": lp_,
                                     "mid": (hp_ + lp_) / 2, "activo": True})
            return {"alcistas": alcistas[-3:], "bajistas": bajistas[-3:]}
        except Exception:
            if attempt < 2: time.sleep(2 ** attempt)
    return {"alcistas": [], "bajistas": []}


def get_ob_contexto(micro_price: float, obs: dict) -> dict:
    TOL = 0.0015
    mejor_dist = float("inf")
    zona, accion = "FUERA_OB", "NEUTRO"
    for ob in obs["alcistas"]:
        if not ob["activo"]: continue
        if ob["low"] <= micro_price <= ob["high"]:
            return {"zona": "DENTRO_OB_ALCISTA", "accion": "LONG"}
        d = abs(micro_price - ob["high"]) / micro_price
        if d < TOL and d < mejor_dist:
            mejor_dist = d; zona = "CERCA_OB_ALCISTA"; accion = "LONG"
    for ob in obs["bajistas"]:
        if not ob["activo"]: continue
        if ob["low"] <= micro_price <= ob["high"]:
            return {"zona": "DENTRO_OB_BAJISTA", "accion": "SHORT"}
        d = abs(micro_price - ob["low"]) / micro_price
        if d < TOL and d < mejor_dist:
            mejor_dist = d; zona = "CERCA_OB_BAJISTA"; accion = "SHORT"
    return {"zona": zona, "accion": accion}


def invalidar_obs(obs: dict, micro_price: float) -> dict:
    for ob in obs["alcistas"]:
        if micro_price < ob["low"] * 0.999: ob["activo"] = False
    for ob in obs["bajistas"]:
        if micro_price > ob["high"] * 1.001: ob["activo"] = False
    return obs


def actualizar_contexto_loop(symbol: str, intervalo: int = 60) -> None:
    while True:
        try:
            trend = get_trend_5min(symbol)
            vp    = build_volume_profile(symbol)
            obs   = detectar_order_blocks(symbol)
            with estado_lock:
                estado_mercado["trend_5m"] = trend
                if vp:
                    estado_mercado["vp_poc"] = vp["poc"]
                    estado_mercado["vp_val"] = vp["val"]
                    estado_mercado["vp_vah"] = vp["vah"]
                estado_mercado["obs"] = obs
                estado_mercado["ts"]  = time.time()
        except Exception as e:
            print(f"  [CTX ERROR] {e}", flush=True)
        time.sleep(intervalo)


def actualizar_candles_loop(symbol: str, intervalo: int = 60) -> None:
    while True:
        try:
            r = requests.get(
                f"{MARKET_API_URL}/api/v3/klines",
                params={"symbol": symbol.upper(), "interval": "1m", "limit": 50},
                timeout=5,
            )
            r.raise_for_status()
            closes = [float(k[4]) for k in r.json()]
            candle_closes.clear()
            candle_closes.extend(closes)
        except Exception as e:
            print(f"  [CANDLE ERROR] {e}", flush=True)
        time.sleep(intervalo)


def calcular_volatilidad_mercado(symbol: str = "BTCUSDT") -> float:
    """Calcula volatilidad reciente del mercado usando ATR de 15m"""
    try:
        r = requests.get(
            f"{MARKET_API_URL}/api/v3/klines",
            params={"symbol": symbol.upper(), "interval": "15m", "limit": 20},
            timeout=5,
        )
        r.raise_for_status()
        klines = r.json()
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        closes = [float(k[4]) for k in klines]
        
        trs = []
        for i in range(1, len(klines)):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i-1]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        
        if not trs:
            return 0.001  # valor por defecto
        
        atr = sum(trs) / len(trs)
        avg_price = sum(closes) / len(closes)
        return atr / avg_price  # volatilidad como porcentaje
    except Exception as e:
        print(f"  [VOLATILIDAD ERROR] {e}", flush=True)
        return 0.001


def ajustar_thresholds_dinamicamente(symbol: str = "BTCUSDT", intervalo_horas: int = 3) -> None:
    """Ajusta Z_SCORE_THRESHOLD y OBI_THRESHOLD según volatilidad del mercado cada 2-4 horas"""
    base_z_threshold = 2.2
    base_obi_threshold = 0.15
    
    while True:
        try:
            vol = calcular_volatilidad_mercado(symbol)
            
            # Ajuste basado en volatilidad (Labadie: adaptar al régimen de mercado)
            # Volatilidad baja (<0.5%): thresholds más bajos para capturar más señales
            # Volatilidad media (0.5%-1.5%): thresholds base
            # Volatilidad alta (>1.5%): thresholds más altos para evitar ruido
            
            with threshold_lock:
                global current_z_threshold, current_obi_threshold
                
                if vol < 0.005:  # baja volatilidad
                    current_z_threshold = base_z_threshold * 0.85
                    current_obi_threshold = base_obi_threshold * 0.85
                elif vol < 0.015:  # volatilidad media
                    current_z_threshold = base_z_threshold
                    current_obi_threshold = base_obi_threshold
                else:  # alta volatilidad
                    current_z_threshold = base_z_threshold * 1.15
                    current_obi_threshold = base_obi_threshold * 1.15
                
                print(f"  [THRESHOLD ADJUST] Vol:{vol:.4f} Z:{current_z_threshold:.2f} OBI:{current_obi_threshold:.3f}", flush=True)
        
        except Exception as e:
            print(f"  [THRESHOLD ERROR] {e}", flush=True)
        
        time.sleep(intervalo_horas * 3600)  # convertir horas a segundos


# ─────────────────────────────────────────────
#  INDICADORES
# ─────────────────────────────────────────────
def get_vp_zona_live(micro_price: float) -> tuple[str, float]:
    with estado_lock:
        poc = estado_mercado["vp_poc"]
        val = estado_mercado["vp_val"]
        vah = estado_mercado["vp_vah"]
    if poc is None:
        return "VP_CALCULANDO", 0.0
    dist_poc = (micro_price - poc) / poc * 100
    if   micro_price > vah:      return "SOBRE_VAH",  dist_poc
    elif micro_price < val:      return "BAJO_VAL",   dist_poc
    elif abs(dist_poc) < 0.05:   return "EN_POC",     dist_poc
    return "DENTRO_VA", dist_poc


def calcular_obi(bids: list, asks: list, niveles: int = DEPTH_LEVELS) -> tuple[float, float, float]:
    bid_vol = sum(float(b[1]) for b in bids[:niveles])
    ask_vol = sum(float(a[1]) for a in asks[:niveles])
    total   = bid_vol + ask_vol
    if total == 0:
        return 0.0, 0.0, 0.0
    obi        = (bid_vol - ask_vol) / total
    best_bid   = float(bids[0][0])
    best_ask   = float(asks[0][0])
    micro_price = (best_bid * ask_vol + best_ask * bid_vol) / total
    spread_pct  = (best_ask - best_bid) / best_ask * 100
    return obi, micro_price, spread_pct


def calcular_vwap(prices: list, volumes: list) -> float | None:
    if len(prices) < 2:
        return None
    p = np.array(prices)
    v = np.array(volumes)
    return float(np.sum(p * v) / np.sum(v))


def get_price_momentum(prices: list) -> tuple[float, str]:
    if len(prices) < 10:
        return 0.0, "CALCULANDO"
    arr       = np.array(prices)
    slope     = np.polyfit(np.arange(len(arr)), arr, 1)[0]
    slope_pct = slope / np.mean(arr) * 100
    if   slope_pct >  0.0001: return slope_pct, "SUBIENDO"
    elif slope_pct < -0.0001: return slope_pct, "BAJANDO"
    return slope_pct, "LATERAL"


def get_rsi(prices, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    arr    = np.array(list(prices)[-(period + 1):])
    deltas = np.diff(arr)
    gains  = np.where(deltas > 0,  deltas,  0.0)
    losses = np.where(deltas < 0, -deltas,  0.0)
    ag, al = float(np.mean(gains)), float(np.mean(losses))
    if al == 0: return 100.0
    if ag == 0: return   0.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def calcular_atr(prices, candles=None) -> float | None:
    if candles is not None and len(candles) >= 15:
        arr = np.array(list(candles)[-20:])
        trs = np.abs(np.diff(arr) / arr[:-1])
        return float(np.mean(trs[-14:]))
    if len(prices) < 20:
        return None
    arr = np.array(list(prices)[-30:])
    return float(np.mean(np.abs(np.diff(arr) / arr[:-1])))


def get_aggressor_bias(bids: list, asks: list) -> str:
    top_bid = sum(float(b[1]) for b in bids[:3])
    top_ask = sum(float(a[1]) for a in asks[:3])
    ratio   = top_bid / (top_bid + top_ask + 1e-9)
    if   ratio > 0.60: return "BUY_PRESSURE"
    elif ratio < 0.40: return "SELL_PRESSURE"
    return "NEUTRAL"


def calcular_niveles(
    micro_price: float, raw_signal: str,
    bids: list, asks: list, obi_actual: float, atr_pct: float | None = None, poc: float | None = None
) -> dict | None:
    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])
    spread   = best_ask - best_bid
    if not atr_pct: atr_pct = 0.0015
    atr_usd  = micro_price * atr_pct
    if raw_signal == "COMPRA":
        tick   = spread * 0.3
        entry  = round(best_ask - tick, 2)
        sl     = round(entry - max(atr_usd * ATR_MULTIPLIER_SL, entry * 0.0010), 2)
        # Usar POC como TP dinámico si está disponible y es favorable
        if poc and poc > entry:
            tp1 = round(poc, 2)
        else:
            tp1 = round(entry + (entry - sl) * 1.5, 2)
        riesgo = (entry - sl)  / entry * 100
        reward = (tp1  - entry) / entry * 100
    elif raw_signal == "VENTA":
        tick   = spread * 0.3
        entry  = round(best_bid + tick, 2)
        sl     = round(entry + max(atr_usd * ATR_MULTIPLIER_SL, entry * 0.0010), 2)
        # Usar POC como TP dinámico si está disponible y es favorable
        if poc and poc < entry:
            tp1 = round(poc, 2)
        else:
            tp1 = round(entry - (sl - entry) * 1.5, 2)
        riesgo = (sl - entry) / entry * 100
        reward = (entry - tp1) / entry * 100
    else:
        return None
    return {"entry": entry, "sl": sl, "tp1": tp1,
            "riesgo_pct": riesgo, "reward_pct": reward, "spread_usd": spread}


def clasificar_señal(z: float, obi: float) -> tuple[str, str]:
    if   z <= -Z_SCORE_THRESHOLD and obi <  0: return "TIPO_A", "Sellers activos"
    elif z <= -Z_SCORE_THRESHOLD and obi >= 0: return "TIPO_B", "Compradores retirandose"
    elif z >=  Z_SCORE_THRESHOLD and obi >  0: return "TIPO_A", "Buyers activos"
    elif z >=  Z_SCORE_THRESHOLD and obi <= 0: return "TIPO_B", "Vendedores retirandose"
    return "NEUTRAL", ""


# ─────────────────────────────────────────────
#  WEBSOCKET
# ─────────────────────────────────────────────
def on_message(ws, message):
    global last_signal, last_signal_time, last_signal_side

    data    = json.loads(message)
    payload = data.get("data", data)
    if "bids" not in payload: return
    bids = payload["bids"]
    asks = payload["asks"]
    if not bids or not asks: return

    obi_actual, micro_price, spread_pct = calcular_obi(bids, asks)
    actualizar_precio(micro_price)
    price_history.append(micro_price)
    vwap_prices.append(micro_price)
    vwap_volumes.append(float(bids[0][1]) + float(asks[0][1]))
    obi_history.append(obi_actual)

    if len(obi_history) < WINDOW_SIZE:
        if len(obi_history) % 100 == 0:
            print(f"  Calentando OBI... {len(obi_history)}/{WINDOW_SIZE}", flush=True)
        return

    obi_array = np.array(obi_history)
    std_obi   = float(np.std(obi_array))
    if std_obi == 0: return
    z_score   = (obi_actual - float(np.mean(obi_array))) / std_obi

    recientes           = list(obi_history)[-50:]
    volatilidad_reciente = np.std(recientes) if len(recientes) >= 10 else std_obi
    ratio_vol           = volatilidad_reciente / std_obi if std_obi > 0 else 1.0
    
    # Usar threshold dinámico ajustado por volatilidad de mercado
    with threshold_lock:
        z_threshold = current_z_threshold
        obi_threshold = current_obi_threshold
    
    threshold_dinamico  = z_threshold * max(0.85, min(1.10, ratio_vol))

    raw_signal = None
    if   z_score >=  threshold_dinamico: raw_signal = "COMPRA"
    elif z_score <= -threshold_dinamico: raw_signal = "VENTA"
    if raw_signal is None: return
    if raw_signal == last_signal: return

    # FILTRO 1: Máximo señales activas (inventario)
    if len(_señales_activas) >= MAX_SIGNALS_ACTIVOS:
        return

    # FILTRO 2: Contexto fresco
    with estado_lock:
        trend_5m = estado_mercado["trend_5m"]
        ctx_age  = time.time() - estado_mercado["ts"]
    if ctx_age < MIN_CTX_SECONDS: return

    # FILTRO 3: Cooldown
    t_since = time.time() - last_signal_time
    if raw_signal == last_signal_side and t_since < COOLDOWN_SECONDS: return

    # FILTRO 4: Solo a favor de tendencia — sin FLAT, sin contra-tendencia
    if trend_5m == "FLAT": return
    if raw_signal == "COMPRA" and trend_5m != "UP": return
    if raw_signal == "VENTA" and trend_5m != "DOWN": return

    # FILTRO 5: OBI confirmación obligatoria
    obi_confirm = "PASS" if (
        (raw_signal == "COMPRA" and obi_actual >  obi_threshold) or
        (raw_signal == "VENTA"  and obi_actual < -obi_threshold)
    ) else "FAIL"
    if obi_confirm != "PASS": return

    # FILTRO 6: Aggressor contrario bloquea
    aggressor  = get_aggressor_bias(bids, asks)
    agg_contra = (raw_signal == "COMPRA" and aggressor == "SELL_PRESSURE") or \
                 (raw_signal == "VENTA"  and aggressor == "BUY_PRESSURE")
    if agg_contra: return

    # FILTRO 7: Solo TIPO_A
    tipo_señal, desc_señal = clasificar_señal(z_score, obi_actual)
    if tipo_señal != "TIPO_A": return

    # FILTRO 8: RSI
    rsi_fast = get_rsi(price_history, period=14)
    rsi_slow = get_rsi(candle_closes, period=14) if len(candle_closes) >= 15 else 50.0
    if raw_signal == "COMPRA" and rsi_slow > 65: return
    if raw_signal == "VENTA"  and rsi_slow < 35: return
    if raw_signal == "COMPRA" and (rsi_fast > 80 or rsi_fast < 10): return
    if raw_signal == "VENTA"  and (rsi_fast < 20 or rsi_fast > 90): return

    # FILTRO 9: Volume Profile zona
    vwap       = calcular_vwap(list(vwap_prices), list(vwap_volumes))
    vwap_bias  = ("ABOVE" if micro_price > vwap else "BELOW") if vwap else "UNKNOWN"
    dist_vwap  = (micro_price - vwap) / vwap * 100 if vwap else 0.0
    vp_zona, dist_poc = get_vp_zona_live(micro_price)

    if raw_signal == "COMPRA" and vp_zona not in ["BAJO_VAL", "EN_POC", "DENTRO_VA"]: return
    if raw_signal == "VENTA"  and vp_zona not in ["SOBRE_VAH", "EN_POC", "DENTRO_VA"]: return

    # FILTRO 10: Order Block en dirección correcta
    with estado_lock:
        obs_actuales = estado_mercado["obs"]
    obs_actuales = invalidar_obs(obs_actuales, micro_price)
    ob_ctx = get_ob_contexto(micro_price, obs_actuales)
    if raw_signal == "COMPRA" and ob_ctx["accion"] == "SHORT": return
    if raw_signal == "VENTA"  and ob_ctx["accion"] == "LONG":  return

    # Calcular niveles
    with estado_lock:
        poc = estado_mercado["vp_poc"]
    atr = calcular_atr(price_history, candle_closes)
    niveles = calcular_niveles(micro_price, raw_signal, bids, asks, obi_actual, atr, poc)
    if niveles is None: return

    # FILTRO 11: R:R mínimo 2.0
    if niveles["reward_pct"] / max(niveles["riesgo_pct"], 0.001) < 2.0:
        return

    last_signal      = raw_signal
    last_signal_side = raw_signal
    last_signal_time = time.time()
    ctx_str = f"OK {ctx_age:.0f}s" if ctx_age < 60 else f"VIEJO {ctx_age:.0f}s"

    print(f"""
─── {raw_signal} ───  {tipo_señal} - {desc_señal}  |  {ctx_str}
   Precio:{micro_price:.2f}  Z:{z_score:+.2f}(th={threshold_dinamico:.2f})  OBI:{obi_actual:+.3f}  OBI_CONFIRM:{obi_confirm}
   RSI fast:{rsi_fast:.0f} slow:{rsi_slow:.0f}  Trend:{trend_5m}  VWAP:{vwap_bias}({dist_vwap:+.2f}%)
   VP:{vp_zona}  OB:{ob_ctx['zona']}  Agg:{aggressor}{"  ⚠ AGG_CONTRA" if agg_contra else ""}
   Entry:{niveles['entry']:.2f}  SL:{niveles['sl']:.2f}  TP1:{niveles['tp1']:.2f}  R:R={niveles['reward_pct']/max(niveles['riesgo_pct'],0.001):.1f}""",
    flush=True)

    registrar_señal(
        raw_signal, niveles["entry"], niveles["tp1"], niveles["sl"],
        signal_id=str(uuid.uuid4()),
    )


def on_error(ws, error):
    print(f"  [WS ERROR] {error}", flush=True)

def on_close(ws, *args):
    print("  Desconectado.", flush=True)

def on_open(ws):
    print("=" * 60)
    print("  Scalping OBI — Binance DEMO  (demo-api.binance.com)")
    print(f"  Symbol:{SYMBOL}  Qty:{QUANTITY}  Z-th:{Z_SCORE_THRESHOLD}  Window:{WINDOW_SIZE}  Cooldown:{COOLDOWN_SECONDS}s")
    print("  ─────────────────────────────────────────────────────")
    print("  COMPRA/VENTA  |  TIPO_A=agresion  TIPO_B=retirada")
    print("  Z=desv OBI  |  OBI_CONFIRM=OBI>0.10  |  Trend=5m")
    print("  VWAP=referencia  |  VP=Volume Profile  |  OB=Order Block")
    print("  Agg=agresor  |  R:R=reward/risk  |  Entry/SL/TP1=niveles")
    print("  ─────────────────────────────────────────────────────")
    mode = "[ORDENES DEMO]" if (API_KEY and API_SECRET) else "[SOLO SEÑAL] — cargá API keys Demo"
    print(f"  {mode}")
    print("=" * 60, flush=True)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scalping OBI — Binance Demo")
    parser.add_argument("--symbol",     default="BTCUSDT",  help="Par (default: BTCUSDT)")
    parser.add_argument("--api-key",    default="",          help="API Key Demo")
    parser.add_argument("--api-secret", default="",          help="API Secret Demo")
    parser.add_argument("--quantity",   type=float, default=0.001, help="Cantidad BTC (default: 0.001)")
    parser.add_argument("--cooldown",   type=int,   default=20,    help="Cooldown seg (default: 20)")
    args = parser.parse_args()

    API_KEY    = (args.api_key    or os.environ.get("BINANCE_DEMO_KEY",    "")).strip()
    API_SECRET = (args.api_secret or os.environ.get("BINANCE_DEMO_SECRET", "")).strip()
    SYMBOL         = args.symbol
    QUANTITY       = args.quantity
    COOLDOWN_SECONDS = args.cooldown

    # ── Carga inicial de contexto ──────────────────────────
    print("Cargando contexto inicial...", end=" ", flush=True)
    vp_inicial    = build_volume_profile(SYMBOL)
    trend_inicial = get_trend_5min(SYMBOL)
    obs_inicial   = detectar_order_blocks(SYMBOL)
    with estado_lock:
        estado_mercado["trend_5m"] = trend_inicial
        if vp_inicial:
            estado_mercado["vp_poc"] = vp_inicial["poc"]
            estado_mercado["vp_val"] = vp_inicial["val"]
            estado_mercado["vp_vah"] = vp_inicial["vah"]
        estado_mercado["obs"] = obs_inicial
        estado_mercado["ts"]  = time.time()
    print("OK")

    threading.Thread(target=actualizar_contexto_loop, args=(SYMBOL, 60),  daemon=True).start()
    threading.Thread(target=actualizar_candles_loop,  args=(SYMBOL, 60),  daemon=True).start()
    threading.Thread(target=ajustar_thresholds_dinamicamente, args=(SYMBOL, 3),  daemon=True).start()

    # ── WebSocket — usa stream de Binance real (mismo feed de precios)
    #    Las ÓRDENES van a demo-api.binance.com
    stream_url = (
        f"wss://stream.binance.com:9443/stream"
        f"?streams={SYMBOL.lower()}@depth20@100ms"
    )
    print(f"Conectando WebSocket: {stream_url}", flush=True)

    ws = websocket.WebSocketApp(
        stream_url,
        on_open=on_open, on_message=on_message,
        on_error=on_error, on_close=on_close,
    )
    ws.run_forever()
