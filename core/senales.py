# -*- coding: utf-8 -*-
"""core.senales: direccion, regla de oro (Paso 4) y reglas de decision (Paso 5).

Extraido de intermarket_parte4_6_7.py (direccion/apply_rules) y
generar_senales.py (direc) -- unificados.
"""
UMBRAL_PENDIENTE = 2.0  # % de variacion de la ventana para considerar tendencia


def direc(st, umbral=UMBRAL_PENDIENTE):
    """Direccion de una ventana de stats: 1 alcista, -1 bajista, 0 plano."""
    if st is None:
        return 0
    if abs(st["slope"]) < umbral:
        return 0
    return 1 if st["slope"] > 0 else -1


def regla_oro(st, wins=(50, 120, 365)):
    """Paso 4: la senal es fuerte si las 3 ventanas coinciden en direccion.

    Returns: 'ALCISTA CONFIRMADA', 'BAJISTA CONFIRMADA',
             'CAMBIO DE REGIMEN' (50=120 pero 365 distinto), 'NEUTRO'.
    """
    d50 = direc(st.get(wins[0]))
    d120 = direc(st.get(wins[1]))
    d365 = direc(st.get(wins[2]))
    if d50 == d120 == d365 == 1:
        return "ALCISTA CONFIRMADA"
    if d50 == d120 == d365 == -1:
        return "BAJISTA CONFIRMADA"
    if d50 and d50 == d120 and d120 != d365:
        return "CAMBIO DE REGIMEN"
    return "NEUTRO"


def accion(regla, st):
    """Paso 5: decision concreta a partir de la regla de oro y z/pct de 120."""
    z120 = st.get(120, {}).get("z", 0.0)
    p120 = st.get(120, {}).get("pct", 50.0)
    if regla == "ALCISTA CONFIRMADA":
        return "MANTENER/ACUMULAR"
    if regla == "BAJISTA CONFIRMADA":
        return "ROTAR/NO COMPRAR"
    if z120 < -1.5 and p120 < 10:
        return "POSIBLE MEAN-REVERSION (verificar macro)"
    if z120 > 1.5 and p120 > 90:
        return "SOBRECOMPRADO: NO PERSEGUIR"
    return "VIGILAR"


def apply_rules(st, wins=(50, 120, 365)):
    """Paso 5 descriptivo: acumula todas las reglas aplicables en un string."""
    if not st:
        return "sin datos"
    msg = []
    if len(st) < 3:
        return "no hay 3 ventanas"
    d50 = direc(st.get(wins[0]))
    d120 = direc(st.get(wins[1]))
    d365 = direc(st.get(wins[2]))
    if d50 == d120 == d365 == 1:
        msg.append("REGLA DE ORO: 50+120+365 al alza -> senal CONFIRMADA (acumular/mantener)")
    elif d50 == d120 == d365 == -1:
        msg.append("REGLA DE ORO: 50+120+365 a la baja -> senal CONFIRMADA (rotar/no comprar)")
    if st.get(120, {}).get("high"):
        msg.append("Maximo relativo en 120 -> mantener/aumentar")
    if st.get(120, {}).get("low"):
        msg.append("Minimo relativo en 120 -> posible reversal")
    z = st.get(wins[1], {}).get("z", 0.0)
    pct = st.get(wins[1], {}).get("pct", 50.0)
    if z < -1.5 and pct < 10:
        msg.append("Z=%.2f Pct=%.0f%% -> posible entry mean-reversion" % (z, pct))
    if z > 1.5 and pct > 90:
        msg.append("Z=%.2f Pct=%.0f%% -> sobrecomprado, no perseguir" % (z, pct))
    return " | ".join(msg) if msg else "neutro"