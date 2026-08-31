import yfinance as yf
import pandas as pd
import time

print("=" * 60)
print("OBTENIENDO SECTORES E INDUSTRIAS DE YFINANCE")
print("=" * 60)

# 1. Obtener sectores dinámicamente desde la API
from yfinance import EquityQuery

# valid_values es una propiedad, usar fget para obtener el dict
valid_values = EquityQuery.valid_values.fget(EquityQuery)
sector_names = valid_values.get('sector', []) if 'sector' in valid_values else []
if not sector_names:
    print("✗ No se pudieron obtener sectores desde EquityQuery.valid_values")
    exit()

print(f"\nSectores disponibles (desde API): {len(sector_names)}")
for s in sector_names:
    print(f"  - {s}")

# 2. Convertir nombre de sector a key (kebab-case) para yf.Sector()
#    Ej: "Basic Materials" -> "basic-materials", "Consumer Cyclical" -> "consumer-cyclical"
def name_to_key(name):
    return name.lower().replace(' ', '-').replace('&', '')

sector_map = {}
for name in sector_names:
    sector_map[name_to_key(name)] = name

print(f"\nMapeo sector_key -> sector_name:")
for k, v in sector_map.items():
    print(f"  {k:35s} -> {v}")

# 3. Obtener industrias de cada sector dinámicamente
todas_industrias = []
errores = []

for i, (skey, sname) in enumerate(sector_map.items()):
    print(f"\n[{i+1}/{len(sector_map)}] Sector: {sname} ({skey})")
    try:
        sector = yf.Sector(skey)
        df_ind = sector.industries
        if df_ind is not None and not df_ind.empty:
            df_ind = df_ind.copy()
            df_ind['sector_key'] = skey
            df_ind['sector_name'] = sname
            todas_industrias.append(df_ind)
            print(f"  ✓ {len(df_ind)} industrias:")
            for _, row in df_ind.iterrows():
                print(f"    - {row.get('symbol', 'N/A')} | {row.get('name', 'N/A')}")
        else:
            print(f"  ⚠ Sin industrias")
        time.sleep(0.5)
    except Exception as e:
        errores.append((skey, sname, str(e)))
        print(f"  ✗ Error: {e}")

# 4. Consolidar resultados
if todas_industrias:
    df = pd.concat(todas_industrias, ignore_index=True)
    
    cols = ['sector_key', 'sector_name', 'symbol', 'name', 'market weight']
    extra_cols = [c for c in df.columns if c not in cols]
    df = df[cols + extra_cols]
    
    print("\n" + "=" * 60)
    print(f"RESUMEN: {len(df)} industrias en {len(sector_map)} sectores")
    print("=" * 60)
    
    print("\nIndustrias por sector:")
    for sname in sector_names:
        count = len(df[df['sector_name'] == sname])
        print(f"  {sname}: {count}")
    
    # Guardar CSV
    output_path = r"c:\Users\boosa\Downloads\optimizaciones\coronar bases\APIS\sectores_industrias.csv"
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ Guardado en: {output_path}")
    
    # Guardar TXT legible
    txt_path = r"c:\Users\boosa\Downloads\optimizaciones\coronar bases\APIS\sectores_industrias.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        for sname in sector_names:
            f.write(f"\n{'='*60}\n")
            f.write(f"SECTOR: {sname}\n")
            f.write(f"{'='*60}\n")
            sector_df = df[df['sector_name'] == sname]
            for _, row in sector_df.iterrows():
                f.write(f"  {row['symbol']:45s} | {row['name']}\n")
    print(f"✓ Guardado en: {txt_path}")
else:
    print("\n✗ No se obtuvieron industrias")

if errores:
    print(f"\nErrores ({len(errores)}):")
    for skey, sname, err in errores:
        print(f"  {skey}/{sname}: {err}")
