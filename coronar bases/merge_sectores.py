import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Mapeo español → inglés (mismo que normalizarSector en fundamental-af.functions.ts)
ES_TO_EN = {
    "Tecnología": "Technology",
    "Servicios de comunicación": "Communication Services",
    "Consumo cíclico": "Consumer Cyclical",
    "Defensiva del Consumidor": "Consumer Defensive",
    "Cuidado de la salud": "Healthcare",
    "Servicios financieros": "Financial Services",
    "Energía": "Energy",
    "Materiales Básicos": "Basic Materials",
    "Acciones industriales": "Industrials",
    "Utilidades": "Utilities",
    "Bienes raíces": "Real Estate",
    "Fondos y ETFs": "Fondos y ETFs",
}

script_dir = os.path.dirname(os.path.abspath(__file__))

# Cargar el nuevo JSON de BCBA
bcba_path = os.path.join(script_dir, "TICKERS_SECTORES_INDUSTRIA.json")
with open(bcba_path, "r", encoding="utf-8") as f:
    bcba = json.load(f)

# Cargar el existente sectores.json
ruta = os.path.join(script_dir, "clarity-dashboard-main6", "src", "lib", "sectores.json")
with open(ruta, "r", encoding="utf-8") as f:
    existente = json.load(f)

# Convertir sectores BCBA al inglés y agregar al existente
total_agregados = 0
for sector_es, industrias in bcba.items():
    sector_en = ES_TO_EN.get(sector_es, sector_es)
    if sector_en not in existente:
        existente[sector_en] = {}
    for industria_es, tickers in industrias.items():
        # Buscar si ya existe una industria con nombre similar (case-insensitive)
        industria_existente = None
        for existing_ind in existente[sector_en]:
            if existing_ind.lower() == industria_es.lower():
                industria_existente = existing_ind
                break
        if not industria_existente:
            # Buscar match parcial: si la industria española contiene alguna palabra clave
            for existing_ind in existente[sector_en]:
                palabras_es = set(industria_es.lower().split())
                palabras_en = set(existing_ind.lower().split())
                if palabras_es & palabras_en:
                    industria_existente = existing_ind
                    break
        target_ind = industria_existente or industria_es
        if target_ind not in existente[sector_en]:
            existente[sector_en][target_ind] = []
        # Agregar tickers (evitar duplicados)
        existentes = {t["ticker"] for t in existente[sector_en][target_ind]}
        for t in tickers:
            if t["ticker"] not in existentes:
                existente[sector_en][target_ind].append(t)
                total_agregados += 1

# Guardar el resultado
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(existente, f, indent=2, ensure_ascii=False)

print(f"OK - {total_agregados} tickers de BCBA agregados")
print(f"Sectores en existente: {list(existente.keys())}")
print(f"Sectores en BCBA: {list(bcba.keys())}")
for s in bcba:
    en = ES_TO_EN.get(s, s)
    print(f"  {s} -> {en} {'✓' if en in existente else '✗'}")
