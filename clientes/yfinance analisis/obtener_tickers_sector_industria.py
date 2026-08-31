import yfinance as yf
import pandas as pd
import time
import json
import sys
from yfinance import EquityQuery

# Configuración
OUTPUT_CSV = r"c:\Users\boosa\Desktop\clientes\yfinance analisis\tickers_por_sector_industria.csv"
MAX_PER_PAGE = 250  # Máximo por página según Yahoo Finance
MAX_PAGES = 10      # Límite de páginas para evitar loops infinitos
EXCHANGE_FILTER = None  # None = todos, 'BUE' = Argentina, 'NMS' = NASDAQ, 'NYQ' = NYSE
AUTO_MODE = True  # Si True, ejecuta opción 3 automáticamente sin prompts

print("=" * 60)
print("OBTENIENDO TICKERS POR SECTOR E INDUSTRIA")
print("=" * 60)

# 1. Seleccionar exchange primero
print(f"\nFiltro de exchange actual: {EXCHANGE_FILTER if EXCHANGE_FILTER else 'TODOS'}")
if not AUTO_MODE:
    print("Valores válidos de exchange (ejemplos):")
    print("  us: NMS (NASDAQ), NYQ (NYSE), ASE (AMEX)")
    print("  ar: BUE (Buenos Aires)")
    print("  br: SAO (São Paulo)")
    print("  ca: TOR (Toronto), VAN (Vancouver)")
    print("  mx: MEX (México)")
    print("  uk: LSE (London)")
    print("  jp: JPX (Tokyo)")

    cambiar_exchange = input("\n¿Cambiar filtro de exchange? (s/n): ").strip().lower()
    while cambiar_exchange not in ['s', 'n', '']:
        print("Respuesta inválida. Ingresa 's' para sí, 'n' para no, o Enter para no.")
        cambiar_exchange = input("¿Cambiar filtro de exchange? (s/n): ").strip().lower()

    if cambiar_exchange == 's':
        exchange_input = input("Ingresa código de exchange (ej: BUE, NMS, NYQ, o Enter para todos): ").strip().upper()
        EXCHANGE_FILTER = exchange_input if exchange_input else None

print(f"\nExchange seleccionado: {EXCHANGE_FILTER if EXCHANGE_FILTER else 'TODOS'}")

# 2. Obtener sectores e industrias directamente de la API
def obtener_sectores_industrias():
    """Obtiene sectores e industrias desde la API de yfinance."""
    valid_values = EquityQuery.valid_values.fget(EquityQuery)
    sector_names = valid_values.get('sector', []) if 'sector' in valid_values else []
    
    if not sector_names:
        print("✗ No se pudieron obtener sectores desde la API")
        return None, None
    
    print(f"\n✓ {len(sector_names)} sectores obtenidos desde la API")
    
    # Convertir nombre de sector a key (kebab-case)
    def to_kebab_case(name):
        return name.lower().replace(' ', '-')
    
    sector_map = {to_kebab_case(name): name for name in sector_names}
    
    # Obtener industrias de cada sector
    todas_industrias = []
    for skey, sname in sector_map.items():
        try:
            sector = yf.Sector(skey)
            df_ind = sector.industries
            if df_ind is not None and not df_ind.empty:
                df_ind = df_ind.copy()
                df_ind['sector_key'] = skey
                df_ind['sector_name'] = sname
                todas_industrias.append(df_ind)
            time.sleep(0.3)
        except Exception as e:
            print(f"  ⚠ Error obteniendo industrias de {sname}: {e}")
    
    if todas_industrias:
        df_industrias = pd.concat(todas_industrias, ignore_index=True)
        print(f"✓ {len(df_industrias)} industrias obtenidas")
        return sector_names, df_industrias
    
    return sector_names, None

sector_names, df_industrias = obtener_sectores_industrias()
if sector_names is None:
    exit()
sector_names = list(sector_names)  # Convertir a lista para permitir indexación

