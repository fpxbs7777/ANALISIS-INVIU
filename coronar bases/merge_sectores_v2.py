import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))
ruta = os.path.join(script_dir, "clarity-dashboard-main6", "src", "lib", "sectores.json")

with open(ruta, "r", encoding="utf-8") as f:
    data = json.load(f)

# Cargar BCBA
ruta_bcba = os.path.join(script_dir, "clarity-dashboard-main6", "src", "lib", "sectores-bcba.json")
with open(ruta_bcba, "r", encoding="utf-8") as f:
    bcba = json.load(f)

# Quitar clave "BCBA" si existe del merge anterior
if "BCBA" in data:
    del data["BCBA"]

# Agregar sectores BCBA directamente al mismo nivel que USA
# Asi: data["Servicios financieros"] = { "Bancos - Regionales": [...] }
for sector, industrias in bcba.items():
    if sector in data:
        print(f"ATENCION: Sector '{sector}' ya existe. Fusionando industrias...")
        for industria, tickers in industrias.items():
            if industria in data[sector]:
                existentes = {t["ticker"] for t in data[sector][industria]}
                for t in tickers:
                    if t["ticker"] not in existentes:
                        data[sector][industria].append(t)
            else:
                data[sector][industria] = tickers
    else:
        data[sector] = industrias

with open(ruta, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

total_bcba = sum(len(v) for s in bcba.values() for v in s.values())
print(f"OK - {total_bcba} tickers BCBA agregados directamente (sin wrapper BCBA)")
