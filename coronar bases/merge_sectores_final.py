import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

script_dir = os.path.dirname(os.path.abspath(__file__))

# Cargar existente sectores.json (USA)
ruta_usa = os.path.join(script_dir, "clarity-dashboard-main6", "src", "lib", "sectores.json")
with open(ruta_usa, "r", encoding="utf-8") as f:
    existente = json.load(f)

# Cargar BCBA
ruta_bcba = os.path.join(script_dir, "clarity-dashboard-main6", "src", "lib", "sectores-bcba.json")
with open(ruta_bcba, "r", encoding="utf-8") as f:
    bcba = json.load(f)

# Agregar BCBA bajo clave "BCBA" en el mismo archivo
existente["BCBA"] = bcba

# Guardar
with open(ruta_usa, "w", encoding="utf-8") as f:
    json.dump(existente, f, indent=2, ensure_ascii=False)

total_bcba = sum(len(v) for s in bcba.values() for v in s.values())
print(f"OK - {total_bcba} tickers BCBA agregados bajo clave 'BCBA' en sectores.json")