# 3. Función para obtener tickers con paginación
def get_tickers_by_sector(sector_name, exchange=None, max_pages=MAX_PAGES):
    """Obtiene todos los tickers de un sector usando paginación."""
    all_tickers = []
    offset = 0
    page = 0
    
    while page < max_pages:
        try:
            if exchange:
                q = EquityQuery('and', [
                    EquityQuery('eq', ['sector', sector_name]),
                    EquityQuery('eq', ['exchange', exchange])
                ])
            else:
                q = EquityQuery('eq', ['sector', sector_name])
            
            r = yf.screen(q, size=MAX_PER_PAGE, offset=offset)
            
            print(f"    DEBUG: respuesta tipo: {type(r)}")
            if r is not None:
                if isinstance(r, pd.DataFrame):
                    print(f"    DEBUG: DataFrame columns: {r.columns.tolist()}")
                    print(f"    DEBUG: DataFrame shape: {r.shape}")
                elif isinstance(r, dict):
                    print(f"    DEBUG: Dict keys: {r.keys()}")
            
            if r is None or (isinstance(r, (pd.DataFrame, dict)) and len(r) == 0):
                print(f"    DEBUG: respuesta vacía o None, break")
                break
            
            # Convertir a DataFrame si es dict
            if isinstance(r, dict):
                r = pd.DataFrame([r])
            elif not isinstance(r, pd.DataFrame):
                break
            
            # Si existe columna 'quotes' con JSON string, expandirla
            if 'quotes' in r.columns:
                expanded_quotes = []
                for _, row in r.iterrows():
                    try:
                        quotes_data = json.loads(row['quotes'])
                        if isinstance(quotes_data, list):
                            for quote in quotes_data:
                                quote['sector'] = sector_name
                                quote['exchange_filter'] = exchange if exchange else 'ALL'
                                expanded_quotes.append(quote)
                    except:
                        pass
                if expanded_quotes:
                    r = pd.DataFrame(expanded_quotes)
                else:
                    r = pd.DataFrame()
            else:
                r['sector'] = sector_name
                if exchange:
                    r['exchange_filter'] = exchange
                else:
                    r['exchange_filter'] = 'ALL'
            
            all_tickers.append(r)
            print(f"    Página {page+1}: {len(r)} tickers (offset={offset})")
            
            if len(r) < MAX_PER_PAGE:
                break
            
            offset += MAX_PER_PAGE
            page += 1
            time.sleep(0.5)  # evitar rate limit
            
        except Exception as e:
            print(f"    ✗ Error en página {page+1}: {e}")
            break
    
    if all_tickers:
        return pd.concat(all_tickers, ignore_index=True)
    return None

def get_tickers_by_industry(industry_name, exchange=None, max_pages=MAX_PAGES):
    """Obtiene todos los tickers de una industria usando paginación."""
    all_tickers = []
    offset = 0
    page = 0
    
    while page < max_pages:
        try:
            if exchange:
                q = EquityQuery('and', [
                    EquityQuery('eq', ['industry', industry_name]),
                    EquityQuery('eq', ['exchange', exchange])
                ])
            else:
                q = EquityQuery('eq', ['industry', industry_name])
            
            r = yf.screen(q, size=MAX_PER_PAGE, offset=offset)
            
            if r is None or (isinstance(r, (pd.DataFrame, dict)) and len(r) == 0):
                break
            
            # Convertir a DataFrame si es dict
            if isinstance(r, dict):
                r = pd.DataFrame([r])
            elif not isinstance(r, pd.DataFrame):
                break
            
            # Si existe columna 'quotes' con JSON string, expandirla
            if 'quotes' in r.columns:
                expanded_quotes = []
                for _, row in r.iterrows():
                    try:
                        quotes_data = json.loads(row['quotes'])
                        if isinstance(quotes_data, list):
                            for quote in quotes_data:
                                quote['industry'] = industry_name
                                quote['exchange_filter'] = exchange if exchange else 'ALL'
                                expanded_quotes.append(quote)
                    except:
                        pass
                if expanded_quotes:
                    r = pd.DataFrame(expanded_quotes)
                else:
                    r = pd.DataFrame()
            else:
                r['industry'] = industry_name
                if exchange:
                    r['exchange_filter'] = exchange
                else:
                    r['exchange_filter'] = 'ALL'
            
            all_tickers.append(r)
            print(f"    Página {page+1}: {len(r)} tickers (offset={offset})")
            
            if len(r) < MAX_PER_PAGE:
                break
            
            offset += MAX_PER_PAGE
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"    ✗ Error en página {page+1}: {e}")
            break
    
    if all_tickers:
        return pd.concat(all_tickers, ignore_index=True)
    return None

# 3. Menú de selección
if AUTO_MODE:
    opcion = '3'
    print(f"\nModo automático: obteniendo tickers de TODOS los sectores")
else:
    print("\nOpciones:")
    print("  1. Obtener tickers por SECTOR")
    print("  2. Obtener tickers por INDUSTRIA")
    print("  3. Obtener tickers de TODOS los sectores")
    print("  4. Obtener tickers de TODAS las industrias")

    # Check for command-line arguments
    if len(sys.argv) > 1:
        opcion = sys.argv[1]
        if len(sys.argv) > 2:
            EXCHANGE_FILTER = sys.argv[2] if sys.argv[2] != 'ALL' else None
        print(f"\nModo no-interactivo: opción={opcion}, exchange={EXCHANGE_FILTER or 'TODOS'}")
    else:
        opcion = input("\nSelecciona opción (1-4): ").strip()

        # Mostrar filtro de exchange y valores válidos
        print(f"\nFiltro de exchange actual: {EXCHANGE_FILTER if EXCHANGE_FILTER else 'TODOS'}")
        print("Valores válidos de exchange (ejemplos):")
        print("  us: NMS (NASDAQ), NYQ (NYSE), ASE (AMEX)")
        print("  ar: BUE (Buenos Aires)")
        print("  br: SAO (São Paulo)")
        print("  ca: TOR (Toronto), VAN (Vancouver)")
        print("  mx: MEX (México)")
        print("  uk: LSE (London)")
        print("  jp: JPX (Tokyo)")

        cambiar_exchange = input("\n¿Cambiar filtro de exchange? (s/n): ").strip().lower()
        while cambiar_exchange not in ['s', 'n', '']:
            print("Respuesta inválida. Ingresa 's' para sí, 'n' para no, o Enter para no.")
            cambiar_exchange = input("¿Cambiar filtro de exchange? (s/n): ").strip().lower()

        if cambiar_exchange == 's':
            exchange_input = input("Ingresa código de exchange (ej: BUE, NMS, NYQ, o Enter para todos): ").strip().upper()
            EXCHANGE_FILTER = exchange_input if exchange_input else None

all_results = []
errores = []

if opcion == '1':
    # Por sector
    print(f"\nSectores disponibles ({len(sector_names)}):")
    for i, s in enumerate(sector_names, 1):
        print(f"  {i}. {s}")
    
    if len(sys.argv) > 3:
        idx = int(sys.argv[3]) - 1
    else:
        idx = int(input("\nSelecciona número de sector: ")) - 1
    sector = sector_names[idx]
    
    print(f"\nObteniendo tickers del sector: {sector}")
    print(f"Exchange filter: {EXCHANGE_FILTER if EXCHANGE_FILTER else 'TODOS'}")
    
    df_tickers = get_tickers_by_sector(sector, EXCHANGE_FILTER)
    if df_tickers is not None:
        all_results.append(df_tickers)
        print(f"✓ Total: {len(df_tickers)} tickers")
    else:
        print("✗ No se obtuvieron tickers")

elif opcion == '2':
    # Por industria
    if df_industrias is None:
        print("✗ No hay datos de industrias disponibles")
        exit()
    print(f"\nIndustrias disponibles ({len(df_industrias)}):")
    for i, row in df_industrias.iterrows():
        print(f"  {i+1}. {row['name']} ({row['sector_name']})")
    
    if len(sys.argv) > 3:
        idx = int(sys.argv[3]) - 1
    else:
        idx = int(input("\nSelecciona número de industria: ")) - 1
    industria = df_industrias.iloc[idx]['name']
    
    print(f"\nObteniendo tickers de la industria: {industria}")
    print(f"Exchange filter: {EXCHANGE_FILTER if EXCHANGE_FILTER else 'TODOS'}")
    
    df_tickers = get_tickers_by_industry(industria, EXCHANGE_FILTER)
    if df_tickers is not None:
        all_results.append(df_tickers)
        print(f"✓ Total: {len(df_tickers)} tickers")
    else:
        print("✗ No se obtuvieron tickers")

elif opcion == '3':
    # Todos los sectores
    print(f"\nProcesando {len(sector_names)} sectores...")
    
    for i, sector in enumerate(sector_names, 1):
        print(f"\n[{i}/{len(sector_names)}] Sector: {sector}")
        df_tickers = get_tickers_by_sector(sector, EXCHANGE_FILTER)
        if df_tickers is not None:
            all_results.append(df_tickers)
        else:
            errores.append(sector)
        time.sleep(1)

elif opcion == '4':
    # Todas las industrias
    if df_industrias is None:
        print("✗ No hay datos de industrias disponibles")
        exit()
    print(f"\nProcesando {len(df_industrias)} industrias...")
    
    for i, row in df_industrias.iterrows():
        industria = row['name']
        sector = row['sector_name']
        print(f"\n[{i+1}/{len(df_industrias)}] {industria} ({sector})")
        df_tickers = get_tickers_by_industry(industria, EXCHANGE_FILTER)
        if df_tickers is not None:
            all_results.append(df_tickers)
        else:
            errores.append(industria)
        time.sleep(1)

else:
    print("✗ Opción inválida")
    exit()

# 4. Consolidar y guardar
if all_results:
    df_final = pd.concat(all_results, ignore_index=True)
    
    # Eliminar duplicados por ticker
    if 'symbol' in df_final.columns:
        antes = len(df_final)
        df_final = df_final.drop_duplicates(subset=['symbol'], keep='first')
        print(f"\nEliminados {antes - len(df_final)} duplicados por ticker")
    
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(df_final)} tickers únicos")
    print(f"{'='*60}")
    
    # Seleccionar columnas importantes si existen
    cols_importantes = ['symbol', 'shortName', 'longName', 'exchange', 'currency', 
                        'regularMarketPrice', 'marketCap', 'sector', 'industry', 'exchange_filter']
    cols_disponibles = [c for c in cols_importantes if c in df_final.columns]
    if cols_disponibles:
        df_final = df_final[cols_disponibles]
    
    df_final.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"✓ Guardado en: {OUTPUT_CSV}")
    
    # Resumen por sector si existe la columna
    if 'sector' in df_final.columns:
        print("\nTickers por sector:")
        print(df_final['sector'].value_counts())
    
    # Resumen por exchange si existe la columna
    if 'exchange' in df_final.columns:
        print("\nTickers por exchange:")
        print(df_final['exchange'].value_counts())

if errores:
    print(f"\nErrores ({len(errores)}):")
    for e in errores:
        print(f"  - {e}")
