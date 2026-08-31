"""
Script unificado para descargar y exportar series históricas de todos los activos y factores.

Este script:
1. Descarga las series de tiempo de:
   - Todos los tickers por sector
   - Todos los ETFs sectoriales
   - ETFs internacionales
   - ETFs de factores
   - Todos los factores y benchmarks definidos
2. Guarda en caché (Parquet/CSV) para descargas incrementales
3. Exporta directamente a JSON con la estructura requerida por el HTML

Incluye sistema de caché automático para evitar descargas innecesarias.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# Agregar el directorio del script al path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"❌ Error: Faltan dependencias requeridas: {e}")
    print("   Instala las dependencias con: pip install yfinance pandas numpy")
    sys.exit(1)

# ============================================================================
# CONFIGURACIÓN DE TICKERS (INDEPENDIENTE - NO REQUIERE config_tickers_factores.py)
# ============================================================================

# TECNOLOGÍA (Technology)
TECH_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'META', 'NVDA', 'AVGO', 'ORCL', 'ADBE', 'CSCO',
    'CRM', 'ACN', 'TXN', 'IBM', 'QCOM', 'INTC', 'AMD', 'NOW', 'INTU', 'AMAT',
    'UBER', 'SHOP', 'NET', 'SNOW', 'CRWD', 'PANW', 'FTNT', 'ZS', 'OKTA', 'TEAM',
    'DDOG', 'MDB', 'PLTR', 'U', 'TWLO', 'DOCU', 'RBLX', 'SQ', 'PYPL', 'COIN'
]

# SERVICIOS FINANCIEROS (Financial Services)
FINANCIAL_TICKERS = [
    'JPM', 'BAC', 'WFC', 'GS', 'MS', 'SCHW', 'BLK', 'C', 'AXP', 'V',
    'MA', 'PYPL', 'SPGI', 'MCO', 'ICE', 'CME', 'BX', 'KKR', 'APO', 'ARES',
    'TROW', 'AMP', 'BEN', 'IVZ', 'NTRS', 'STT', 'BK', 'DFS', 'SYF', 'COF'
]

# SALUD (Healthcare)
HEALTHCARE_TICKERS = [
    'JNJ', 'UNH', 'PFE', 'ABT', 'TMO', 'LLY', 'MRK', 'DHR', 'ABBV', 'AMGN',
    'GILD', 'BMY', 'CVS', 'ELV', 'CI', 'HUM', 'VRTX', 'REGN', 'BIIB', 'ISRG',
    'SYK', 'BDX', 'ZTS', 'EW', 'IDXX', 'DXCM', 'MRNA', 'BNTX', 'VEEV', 'HCA'
]

# CONSUMO DISCRECIONAL (Consumer Cyclical)
CONSUMER_CYCLICAL_TICKERS = [
    'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'TGT', 'BKNG',
    'MAR', 'YUM', 'CMG', 'ORLY', 'AZO', 'F', 'GM', 'RIVN', 'LCID', 'NIO',
    'DPZ', 'DRI', 'LVS', 'WYNN', 'MGM', 'RCL', 'NCLH', 'CCL', 'EXPE', 'ABNB'
]

# SERVICIOS DE COMUNICACIÓN (Communication Services)
COMMUNICATION_TICKERS = [
    'GOOGL', 'META', 'NFLX', 'DIS', 'T', 'VZ', 'CMCSA', 'CHTR', 'TMUS', 'EA',
    'ATVI', 'TTWO', 'SPOT', 'LYV', 'LGF-A', 'NWSA', 'FOX', 'FOXA', 'IPG', 'OMC'
]

# CONSUMO BÁSICO (Consumer Defensive)
CONSUMER_DEFENSIVE_TICKERS = [
    'PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'KMB', 'MO', 'PM', 'MDLZ',
    'KHC', 'SYY', 'KR', 'TGT', 'DG', 'DLTR', 'CLX', 'HSY', 'CAG', 'GIS',
    'K', 'MKC', 'SJM', 'TAP', 'STZ', 'BF-B', 'MNST', 'EL', 'UL', 'NSRGY'
]

# ENERGÍA (Energy)
ENERGY_TICKERS = [
    'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PSX', 'MPC', 'VLO', 'OXY', 'PXD',
    'HES', 'DVN', 'FANG', 'MRO', 'APA', 'BKR', 'HAL', 'WMB', 'OKE', 'LNG',
    'KMI', 'TRP', 'ENB', 'EQT', 'CTRA', 'RRC', 'OVV', 'MTDR', 'CHK', 'EQNR'
]

# INDUSTRIALES (Industrials)
INDUSTRIAL_TICKERS = [
    'RTX', 'HON', 'UPS', 'CAT', 'GE', 'BA', 'LMT', 'NOC', 'GD', 'DE',
    'EMR', 'ITW', 'WM', 'FDX', 'CSX', 'UNP', 'NSC', 'CP', 'CNI', 'MMM',
    'ETN', 'CARR', 'IR', 'DOV', 'FAST', 'GWW', 'NDAQ', 'CMI', 'PH', 'TT'
]

# MATERIALES BÁSICOS (Basic Materials)
MATERIALS_TICKERS = [
    'LIN', 'APD', 'ECL', 'SHW', 'FCX', 'NEM', 'DD', 'PPG', 'ALB', 'VMC',
    'MLM', 'NUE', 'STLD', 'CF', 'MOS', 'FMC', 'IFF', 'AVY', 'BALL', 'PKG',
    'WRK', 'IP', 'WLK', 'CE', 'EMN', 'LYB', 'DOW', 'CTVA', 'NTR', 'SMG'
]

# BIENES RAÍCES (Real Estate)
REAL_ESTATE_TICKERS = [
    'AMT', 'PLD', 'EQIX', 'PSA', 'CCI', 'SBAC', 'DLR', 'WELL', 'AVB', 'EQR',
    'O', 'SPG', 'VTR', 'EXR', 'MAA', 'UDR', 'ESS', 'ARE', 'BXP',
    'KIM', 'REG', 'FRT', 'SLG', 'HIW', 'CPT', 'AIV'
]

# SERVICIOS PÚBLICOS (Utilities)
UTILITIES_TICKERS = [
    'NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE', 'EXC', 'XEL', 'WEC', 'PEG',
    'ED', 'ES', 'EIX', 'FE', 'AES', 'AWK', 'CNP', 'LNT', 'DTE', 'CMS',
    'ATO', 'NRG', 'PPL', 'WTRG', 'NI', 'SWX', 'OGS', 'ALE', 'OTTR', 'MGEE'
]

# LISTA MAESTRA DE TICKERS (~1000 tickers)
BIG_TICKERS_LIST = [
    # (1) Grandes tecnológicos y FAANG+ plus semis
    'AAPL','MSFT','GOOGL','GOOG','AMZN','META','NVDA','TSLA','INTC','ADBE',
    'CSCO','ORCL','CRM','IBM','AMD','QCOM','AVGO','TXN','INTU','NOW',
    'ADP','SNOW','PANW','CRWD','OKTA','FTNT','NET','SPLK','ZS','MDB',
    'DDOG','ROKU','SPOT','TWTR','SNAP','UBER','LYFT','SQ','PYPL','COIN',
    # (2) Grandes financieras y bancos
    'JPM','BAC','WFC','C','GS','MS','BK','USB','PNC','TFC',
    'BLK','SCHW','AXP','MA','V','PYPL','SPGI','MCO','ICE','CME',
    'GSX','KKR','APO','BX','BKNG','ALLY','COF','DFS','SYF','NTRS',
    # (3) Salud y farmacéuticas
    'JNJ','PFE','MRK','ABBV','LLY','BMY','UNH','DHR','AMGN','GILD',
    'REGN','VRTX','ISRG','BIIB','MDT','SYK','BDX','ZBH','IDXX','HCA',
    'CVS','CNC','CI','HUM','ELV','SNY','NVO','BNTX','MRNA','VEEV',
    # (4) Consumo discrecional y retail
    'AMZN','HD','LOW','MCD','SBUX','NKE','LULU','SFM','WMT','COST',
    'TGT','TJX','ROST','BBY','KMX','DG','DLTR','TSCO','YUM','MOMO',
    'BKNG','EXPE','ABNB','LYV','MAR','CMG','ORLY','AZO','F','GM',
    # (5) Energía y materiales
    'XOM','CVX','COP','BP','TOT','PBR','PBR.A','OXY','EOG','CHK',
    'SLB','HAL','BKR','APA','MPC','PSX','VLO','PXD','HES','DVN',
    'FCX','NUE','DD','LIN','APD','SHW','ECL','PPG','ALB','MLM',
    # (6) Industrials y transporte
    'CAT','DE','GE','BA','LMT','NOC','RTX','HON','UTX','GD',
    'UPS','FDX','CSX','UNP','NSC','CP','CNI','EMR','ITW','MMM',
    'ETN','CMI','PH','CARR','IR','DOV','FAST','GWW','KSU','KEX',
    # (7) Utilities y real estate
    'NEE','DUK','SO','D','AEP','EXC','SRE','XEL','WEC','PEG',
    'ED','ES','EIX','NRG','PPL','WTRG','AWK','ATO','AES','OGS',
    'AMT','PLD','EQIX','PSA','CCI','SPG','O','VTR','EQR','DLR',
    # (8) ETFs amplios, sectoriales y factores (US)
    'SPY','IVV','VOO','QQQ','IWM','DIA','VTI','VEA','VWO','EEM',
    'IWF','IVW','IVE','IWD','IWS','IWN','XLF','XLY','XLK','XLV',
    'XLE','XLC','XLP','XLI','XLB','XLRE','XLU','XBI','XHB','XLV',
    'GLD','SLV','TLT','IEF','LQD','HYG','SHV','SHY','BND','BNDX',
    'MTUM','QUAL','VLUE','SIZE','USMV','IUSG','IUSV','SPYG','SPYV','SPYD',
    # (9) ETFs internacionales y regionales
    'EFA','EEM','EWZ','EWT','EWG','EWJ','EWC','EWH','EWL','EWA',
    'FXI','RSX','EWQ','EWP','EWI','EWD','EWO','IEMG','VNQ','REM',
    # (10) Commodities y alternativas
    'DBC','DBA','USO','UNG','DBB','PDBC','PPLT','PALL','SLV','GLTR',
    # (11) Dividend / Income / REITs / Preferreds
    'VYM','SCHD','DVY','SDY','NOBL','SCHR','SCHV','SPYD','FTEC','FVD',
    # (12) Small & mid caps (representative sample)
    'SMH','VO','VB','VBK','IWM','MDY','MDYG','MDYV','IJR','IWO',
    # (13) Mercado argentino - BYMA (símbolos comunes con y sin sufijo)
    'YPF.BA','PAMP.BA','GGAL.BA','BMA.BA','BBAR.BA','CECO2.BA','EDN.BA','SUPV.BA','TECO2.BA','PBR.A',
    'MIRG.BA','CVH.BA','TGSU2.BA','YPFD','CECO3.BA','YCA.BA','TRAN.BA','ALUA.BA','PGR.BA','CRES.BA',
    'MELI','BYMA','MERV','BOLD.BA','VALO.BA','AGRO.BA','BIND.BA','BHIP.BA','BRIO.BA','CAAA.BA',
    'CAPX.BA','CECO.BA','CRES.BA','CTIO.BA','CVH.BA','DGCU2.BA','DOCA.BA','EDN.BA','ERAR.BA','FIDE.BA',
    'FERR.BA','GCLA.BA','GLOB.BA','GAMI.BA','GGAL','GARO.BA','HRGR.BA','INTR.BA','IRCP.BA','LOMA.BA',
    'MELI.BA','METR.BA','MIRG','MOLI.BA','PAMP','PESA.BA','PGR','PSUR.BA','RICH.BA','SUPV',
    # Panel líder en pesos
    'ALUA.BA','BBAR.BA','BMA.BA','BYMA.BA','CEPU.BA','COME.BA','CRES.BA','EDN.BA','GGAL.BA','LOMA.BA',
    'METR.BA','PAMP.BA','SUPV.BA','TECO2.BA','TGNO4.BA','TGSU2.BA','TRAN.BA','TXAR.BA','VALO.BA','YPFD.BA',
    # Panel general en pesos
    'FERR.BA','BOLT.BA','CARC.BA','ROSE.BA','HSAT.BA','IRSA.BA','LONG.BA','GCDI.BA','CGPA2.BA','CAPX.BA',
    'HAVA.BA','MIRG.BA','BPAT.BA','GRIM.BA','DGCU2.BA','IEB.BA','RIGO.BA','CVH.BA','RICH.BA','GBAN.BA',
    'GCLA.BA','OEST.BA','DOME.BA','IRS2W.BA','GARO.BA','CRE3W.BA','DGCE.BA','INTR.BA','REGE.BA','POLL.BA',
    'YPFDB.BA','BMA.B.BA','PAMPB.BA','RAGH.BA','GGALB.BA',
    # Dólar cable (sufijo D)
    'ALUAD.BA','BBARD.BA','BMA.D.BA','BYMAD.BA','CEPUD.BA','COMED.BA','CRESD.BA','ECOGD.BA','EDND.BA','GGALD.BA',
    'IRSAD.BA','LOMAD.BA','METRD.BA','PAMPD.BA','SUPVD.BA','TECOD.BA','TGN4D.BA','TGSUD.BA','TRAND.BA','TXARD.BA',
    'VALOD.BA','YPFDD.BA',
    # Panel general en dólar
    'PAMPC.BA','SUPVC.BA','GGALC.BA','YPFDC.BA','A3D.BA','ALUAC.BA','BHIPD.BA','BYMAC.BA','VALOC.BA','TGSUC.BA',
    'BMA.C.BA','EDNC.BA','METRC.BA','CRESC.BA','CVHD.BA','MOLID.BA','GGADB.BA','CTICB.BA','MORID.BA',
    # (14) Más tickers US mid & small - expansión
    'ABNB','ACN','ADSK','AEP','AES','AFL','AGN','AIG','AIZ','AJG',
    'AKAM','ALB','ALK','ALL','ALLE','ALXN','AMAT','AMCR','AMP','AMG',
    'AMH','AMKR','AMPH','AMT','AMZN','ANET','ANSS','ANTM','AON','AOS',
    'APA','APD','APH','APTV','ARE','ARNC','ATO','ATR','ATVI','AVB',
    'AVGO','AVY','AWK','AXP','AZO','BA','BAC','BAX','BBY','BDX',
    'BEN','BF-B','BIIB','BIO','BK','BKR','BLK','BLL','BMY','BND',
    'BRK-B','BSX','BTI','BWA','BXP','CAG','CAH','CARR','CAT','CB',
    'CBOE','CBRE','CBS','CCI','CCL','CDW','CE','CELG','CF','CFG',
    'CHD','CHRW','CHTR','CI','CINF','CL','CLX','CMA','CMCSA','CME',
    'CMG','CNC','CNP','COF','COG','COO','COP','COST','COTY','CPB',
    'CPRT','CRM','CSCO','CSX','CTAS','CTL','CTSH','CTVA','CTXS','CUB',
    # (15) Continuación lista US
    'CVS','CVX','CXO','CYH','D','DAL','DD','DECK','DFS','DGX',
    'DHI','DIS','DAL','DLR','DLTR','DNB','DOCU','DOV','DOW','DPZ',
    'DRI','DTE','DUK','DVA','DVN','DXC','EA','EBAY','ECL','ED',
    'EFX','EIX','EL','EMN','EMR','EOG','EQIX','EQNR','EQR','ES',
    'ESS','ETN','ETR','EVRG','EW','EWBC','EXC','EXPD','EXR','F',
    'FANG','FAST','FB','FBHS','FCX','FDX','FE','FFIV','FIS','FISV',
    'FITB','FIT','FLIR','FLS','FL','FMC','FOX','FOXA','FRT','FSLR',
    'FTNT','FTV','GD','GDDY','GE','GILD','GIS','GL','GLW','GM',
    'GME','GNRC','GPN','GPS','GRMN','GS','GWW','HAL','HAS','HBAN',
    'HCA','HCI','HES','HFC','HIG','HII','HLT','HOG','HOLX','HON',
    'HPQ','HRL','HSY','HUM','IBM','ICE','IFF','ILMN','INCY','INFO',
    'INTC','INTU','IP','IPG','IPGP','IQV','IR','IRM','ISRG','IT',
    'ITW','IVZ','JBHT','JCI','JEC','JEF','JNJ','JNPR','JPM','JWN',
    'K','KEY','KEYS','KHC','KIM','KLAC','KMB','KMI','KMX','KO',
    'KR','KSS','L','LB','LDOS','LEG','LEN','LHX','LH','LII',
    'LKQ','LLY','LMT','LNC','LNT','LOW','LRCX','LUV','LVS','LW',
    'LYB','LYV','M','MA','MAA','MAC','MAR','MAS','MAT','MCD',
    'MCK','MCO','MDLZ','MDT','MET','MGM','MHK','MKC','MLM','MMC',
    'MMM','MNST','MO','MOS','MPC','MRK','MRO','MS','MSFT','MSI',
    'MTB','MTCH','MU','MXIM','MYL','NCLH','NDAQ','NEE','NEM','NFLX',
    'NKE','NLSN','NOC','NOV','NRG','NSC','NTAP','NTRS','NUE','NVR',
    'NWL','NWS','NWSA','O','OAK','OKE','OMC','ORCL','ORLY','OTIS',
    'OXY','PAYX','PAYC','PBCT','PBF','PCAR','PCG','PCLN','PDCO','PEG',
    'PEP','PFG','PG','PGR','PH','PHM','PKG','PKI','PLD','PNC',
    'PNR','PNW','POOL','PPG','PPL','PRGO','PRU','PSX','PVH','PWR',
    'PXD','PYPL','QCOM','QRVO','RCL','RE','REG','REGN','RF','RHI',
    'RHT','RIO','RJF','RL','RMD','ROK','ROL','ROP','ROST','RSG',
    'RTX','SBAC','SBUX','SCHW','SEE','SJM','SLB','SLG','SNA','SNPS',
    'SO','SPG','SPGI','SRCL','SRE','STT','STX','STZ','SWK','SWKS',
    'SYF','SYK','SYY','T','TAP','TDG','TEL','TERM','TFX','TGT',
    'TIF','TJX','TMUS','TMO','TROW','TRV','TSCO','TSLA','TSN','TSS',
    'TTWO','TUP','TWTR','TXN','TXT','TYL','UA','UA.U','UAA','UAL',
    'UDR','UHS','ULTA','UNH','UNM','UNP','UPS','URI','USB','V',
    'VFC','VIAC','VLO','VMC','VNO','VRSK','VRSN','VRTS','VRTX','VTR',
    'VZ','WAB','WAT','WBA','WDC','WEC','WELL','WFC','WHR','WM',
    'WMB','WMT','WRB','WRI','WRK','WY','WYNN','X','XEL','XLNX',
    'XOM','XRAY','XRX','XYL','YUM','ZBH','ZION','ZTS',
    # (16) ADRs y globales frecuentes
    'BABA','TCEHY','NSRGF','BIDU','SNP','RIO','RIO.L','RDS.A','RDS.B','SNY',
    'BP','HSBA','TM','NSU','SAP','SAP.DE','SAP.VI','RHHBY','SJM.BR','PTR',
    # (17) Factores y símbolos auxiliares (índices)
    '^GSPC','^DJI','^IXIC','^MERV','^BVSP','^FTSE','^N225','^GDAXI','DXY','^VIX',
    # (18) Más ETFs, factores, bonos y smart-beta
    'VIG','VGT','IYW','SOXX','XOP','IYT','XLY','XLP','XLE','XLF',
    'VOO','SCHF','VT','ACWI','AGG','BND','IEFA','IEF','MBB','TIP',
    # (19) Pequeñas empresas argentinas adicionales (.BA) - Ya incluidos en (13)
    'BMA.BA','GGAL.BA','PAMP.BA','ALUA.BA','TRAN.BA','COME.BA','CEPU.BA','EDN.BA','TGSU2.BA','YPF.BA',
    'SUPV.BA','RICH.BA','MIRG.BA','MOLI.BA','PESA.BA','BIND.BA','BRIO.BA','BYMA.BA','GGAL','PAMP',
    # Tickers adicionales panel general y dólar cable (evitar duplicados)
    'BOLT.BA','CARC.BA','ROSE.BA','HSAT.BA','IRSA.BA','LONG.BA','GCDI.BA','CGPA2.BA','HAVA.BA',
    'BPAT.BA','GRIM.BA','IEB.BA','RIGO.BA','GBAN.BA','OEST.BA','DOME.BA','IRS2W.BA','CRE3W.BA',
    'DGCE.BA','REGE.BA','POLL.BA','YPFDB.BA','BMA.B.BA','PAMPB.BA','RAGH.BA','GGALB.BA',
    'BMA.D.BA','ECOGD.BA','EDND.BA','IRSAD.BA','LOMAD.BA','METRD.BA','PAMPD.BA','SUPVD.BA',
    'TECOD.BA','TGN4D.BA','TGSUD.BA','TRAND.BA','TXARD.BA','VALOD.BA','YPFDD.BA',
    'PAMPC.BA','SUPVC.BA','GGALC.BA','YPFDC.BA','A3D.BA','ALUAC.BA','BHIPD.BA','BYMAC.BA',
    'VALOC.BA','TGSUC.BA','BMA.C.BA','EDNC.BA','METRC.BA','CRESC.BA','CVHD.BA','MOLID.BA',
    'GGADB.BA','CTICB.BA','MORID.BA',
]

# Eliminar duplicados de la lista maestra
BIG_TICKERS_LIST = list(dict.fromkeys(BIG_TICKERS_LIST))  # Mantiene el orden

# DICCIONARIOS POR SECTOR
SECTOR_TICKERS_EN = {
    'Technology': TECH_TICKERS,
    'Financial Services': FINANCIAL_TICKERS,
    'Healthcare': HEALTHCARE_TICKERS,
    'Consumer Cyclical': CONSUMER_CYCLICAL_TICKERS,
    'Communication Services': COMMUNICATION_TICKERS,
    'Consumer Defensive': CONSUMER_DEFENSIVE_TICKERS,
    'Energy': ENERGY_TICKERS,
    'Industrials': INDUSTRIAL_TICKERS,
    'Basic Materials': MATERIALS_TICKERS,
    'Real Estate': REAL_ESTATE_TICKERS,
    'Utilities': UTILITIES_TICKERS
}

SECTOR_TICKERS_ES = {
    'Tecnología': TECH_TICKERS,
    'Technology': TECH_TICKERS,
    'Financiero': FINANCIAL_TICKERS,
    'Financial Services': FINANCIAL_TICKERS,
    'Salud': HEALTHCARE_TICKERS,
    'Healthcare': HEALTHCARE_TICKERS,
    'Consumo Discrecional': CONSUMER_CYCLICAL_TICKERS,
    'Consumer Cyclical': CONSUMER_CYCLICAL_TICKERS,
    'Consumo': CONSUMER_CYCLICAL_TICKERS,
    'Servicios de Comunicación': COMMUNICATION_TICKERS,
    'Communication Services': COMMUNICATION_TICKERS,
    'Consumo Básico': CONSUMER_DEFENSIVE_TICKERS,
    'Consumer Defensive': CONSUMER_DEFENSIVE_TICKERS,
    'Energía': ENERGY_TICKERS,
    'Energy': ENERGY_TICKERS,
    'Industriales': INDUSTRIAL_TICKERS,
    'Industrials': INDUSTRIAL_TICKERS,
    'Industrial': INDUSTRIAL_TICKERS,
    'Materiales Básicos': MATERIALS_TICKERS,
    'Basic Materials': MATERIALS_TICKERS,
    'Materials': MATERIALS_TICKERS,
    'Bienes Raíces': REAL_ESTATE_TICKERS,
    'Real Estate': REAL_ESTATE_TICKERS,
    'Servicios Públicos': UTILITIES_TICKERS,
    'Utilities': UTILITIES_TICKERS
}

# ETFs POR SECTOR PARA COMPARACIÓN
SECTOR_ETF_MAPPING = {
    'Technology': 'XLK',
    'Financial Services': 'XLF', 
    'Healthcare': 'XLV',
    'Consumer Cyclical': 'XLY',
    'Communication Services': 'XLC',
    'Consumer Defensive': 'XLP',
    'Energy': 'XLE',
    'Industrials': 'XLI',
    'Basic Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Utilities': 'XLU',
    'Tecnología': 'XLK',
    'Financiero': 'XLF',
    'Salud': 'XLV',
    'Consumo Discrecional': 'XLY',
    'Consumo': 'XLY',
    'Servicios de Comunicación': 'XLC',
    'Consumo Básico': 'XLP',
    'Energía': 'XLE',
    'Industriales': 'XLI',
    'Industrial': 'XLI',
    'Materiales Básicos': 'XLB',
    'Materials': 'XLB',
    'Bienes Raíces': 'XLRE',
    'Real Estate': 'XLRE',
    'Servicios Públicos': 'XLU'
}

# ETFs INTERNACIONALES
INTERNATIONAL_ETFS = {
    'EWW': 'MSCI México',
    'EWZ': 'MSCI Brasil', 
    'EWC': 'MSCI Canadá',
    'EWU': 'MSCI Reino Unido',
    'EWG': 'MSCI Alemania',
    'EWJ': 'MSCI Japón',
    'EWY': 'MSCI Corea',
    'FXI': 'FTSE China',
    'EEM': 'MSCI Mercados Emergentes',
    'EFA': 'MSCI Europa Australasia Lejano Oriente'
}

# ETFs DE FACTORES
FACTOR_ETFS = {
    'MTUM': 'Momentum',
    'QUAL': 'Calidad',
    'VLUE': 'Valor',
    'SIZE': 'Tamaño Pequeño',
    'USMV': 'Mínima Volatilidad'
}

# FACTORES Y BENCHMARKS COMPLETOS
FACTORES = {
    '^SPX': 'S&P 500',
    '^GSPC': 'S&P 500',
    '^IXIC': 'NASDAQ',
    '^DJI': 'Dow Jones',
    '^MXX': 'IPC México',
    '^STOXX': 'STOXX Europa 600',
    '^GDAXI': 'DAX',
    '^FCHI': 'CAC 40',
    '^VIX': 'Índice de Volatilidad',
    '^MERV': 'Índice MERVAL',
    'DX-Y.NYB': 'Índice Dólar',
    'DXY': 'Índice Dólar',
    'XLK': 'Sector Tecnología',
    'XLF': 'Sector Financiero',
    'XLV': 'Sector Salud',
    'XLE': 'Sector Energía',
    'XLC': 'Sector Servicios de Comunicación',
    'XLY': 'Sector Consumo Discrecional',
    'XLP': 'Sector Consumo Básico',
    'XLI': 'Sector Industrial',
    'XLB': 'Sector Materiales',
    'XLRE': 'Sector Inmobiliario',
    'XLU': 'Sector Servicios Públicos',
    'SPY': 'ETF S&P 500',
    'IVW': 'ETF S&P 500 Crecimiento',
    'IVE': 'Sector Valor',
    'IWM': 'Sector Crecimiento',
    **{k: f'ETF {v}' for k, v in INTERNATIONAL_ETFS.items()},
    **{k: f'Factor {v}' for k, v in FACTOR_ETFS.items()}
}

# FACTORES DE DIVERSIFICACIÓN
FACTORES_DIVERSIFICACION = {
    'MTUM': 'Factor Momentum',
    'QUAL': 'Factor Calidad',
    'VLUE': 'Factor Valor',
    'USMV': 'Factor Mínima Volatilidad',
    'SIZE': 'Factor Tamaño Pequeño',
    'XLP': 'Sector Consumo Básico',
    'XLV': 'Sector Salud',
    'XLU': 'Sector Servicios Públicos',
    'XLRE': 'Sector Inmobiliario',
    'XLE': 'Sector Energía',
    'XLB': 'Sector Materiales',
    'XLI': 'Sector Industrial',
    'XLF': 'Sector Financiero',
    'EWW': 'MSCI México',
    'EWZ': 'MSCI Brasil',
    'EWC': 'MSCI Canadá',
    'EWU': 'MSCI Reino Unido',
    'EWG': 'MSCI Alemania',
    'EWJ': 'MSCI Japón',
    'EEM': 'MSCI Mercados Emergentes',
    'EFA': 'MSCI Europa Australasia Lejano Oriente',
    'GLD': 'Oro',
    'SLV': 'Plata',
    'DBA': 'Agricultura',
    'USO': 'Petróleo',
    'TLT': 'Bonos del Tesoro 20+ años',
    'IEF': 'Bonos del Tesoro 7-10 años',
    'LQD': 'Bonos Corporativos Investment Grade',
    'HYG': 'Bonos de Alto Rendimiento'
}

# FUNCIONES AUXILIARES
def obtener_todos_tickers_sectores():
    """Obtiene todos los tickers de todos los sectores (sin duplicados)."""
    todos_tickers = set()
    for tickers in SECTOR_TICKERS_EN.values():
        todos_tickers.update(tickers)
    return todos_tickers

def obtener_lista_maestra(limit=None):
    """Devuelve la lista maestra de tickers."""
    if limit is None:
        return BIG_TICKERS_LIST.copy()
    return BIG_TICKERS_LIST[:limit]

def obtener_todos_tickers_combinados():
    """Obtiene todos los tickers combinando lista maestra, sectores, ETFs y factores."""
    todos_tickers = set(BIG_TICKERS_LIST)
    for tickers in SECTOR_TICKERS_EN.values():
        todos_tickers.update(tickers)
    todos_tickers.update(FACTORES.keys())
    todos_tickers.update(FACTORES_DIVERSIFICACION.keys())
    todos_tickers.update(INTERNATIONAL_ETFS.keys())
    todos_tickers.update(FACTOR_ETFS.keys())
    return todos_tickers


# ============================================================================
# SISTEMA DE CACHÉ
# ============================================================================

def verificar_soporte_parquet():
    """
    Verifica si hay soporte para formato Parquet disponible.
    
    Returns:
        bool: True si Parquet está disponible, False si no
    """
    try:
        # Intentar importar pyarrow primero (más común y más fácil de instalar)
        import pyarrow
        return True
    except ImportError:
        try:
            # Intentar fastparquet como alternativa
            import fastparquet
            return True
        except ImportError:
            return False

# Verificar soporte Parquet al cargar el módulo
_SOPORTE_PARQUET = verificar_soporte_parquet()


def obtener_nombre_cache(periodo, intervalo, usar_parquet=None):
    """
    Genera el nombre del archivo de caché basado en período e intervalo.
    
    Args:
        periodo (str): Período de datos ('1y', '2y', etc.)
        intervalo (str): Intervalo de datos ('1d', '1wk', etc.)
        usar_parquet (bool, optional): Si usar Parquet. Si None, detecta automáticamente
    
    Returns:
        str: Nombre del archivo de caché
    """
    if usar_parquet is None:
        usar_parquet = _SOPORTE_PARQUET
    
    extension = 'parquet' if usar_parquet else 'csv'
    return f'cache_series_{periodo}_{intervalo}.{extension}'


def cargar_cache(periodo, intervalo, directorio_cache='datos_series'):
    """
    Carga datos desde el caché si existe (soporta Parquet, CSV y JSON).
    ✅ MEJORADO: Ahora también carga desde JSON.
    
    Args:
        periodo (str): Período de datos
        intervalo (str): Intervalo de datos
        directorio_cache (str): Directorio donde buscar el caché
    
    Returns:
        tuple: (DataFrame con datos, dict con metadata) o (None, None) si no existe
    """
    cache_dir = Path(directorio_cache)
    
    # ✅ Prioridad: JSON > Parquet > CSV
    cache_file_json = cache_dir / obtener_nombre_cache(periodo, intervalo, usar_parquet=False).replace('.csv', '.json')
    cache_file_parquet = cache_dir / obtener_nombre_cache(periodo, intervalo, usar_parquet=True)
    cache_file_csv = cache_dir / obtener_nombre_cache(periodo, intervalo, usar_parquet=False)
    metadata_file = cache_dir / f"cache_metadata_{periodo}_{intervalo}.json"
    
    cache_file = None
    formato_cache = None
    
    # Intentar cargar en orden de prioridad: JSON > Parquet > CSV
    if cache_file_json.exists():
        cache_file = cache_file_json
        formato_cache = 'json'
    elif cache_file_parquet.exists() and _SOPORTE_PARQUET:
        cache_file = cache_file_parquet
        formato_cache = 'parquet'
    elif cache_file_csv.exists():
        cache_file = cache_file_csv
        formato_cache = 'csv'
    
    if cache_file is None or not cache_file.exists():
        return None, None
    
    try:
        # Cargar datos según el formato
        if formato_cache == 'json':
            import json
            with open(cache_file, 'r', encoding='utf-8') as f:
                data_dict = json.load(f)
            # Convertir JSON a DataFrame
            df_cache = pd.DataFrame(data_dict).T
            df_cache.index = pd.to_datetime(df_cache.index)
            df_cache = df_cache.sort_index()
        elif formato_cache == 'parquet':
            df_cache = pd.read_parquet(cache_file)
        else:  # csv
            df_cache = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        
        # Cargar metadata
        metadata = {}
        if metadata_file.exists():
            import json
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        return df_cache, metadata
    except Exception as e:
        print(f"   ⚠️ Error cargando caché ({formato_cache}): {e}")
        return None, None


def guardar_cache(df_series, periodo, intervalo, directorio_cache='datos_series', 
                  tickers_descargados=None):
    """
    Guarda datos en el caché (usa Parquet si está disponible, sino CSV).
    
    Args:
        df_series (pd.DataFrame): DataFrame con las series a guardar
        periodo (str): Período de datos
        intervalo (str): Intervalo de datos
        directorio_cache (str): Directorio donde guardar el caché
        tickers_descargados (list): Lista de tickers que se descargaron en esta ejecución
    """
    cache_dir = Path(directorio_cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_file = cache_dir / f"cache_metadata_{periodo}_{intervalo}.json"
    
    try:
        # Guardar datos según formato disponible
        if _SOPORTE_PARQUET:
            cache_file = cache_dir / obtener_nombre_cache(periodo, intervalo, usar_parquet=True)
            df_series.to_parquet(cache_file, compression='snappy')
            formato_usado = 'Parquet'
        else:
            cache_file = cache_dir / obtener_nombre_cache(periodo, intervalo, usar_parquet=False)
            df_series.to_csv(cache_file)
            formato_usado = 'CSV'
        
        # ✅ NUEVO: Guardar también en JSON para compatibilidad
        try:
            cache_file_json = cache_dir / obtener_nombre_cache(periodo, intervalo, usar_parquet=False).replace('.csv', '.json')
            # Convertir DataFrame a formato JSON compatible
            df_json = df_series.copy()
            df_json.index = df_json.index.strftime('%Y-%m-%d')
            df_json.to_json(cache_file_json, orient='index', date_format='iso')
            formato_usado += ' + JSON'
        except Exception as e:
            print(f"   ⚠️ No se pudo guardar en JSON: {e}")
        
        # Guardar metadata con información de fechas
        import json
        fecha_minima = df_series.index.min().strftime('%Y-%m-%d') if not df_series.empty else None
        fecha_maxima = df_series.index.max().strftime('%Y-%m-%d') if not df_series.empty else None
        
        metadata = {
            'fecha_actualizacion': datetime.now().isoformat(),
            'periodo': periodo,
            'intervalo': intervalo,
            'formato': formato_usado,
            'total_tickers': len(df_series.columns),
            'tickers': list(df_series.columns),
            'ultima_descarga': datetime.now().isoformat(),
            'tickers_descargados_esta_vez': tickers_descargados or [],
            'fecha_minima_datos': fecha_minima,
            'fecha_maxima_datos': fecha_maxima,
            'descarga_incremental': True  # Flag para indicar que soporta incrementales
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"   ⚠️ Error guardando caché: {e}")
        # Intentar CSV como respaldo si Parquet falló
        if _SOPORTE_PARQUET:
            try:
                cache_file_csv = cache_dir / obtener_nombre_cache(periodo, intervalo, usar_parquet=False)
                df_series.to_csv(cache_file_csv)
                print(f"   ✅ Guardado en CSV como respaldo")
                return True
            except Exception as e2:
                print(f"   ❌ Error guardando en CSV: {e2}")
        return False


def identificar_tickers_a_descargar(tickers_solicitados, df_cache, 
                                     max_edad_cache_horas=24,
                                     periodo='5y', intervalo='1d',
                                     directorio_cache='datos_series',
                                     descarga_incremental=True):
    """
    Identifica qué tickers necesitan descarga basándose en el caché.
    ✅ MEJORADO: Ahora detecta la última fecha del caché y solo descarga datos faltantes.
    
    Args:
        tickers_solicitados (list): Lista de todos los tickers solicitados
        df_cache (pd.DataFrame): DataFrame del caché o None
        max_edad_cache_horas (int): Máxima antigüedad del caché en horas antes de actualizar
        periodo (str): Período de datos (para buscar metadata)
        intervalo (str): Intervalo de datos (para buscar metadata)
        directorio_cache (str): Directorio del caché
        descarga_incremental (bool): Si True, solo descarga datos desde última fecha hasta hoy
    
    Returns:
        dict: {
            'tickers_en_cache': list,
            'tickers_a_descargar': list,
            'tickers_a_actualizar': list,  # Tickers en cache que necesitan actualización
            'actualizar_cache': bool,
            'fecha_inicio_actualizacion': str,  # Fecha desde la cual actualizar (ISO format)
            'descarga_incremental': bool  # Si se usará descarga incremental
        }
    """
    if df_cache is None or df_cache.empty:
        return {
            'tickers_en_cache': [],
            'tickers_a_descargar': tickers_solicitados,
            'tickers_a_actualizar': [],
            'actualizar_cache': True,
            'fecha_inicio_actualizacion': None,
            'descarga_incremental': False
        }
    
    # Tickers que están en el caché
    tickers_en_cache = [col for col in df_cache.columns if col in tickers_solicitados]
    
    # Tickers que faltan en el caché (nunca descargados)
    tickers_a_descargar = [t for t in tickers_solicitados if t not in tickers_en_cache]
    
    # ✅ NUEVO: Detectar última fecha del caché para descarga incremental
    fecha_inicio_actualizacion = None
    tickers_a_actualizar = []
    actualizar_cache = False
    usar_incremental = False
    
    if df_cache is not None and not df_cache.empty:
        # Obtener la última fecha disponible en el caché
        ultima_fecha_cache = df_cache.index.max()
        if isinstance(ultima_fecha_cache, pd.Timestamp):
            # Calcular días desde última fecha hasta hoy
            dias_desde_ultima = (datetime.now() - ultima_fecha_cache.to_pydatetime()).days
            
            # Si hay más de 1 día de diferencia, usar descarga incremental
            if descarga_incremental and dias_desde_ultima > 1:
                fecha_inicio_actualizacion = ultima_fecha_cache.strftime('%Y-%m-%d')
                tickers_a_actualizar = tickers_en_cache.copy()  # Actualizar todos los del cache
                usar_incremental = True
                print(f"   📅 Última fecha en caché: {ultima_fecha_cache.strftime('%Y-%m-%d')}")
                print(f"   📅 Actualizando desde: {fecha_inicio_actualizacion} hasta hoy ({dias_desde_ultima} días nuevos)")
    
    # Verificar si hay que actualizar el caché (si tiene más de max_edad_cache_horas)
    metadata_file = Path(directorio_cache) / f"cache_metadata_{periodo}_{intervalo}.json"
    
    if metadata_file.exists() and not usar_incremental:
        try:
            import json
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            fecha_actualizacion_str = metadata.get('fecha_actualizacion', metadata.get('ultima_descarga', datetime.now().isoformat()))
            if isinstance(fecha_actualizacion_str, str):
                fecha_actualizacion = datetime.fromisoformat(fecha_actualizacion_str)
            else:
                fecha_actualizacion = datetime.now()
            
            edad_cache = datetime.now() - fecha_actualizacion
            
            if edad_cache > timedelta(hours=max_edad_cache_horas):
                actualizar_cache = True
                if not usar_incremental and df_cache is not None and not df_cache.empty:
                    # Usar última fecha del caché como inicio
                    ultima_fecha = df_cache.index.max()
                    if isinstance(ultima_fecha, pd.Timestamp):
                        fecha_inicio_actualizacion = ultima_fecha.strftime('%Y-%m-%d')
                        tickers_a_actualizar = tickers_en_cache.copy()
                        usar_incremental = True
        except Exception as e:
            # Si hay error leyendo metadata, no actualizar
            pass
    
    return {
        'tickers_en_cache': tickers_en_cache,
        'tickers_a_descargar': tickers_a_descargar,
        'tickers_a_actualizar': tickers_a_actualizar,
        'actualizar_cache': actualizar_cache,
        'fecha_inicio_actualizacion': fecha_inicio_actualizacion,
        'descarga_incremental': usar_incremental
    }


def combinar_cache_y_descarga(df_cache, df_nuevo, eliminar_duplicados=True):
    """
    Combina datos del caché con datos nuevos descargados.
    ✅ MEJORADO: Elimina duplicados y combina correctamente datos incrementales.
    
    Args:
        df_cache (pd.DataFrame): DataFrame del caché
        df_nuevo (pd.DataFrame): DataFrame con nuevos datos
        eliminar_duplicados (bool): Si True, elimina duplicados de fechas
    
    Returns:
        pd.DataFrame: DataFrame combinado sin duplicados
    """
    if df_cache is None or df_cache.empty:
        return df_nuevo
    
    if df_nuevo is None or df_nuevo.empty:
        return df_cache
    
    # ✅ MEJORADO: Combinar correctamente eliminando duplicados
    df_combinado = df_cache.copy()
    
    # Para cada columna nueva, combinar eliminando duplicados
    for col in df_nuevo.columns:
        if col in df_combinado.columns:
            # Combinar series eliminando duplicados (prioridad a nuevos datos)
            serie_cache = df_combinado[col]
            serie_nuevo = df_nuevo[col]
            
            # Concatenar y eliminar duplicados manteniendo el último (nuevo)
            serie_combinada = pd.concat([serie_cache, serie_nuevo])
            if eliminar_duplicados:
                serie_combinada = serie_combinada[~serie_combinada.index.duplicated(keep='last')]
            
            df_combinado[col] = serie_combinada.sort_index()
        else:
            # Nueva columna, agregarla directamente
            df_combinado[col] = df_nuevo[col]
    
    # Ordenar por fecha y eliminar duplicados a nivel de índice completo
    df_combinado = df_combinado.sort_index()
    
    # Eliminar filas completamente duplicadas
    if eliminar_duplicados:
        df_combinado = df_combinado[~df_combinado.index.duplicated(keep='last')]
    
    return df_combinado


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def cargar_series_desde_cache(tickers=None, periodo='5y', intervalo='1d', 
                               directorio_cache='datos_series'):
    """
    Carga series históricas directamente desde el caché sin descargar.
    
    Args:
        tickers (list, optional): Lista de tickers a cargar. Si es None, carga todos.
        periodo (str): Período de datos
        intervalo (str): Intervalo de datos
        directorio_cache (str): Directorio del caché
    
    Returns:
        pd.DataFrame: DataFrame con las series solicitadas, o None si no hay caché
    """
    df_cache, metadata = cargar_cache(periodo, intervalo, directorio_cache)
    
    if df_cache is None or df_cache.empty:
        return None
    
    if tickers is None:
        return df_cache
    
    # Filtrar solo los tickers solicitados que existen en el caché
    tickers_disponibles = [t for t in tickers if t in df_cache.columns]
    if not tickers_disponibles:
        return None
    
    return df_cache[tickers_disponibles]


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def obtener_todos_tickers():
    """
    Obtiene todos los tickers únicos de todas las categorías.
    Incluye la lista maestra de ~1000 tickers si está disponible.
    
    Returns:
        dict: Diccionario con categorías y listas de tickers
    """
    tickers_dict = {}
    
    # Lista maestra (incluye ~1000 tickers de múltiples mercados)
    try:
        lista_maestra = obtener_lista_maestra()
        tickers_dict['lista_maestra'] = lista_maestra
    except:
        lista_maestra = []
        tickers_dict['lista_maestra'] = []
    
    # Tickers por sector
    tickers_dict['sectores'] = list(obtener_todos_tickers_sectores())
    
    # ETFs sectoriales
    tickers_dict['etfs_sectoriales'] = list(set(SECTOR_ETF_MAPPING.values()))
    
    # ETFs internacionales
    tickers_dict['etfs_internacionales'] = list(INTERNATIONAL_ETFS.keys())
    
    # ETFs de factores
    tickers_dict['etfs_factores'] = list(FACTOR_ETFS.keys())
    
    # Factores y benchmarks (solo los tickers, no las descripciones)
    tickers_dict['factores_benchmarks'] = list(FACTORES.keys())
    
    # Factores de diversificación
    tickers_dict['factores_diversificacion'] = list(FACTORES_DIVERSIFICACION.keys())
    
    # Combinar todos en una lista única
    todos_tickers = set()
    for categoria, tickers in tickers_dict.items():
        todos_tickers.update(tickers)
    
    tickers_dict['todos_unicos'] = sorted(list(todos_tickers))
    
    return tickers_dict


def descargar_series_tickers(tickers, periodo='5y', intervalo='1d', 
                             directorio_salida='datos_series', 
                             batch_size=50, usar_cache=True, max_edad_cache_horas=24):
    """
    Descarga series históricas de una lista de tickers con sistema de caché automático.
    
    Args:
        tickers (list): Lista de tickers a descargar
        periodo (str): Período de descarga ('1y', '2y', '5y', '10y', 'max')
        intervalo (str): Intervalo de datos ('1d', '1wk', '1mo')
        directorio_salida (str): Directorio donde guardar los datos
        batch_size (int): Número de tickers a descargar por lote
        usar_cache (bool): Si True, usa el caché para evitar descargas innecesarias
        max_edad_cache_horas (int): Máxima antigüedad del caché antes de actualizar
    
    Returns:
        dict: Diccionario con resultados de la descarga
    """
    print(f"\n📊 Iniciando descarga de series históricas...")
    print(f"   Total de tickers solicitados: {len(tickers)}")
    print(f"   Período: {periodo}")
    print(f"   Intervalo: {intervalo}")
    print(f"   Tamaño de lote: {batch_size} tickers")
    print(f"   Caché: {'✅ Habilitado' if usar_cache else '❌ Deshabilitado'}")
    
    # Crear directorio de salida
    output_dir = Path(directorio_salida)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ========================================================================
    # PASO 1: Cargar caché si está habilitado
    # ========================================================================
    df_cache = None
    datos_desde_cache = {}
    
    if usar_cache:
        print(f"\n🔍 Verificando caché...")
        df_cache, metadata_cache = cargar_cache(periodo, intervalo, directorio_salida)
        
        if df_cache is not None and not df_cache.empty:
            print(f"   ✅ Caché encontrado con {len(df_cache.columns)} tickers")
            
            # Extraer datos del caché
            for col in df_cache.columns:
                if col in tickers:
                    datos_desde_cache[col] = df_cache[col]
            
            print(f"   📦 {len(datos_desde_cache)} tickers disponibles en caché")
        else:
            print(f"   ⚠️ No se encontró caché o está vacío")
    
    # ========================================================================
    # PASO 2: Identificar qué tickers necesitan descarga
    # ========================================================================
    analisis_cache = identificar_tickers_a_descargar(
        tickers, 
        df_cache, 
        max_edad_cache_horas,
        periodo,
        intervalo,
        directorio_salida,
        descarga_incremental=True  # ✅ Habilitar descarga incremental
    )
    
    tickers_en_cache = analisis_cache['tickers_en_cache']
    tickers_a_descargar = analisis_cache['tickers_a_descargar']
    tickers_a_actualizar = analisis_cache.get('tickers_a_actualizar', [])
    actualizar_cache = analisis_cache['actualizar_cache']
    fecha_inicio_actualizacion = analisis_cache.get('fecha_inicio_actualizacion')
    usar_incremental = analisis_cache.get('descarga_incremental', False)
    
    print(f"\n📋 Análisis de caché:")
    print(f"   ✅ Tickers en caché: {len(tickers_en_cache)}")
    print(f"   ⬇️ Tickers nuevos a descargar: {len(tickers_a_descargar)}")
    print(f"   🔄 Tickers a actualizar (incremental): {len(tickers_a_actualizar)}")
    
    if usar_incremental and fecha_inicio_actualizacion:
        print(f"   📅 Descarga incremental: desde {fecha_inicio_actualizacion} hasta hoy")
    
    # Combinar tickers nuevos y tickers a actualizar
    todos_tickers_a_procesar = list(set(tickers_a_descargar + tickers_a_actualizar))
    
    # Si no hay tickers a procesar, retornar datos del caché
    if not todos_tickers_a_procesar:
        print(f"\n✅ Todos los tickers están en caché y actualizados, no es necesario descargar nada")
        return {
            'datos': datos_desde_cache,
            'exitosos': list(datos_desde_cache.keys()),
            'fallidos': [],
            'errores': {},
            'desde_cache': True,
            'descarga_incremental': False
        }
    
    # ========================================================================
    # PASO 3: Descargar tickers faltantes y actualizar existentes
    # ========================================================================
    print(f"\n⬇️ Descargando {len(todos_tickers_a_procesar)} tickers ({len(tickers_a_descargar)} nuevos + {len(tickers_a_actualizar)} a actualizar)...")
    
    # Preparar almacenamiento de datos
    datos_descargados = {}
    tickers_exitosos = [t for t in tickers_en_cache if t not in tickers_a_actualizar]  # Mantener los que no necesitan actualización
    tickers_fallidos = []
    errores = {}
    
    # ✅ NUEVO: Calcular fecha de inicio para descarga incremental
    start_date = None
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    if usar_incremental and fecha_inicio_actualizacion:
        # Usar fecha de inicio desde el día siguiente a la última fecha del caché
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_actualizacion, '%Y-%m-%d')
            # Empezar desde el día siguiente (no incluir la última fecha que ya tenemos)
            fecha_inicio = fecha_inicio + timedelta(days=1)
            start_date = fecha_inicio.strftime('%Y-%m-%d')
            print(f"   📅 Descarga incremental: desde {start_date} hasta {end_date}")
        except Exception as e:
            print(f"   ⚠️ Error calculando fecha inicio: {e}, usando descarga completa")
            start_date = None
    
    # Dividir tickers a descargar en lotes
    total_batches = (len(todos_tickers_a_procesar) + batch_size - 1) // batch_size
    
    for batch_idx in range(0, len(todos_tickers_a_procesar), batch_size):
        batch = todos_tickers_a_procesar[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1
        
        print(f"\n   📦 Procesando lote {batch_num}/{total_batches} ({len(batch)} tickers)...")
        
        try:
            # Descargar datos del lote (incremental o completo)
            if start_date:
                print(f"      ⬇️ Descargando datos incrementales desde {start_date}...")
                data = yf.download(
                    batch,
                    start=start_date,
                    end=end_date,
                    interval=intervalo,
                    progress=False,
                    auto_adjust=True,
                    threads=True,
                    group_by='ticker'
                )
            else:
                print(f"      ⬇️ Descargando datos completos...")
                data = yf.download(
                    batch,
                    period=periodo,
                    interval=intervalo,
                    progress=False,
                    auto_adjust=True,
                    threads=True,
                    group_by='ticker'
                )
            
            if data.empty:
                print(f"      ⚠️ Lote vacío, saltando...")
                tickers_fallidos.extend(batch)
                continue
            
            # Procesar datos descargados
            # yf.download puede retornar MultiIndex o DataFrame simple dependiendo del número de tickers
            closes = None
            
            # Intentar obtener precios de cierre
            if isinstance(data.columns, pd.MultiIndex):
                # Múltiples tickers: estructura MultiIndex (Ticker, Column) o (Column, Ticker)
                # Verificar estructura: puede ser (Ticker, Column) o (Column, Ticker)
                niveles = data.columns.nlevels
                nombres_niveles = data.columns.names
                
                if niveles == 2:
                    # Buscar 'Close' en ambos niveles
                    if 'Close' in data.columns.levels[0]:
                        closes = data['Close']
                    elif 'Close' in data.columns.levels[1]:
                        closes = data.xs('Close', level=1, axis=1)
                    else:
                        # Intentar buscar en los valores de las columnas
                        try:
                            closes = data.xs('Close', level=0, axis=1)
                        except KeyError:
                            try:
                                closes = data.xs('Close', level=1, axis=1)
                            except KeyError:
                                closes = None
                else:
                    closes = data
            else:
                # Estructura simple (un solo ticker o formato especial)
                if 'Close' in data.columns:
                    closes = pd.DataFrame(data['Close'])
                    closes.columns = [batch[0]] if len(batch) == 1 else ['Close']
                elif len(batch) == 1:
                    # Un solo ticker sin MultiIndex
                    closes = pd.DataFrame(data)
                    closes.columns = [batch[0]]
                else:
                    closes = data
            
            if closes is None or closes.empty:
                print(f"      ⚠️ No se pudieron extraer precios de cierre del lote")
                tickers_fallidos.extend(batch)
                for ticker in batch:
                    errores[ticker] = "No se pudieron extraer precios de cierre"
                continue
            
            # Extraer series para cada ticker del lote
            for ticker in batch:
                try:
                    # Intentar diferentes formas de acceder a la serie del ticker
                    serie = None
                    
                    if isinstance(closes.columns, pd.MultiIndex):
                        # MultiIndex: buscar el ticker en las columnas
                        if ticker in closes.columns.get_level_values(0):
                            serie = closes[ticker]
                        elif ticker in closes.columns.get_level_values(-1):
                            serie = closes.xs(ticker, level=-1, axis=1).iloc[:, 0]
                        else:
                            # Buscar en todas las columnas
                            for col in closes.columns:
                                if ticker in str(col):
                                    serie = closes[col] if isinstance(col, str) else closes.xs(ticker, level=0, axis=1)
                                    break
                    else:
                        # Columnas simples
                        if ticker in closes.columns:
                            serie = closes[ticker]
                        elif len(closes.columns) == 1 and len(batch) == 1:
                            # Un solo ticker, una sola columna
                            serie = closes.iloc[:, 0]
                    
                    if serie is None or (hasattr(serie, 'empty') and serie.empty):
                        tickers_fallidos.append(ticker)
                        errores[ticker] = "Ticker no encontrado en datos descargados"
                        print(f"      ⚠️ {ticker}: no encontrado")
                        continue
                    
                    # Limpiar serie (eliminar NaN)
                    serie = serie.dropna()
                    
                    if len(serie) > 0:
                        datos_descargados[ticker] = serie
                        tickers_exitosos.append(ticker)
                        print(f"      ✅ {ticker}: {len(serie)} registros")
                    else:
                        tickers_fallidos.append(ticker)
                        errores[ticker] = "Serie vacía después de limpieza"
                        print(f"      ⚠️ {ticker}: serie vacía")
                        
                except Exception as e:
                    tickers_fallidos.append(ticker)
                    errores[ticker] = f"Error procesando: {str(e)[:100]}"
                    print(f"      ⚠️ {ticker}: error al procesar")
        
        except Exception as e:
            error_msg = str(e)[:200]
            print(f"      ❌ Error en lote: {error_msg}")
            for ticker in batch:
                tickers_fallidos.append(ticker)
                errores[ticker] = error_msg
        
        # Pequeño delay entre lotes para evitar rate limiting
        if batch_idx + batch_size < len(tickers_a_descargar):
            import time
            time.sleep(0.5)
    
    print(f"\n✅ Descarga completada:")
    print(f"   ✓ Exitosos: {len(tickers_exitosos)} ({len(tickers_en_cache)} del caché + {len(tickers_exitosos) - len(tickers_en_cache)} descargados)")
    print(f"   ✗ Fallidos: {len(tickers_fallidos)}")
    
    # ========================================================================
    # PASO 4: Combinar datos del caché con datos nuevos
    # ========================================================================
    print(f"\n🔄 Combinando datos del caché con datos nuevos...")
    
    # ✅ MEJORADO: Combinar correctamente datos incrementales con caché
    if df_cache is not None and not df_cache.empty:
        # Usar función mejorada de combinación que elimina duplicados
        df_nuevo = pd.DataFrame(datos_descargados) if datos_descargados else pd.DataFrame()
        if not df_nuevo.empty:
            df_completo = combinar_cache_y_descarga(df_cache, df_nuevo, eliminar_duplicados=True)
        else:
            df_completo = df_cache.copy()
        
        # Agregar tickers que estaban en caché pero no se actualizaron
        for ticker in tickers_exitosos:
            if ticker not in df_completo.columns and ticker in df_cache.columns:
                df_completo[ticker] = df_cache[ticker]
    else:
        # No hay caché, usar solo datos descargados
        datos_completos = datos_desde_cache.copy()
        datos_completos.update(datos_descargados)
        df_completo = pd.DataFrame(datos_completos) if datos_completos else pd.DataFrame()
    
    # Ordenar por fecha
    if not df_completo.empty:
        df_completo = df_completo.sort_index()
        
        # Guardar en caché si está habilitado
        if usar_cache:
            print(f"\n💾 Guardando en caché...")
            guardar_cache(
                df_completo, 
                periodo, 
                intervalo, 
                directorio_salida,
                tickers_descargados=list(datos_descargados.keys())
            )
            print(f"   ✅ Caché actualizado")
        
        # Guardar en CSV (siempre disponible)
        print(f"\n💾 Guardando archivos de salida (CSV)...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_csv = output_dir / f'series_historicas_{periodo}_{timestamp}.csv'
        df_completo.to_csv(archivo_csv)
        print(f"   ✅ Guardado en CSV: {archivo_csv}")
        
        # Guardar en Parquet solo si está disponible
        if _SOPORTE_PARQUET:
            try:
                archivo_parquet = output_dir / f'series_historicas_{periodo}_{timestamp}.parquet'
                df_completo.to_parquet(archivo_parquet, compression='snappy')
                print(f"   ✅ Guardado en Parquet: {archivo_parquet}")
            except Exception as e:
                print(f"   ⚠️ No se pudo guardar en Parquet: {e}")
        else:
            print(f"   ℹ️ Parquet no disponible (instala pyarrow o fastparquet para soporte Parquet)")
        
        # Guardar metadatos
        metadata = {
            'fecha_descarga': datetime.now().isoformat(),
            'periodo': periodo,
            'intervalo': intervalo,
            'total_tickers_solicitados': len(tickers),
            'tickers_en_cache': len(tickers_en_cache),
            'tickers_descargados': len(datos_descargados),
            'tickers_exitosos': len(tickers_exitosos),
            'tickers_fallidos': len(tickers_fallidos),
            'tickers_exitosos_lista': sorted(tickers_exitosos),
            'tickers_fallidos_lista': sorted(tickers_fallidos),
            'errores': errores,
            'usar_cache': usar_cache
        }
        
        import json
        archivo_metadata = output_dir / f'metadata_descarga_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(archivo_metadata, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Metadatos guardados: {archivo_metadata}")
    else:
        print(f"\n⚠️ No hay datos para guardar")
        df_completo = pd.DataFrame()
    
    return {
        'datos': {col: df_completo[col] for col in df_completo.columns} if not df_completo.empty else {},
        'exitosos': tickers_exitosos,
        'fallidos': tickers_fallidos,
        'errores': errores,
        'desde_cache': len(datos_descargados) == 0 and len(datos_desde_cache) > 0,
        'tickers_en_cache': tickers_en_cache,
        'tickers_descargados': list(datos_descargados.keys()),
        'descarga_incremental': usar_incremental,
        'fecha_inicio_actualizacion': fecha_inicio_actualizacion
    }


# ============================================================================
# FUNCIONES DE EXPORTACIÓN A JSON
# ============================================================================

def identificar_indices():
    """
    Identifica qué factores son índices (no ETFs).
    
    Returns:
        set: Conjunto de tickers que son índices
    """
    indices = set()
    for ticker in FACTORES.keys():
        # Los índices típicamente empiezan con ^ o son DXY/DX-Y.NYB
        if ticker.startswith('^') or ticker in ['DX-Y.NYB', 'DXY', 'VIX']:
            indices.add(ticker)
    return indices


def obtener_factores_no_indices():
    """
    Obtiene todos los factores que NO son índices (solo ETFs).
    
    Returns:
        dict: Diccionario {ticker: nombre} de factores que son ETFs
    """
    indices = identificar_indices()
    factores_etfs = {}
    
    for ticker, nombre in FACTORES.items():
        if ticker not in indices:
            factores_etfs[ticker] = nombre
    
    # Agregar también los ETFs de las otras categorías
    factores_etfs.update(SECTOR_ETF_MAPPING)
    factores_etfs.update(INTERNATIONAL_ETFS)
    factores_etfs.update({k: f'Factor {v}' for k, v in FACTOR_ETFS.items()})
    
    return factores_etfs


def cargar_monedas_cache(directorio_cache='datos_series', archivo_json='series_historicas.json'):
    """
    Carga las monedas detectadas desde el caché (JSON).
    
    Args:
        directorio_cache (str): Directorio donde buscar el caché
        archivo_json (str): Nombre del archivo JSON con las series
    
    Returns:
        dict: Diccionario {ticker: moneda} o {} si no existe
    """
    cache_dir = Path(directorio_cache)
    json_file = cache_dir / archivo_json
    
    if not json_file.exists():
        return {}
    
    try:
        import json
        with open(json_file, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        # Buscar monedas en el JSON
        monedas = datos.get('monedas', {})
        return monedas
    except Exception as e:
        print(f"   ⚠️ Error cargando monedas desde caché: {e}")
        return {}


def guardar_monedas_cache(monedas_tickers, directorio_cache='datos_series', 
                          archivo_cache='monedas_cache.json'):
    """
    Guarda las monedas detectadas en un archivo de caché separado.
    
    Args:
        monedas_tickers (dict): Diccionario {ticker: moneda}
        directorio_cache (str): Directorio donde guardar el caché
        archivo_cache (str): Nombre del archivo de caché
    """
    cache_dir = Path(directorio_cache)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / archivo_cache
    
    try:
        import json
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(monedas_tickers, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"   ⚠️ Error guardando monedas en caché: {e}")


def detectar_moneda_ticker(ticker: str) -> str:
    """
    Detecta la moneda de un ticker basándose en el formato del ticker.
    
    Reglas:
    - Tickers con "D" o ".C." (como MELID.BA, AAPLD.BA) → USD (CEDEARs en USD)
    - Tickers sin "D" que terminan en .BA (como MELI.BA, GGAL.BA) → ARS (acciones argentinas)
    - Tickers sin .BA → USD (tickers internacionales)
    
    Args:
        ticker: Ticker a analizar
    
    Returns:
        'USD' o 'ARS' según la moneda detectada
    """
    # Si termina en .BA, verificar si tiene D o C (CEDEARs en USD)
    if ticker.endswith('.BA'):
        # CEDEARs en USD: terminan en D.BA, tienen .D.BA, o tienen .C.BA
        if (ticker.endswith('D.BA') or 
            '.D.BA' in ticker or 
            '.C.BA' in ticker or
            ticker.endswith('C.BA')):
            return 'USD'  # CEDEARs en USD (ej: MELID.BA, AAPLD.BA)
        else:
            # Acciones argentinas en ARS (ej: MELI.BA, GGAL.BA, ALUA.BA)
            return 'ARS'
    
    # Para tickers sin .BA, intentar obtener info de yfinance como fallback
    try:
        t = yf.Ticker(ticker)
        info = t.info
        currency = info.get('currency', '').upper()
        if currency == 'ARS':
            return 'ARS'
        elif currency == 'USD':
            return 'USD'
    except:
        pass
    
    # Por defecto, asumir USD para tickers internacionales
    return 'USD'


def exportar_a_json(df_series, periodo='5y', intervalo='1d', 
                     output_file='series_historicas.json'):
    """
    Exporta series históricas a JSON con la estructura requerida por el HTML.
    Incluye detección automática de monedas para cada ticker.
    
    Args:
        df_series (pd.DataFrame): DataFrame con las series (índice=fechas, columnas=tickers)
        periodo (str): Período de las series
        intervalo (str): Intervalo de las series
        output_file (str): Nombre del archivo JSON de salida
    
    Returns:
        bool: True si se exportó exitosamente, False en caso contrario
    """
    if df_series is None or df_series.empty:
        print("❌ Error: No hay datos para exportar a JSON")
        return False
    
    print(f"\n📤 Exportando a JSON: {output_file}")
    
    # 1. Identificar activos y factores
    # ✅ CORREGIDO: Incluir todos los tickers (lista maestra + sectores), no solo sectores
    # obtener_todos_tickers_combinados() ya incluye BIG_TICKERS_LIST + sectores + ETFs
    todos_tickers = obtener_todos_tickers_combinados()
    
    factores_etfs = obtener_factores_no_indices()
    indices = identificar_indices()
    
    # Activos: todos los tickers que están en los datos Y que no son factores/ETFs/índices
    # Excluir factores, ETFs e índices de la lista de activos
    tickers_factores_etfs_indices = set(factores_etfs.keys()).union(indices)
    activos_disponibles = [t for t in df_series.columns 
                          if t in todos_tickers and t not in tickers_factores_etfs_indices]
    
    # Factores: todos los ETFs que están en los datos y NO son índices
    factores_disponibles = {
        t: factores_etfs.get(t, t) 
        for t in df_series.columns 
        if t in factores_etfs and t not in indices
    }
    
    print(f"   ✅ Activos identificados: {len(activos_disponibles)}")
    print(f"   ✅ Factores identificados (ETFs, sin índices): {len(factores_disponibles)}")
    print(f"   ⚠️ Índices excluidos: {len([t for t in df_series.columns if t in indices])}")
    
    if not activos_disponibles:
        print("❌ Error: No se encontraron activos en los datos")
        return False
    
    if not factores_disponibles:
        print("❌ Error: No se encontraron factores (ETFs) en los datos")
        return False
    
    # 2. Preparar datos para JSON
    # Convertir fechas a strings
    fechas = [fecha.strftime('%Y-%m-%d') if hasattr(fecha, 'strftime') else str(fecha) 
              for fecha in df_series.index]
    
    # Preparar precios de activos
    precios_activos = {}
    for activo in activos_disponibles:
        if activo in df_series.columns:
            serie = df_series[activo].ffill().bfill()
            precios_activos[activo] = serie.tolist()
    
    # Preparar precios de factores
    precios_factores = {}
    for factor, nombre in factores_disponibles.items():
        if factor in df_series.columns:
            serie = df_series[factor].ffill().bfill()
            precios_factores[factor] = {
                'nombre': nombre,
                'precios': serie.tolist()
            }
    
    # 3. Mapear activos por sector
    activos_por_sector = {}
    for sector, tickers_sector in SECTOR_TICKERS_ES.items():
        # Filtrar solo los tickers que están disponibles en los datos
        tickers_disponibles = [t for t in tickers_sector if t in activos_disponibles]
        if tickers_disponibles:
            activos_por_sector[sector] = tickers_disponibles
    
    print(f"   ✅ {len(activos_por_sector)} sectores con activos disponibles")
    
    # 4. Cargar monedas desde caché y detectar solo las faltantes
    print(f"\n   💱 Cargando monedas desde caché...")
    
    # Intentar cargar desde el JSON principal primero
    output_path = Path(output_file)
    directorio_json = output_path.parent
    monedas_cache = cargar_monedas_cache(str(directorio_json), output_path.name)
    
    # También intentar cargar desde archivo de caché separado
    if not monedas_cache:
        monedas_cache = cargar_monedas_cache(str(directorio_json), 'monedas_cache.json')
    
    todos_tickers_para_detectar = activos_disponibles + list(factores_disponibles.keys())
    
    # Identificar tickers que faltan en el caché
    tickers_faltantes = [t for t in todos_tickers_para_detectar if t not in monedas_cache]
    
    if tickers_faltantes:
        print(f"   📋 Monedas en caché: {len(monedas_cache)}")
        print(f"   🔍 Detectando monedas para {len(tickers_faltantes)} tickers nuevos...")
        
        for i, ticker in enumerate(tickers_faltantes):
            if i % 50 == 0:
                print(f"      Procesando {i+1}/{len(tickers_faltantes)}...")
            monedas_cache[ticker] = detectar_moneda_ticker(ticker)
        
        # Guardar monedas actualizadas en caché
        guardar_monedas_cache(monedas_cache, str(directorio_json), 'monedas_cache.json')
        print(f"   ✅ Monedas actualizadas en caché")
    else:
        print(f"   ✅ Todas las monedas están en caché ({len(monedas_cache)} tickers)")
    
    monedas_tickers = monedas_cache
    
    # Contar monedas detectadas
    monedas_count = {}
    for moneda in monedas_tickers.values():
        monedas_count[moneda] = monedas_count.get(moneda, 0) + 1
    print(f"   ✅ Monedas totales: {monedas_count}")
    
    # 5. Calcular matrices de correlación y R² entre todos los activos
    print(f"\n   📊 Calculando matrices de correlación y R² entre {len(activos_disponibles)} activos...")
    
    # Calcular retornos diarios para todos los activos (una sola vez)
    df_activos = df_series[activos_disponibles].copy()
    retornos_activos = df_activos.pct_change().dropna()
    
    # Filtrar solo activos que tienen datos en retornos
    activos_con_datos = [t for t in activos_disponibles if t in retornos_activos.columns]
    
    if len(activos_con_datos) < 2:
        print(f"   ⚠️ No hay suficientes activos con datos para calcular matrices")
        matriz_correlacion = {}
        matriz_r2 = {}
    else:
        # Usar método vectorizado de pandas para calcular correlación (más rápido)
        print(f"   ⚡ Calculando matriz de correlación usando método vectorizado...")
        try:
            # Calcular matriz de correlación completa de una vez (mucho más rápido)
            matriz_corr_df = retornos_activos[activos_con_datos].corr()
            
            # Convertir a diccionario anidado
            matriz_correlacion = {}
            matriz_r2 = {}
            
            for ticker1 in activos_con_datos:
                matriz_correlacion[ticker1] = {}
                matriz_r2[ticker1] = {}
                
                for ticker2 in activos_con_datos:
                    try:
                        correlacion = float(matriz_corr_df.loc[ticker1, ticker2])
                        if np.isnan(correlacion):
                            correlacion = None
                        else:
                            correlacion = round(correlacion, 6)
                    except:
                        correlacion = None
                    
                    # Calcular R² (correlación al cuadrado)
                    if correlacion is not None:
                        r2 = round(correlacion ** 2, 6)
                    else:
                        r2 = None
                    
                    matriz_correlacion[ticker1][ticker2] = correlacion
                    matriz_r2[ticker1][ticker2] = r2
            
            total_pares = len(activos_con_datos) * (len(activos_con_datos) - 1) // 2
            print(f"   ✅ Matrices calculadas: {total_pares} pares procesados (método vectorizado)")
        except Exception as e:
            print(f"   ⚠️ Error en método vectorizado, usando método iterativo: {e}")
            # Fallback al método iterativo si falla el vectorizado
            matriz_correlacion = {ticker: {} for ticker in activos_con_datos}
            matriz_r2 = {ticker: {} for ticker in activos_con_datos}
            
            total_pares = len(activos_con_datos) * (len(activos_con_datos) - 1) // 2
            pares_procesados = 0
            
            for i, ticker1 in enumerate(activos_con_datos):
                serie1 = retornos_activos[ticker1].dropna()
                
                # Diagonal: correlación perfecta y R² = 1
                matriz_correlacion[ticker1][ticker1] = 1.0
                matriz_r2[ticker1][ticker1] = 1.0
                
                for j, ticker2 in enumerate(activos_con_datos):
                    if i >= j:  # Solo calcular una vez por par (matriz simétrica)
                        continue
                    
                    serie2 = retornos_activos[ticker2].dropna()
                    
                    # Alinear series por fecha
                    aligned = pd.DataFrame({ticker1: serie1, ticker2: serie2}).dropna()
                    
                    if len(aligned) < 20:  # Mínimo de datos para calcular correlación
                        correlacion = None
                        r2 = None
                    else:
                        # Calcular correlación
                        try:
                            correlacion = float(aligned[ticker1].corr(aligned[ticker2]))
                            if np.isnan(correlacion):
                                correlacion = None
                            else:
                                correlacion = round(correlacion, 6)
                        except:
                            correlacion = None
                        
                        # Calcular R² (correlación al cuadrado)
                        if correlacion is not None:
                            r2 = round(correlacion ** 2, 6)
                        else:
                            r2 = None
                    
                    # Guardar en ambas direcciones (matriz simétrica)
                    matriz_correlacion[ticker1][ticker2] = correlacion
                    matriz_r2[ticker1][ticker2] = r2
                    matriz_correlacion[ticker2][ticker1] = correlacion
                    matriz_r2[ticker2][ticker1] = r2
                    
                    pares_procesados += 1
                    if pares_procesados % 100 == 0:
                        print(f"      Procesados {pares_procesados}/{total_pares} pares...")
            
            print(f"   ✅ Matrices calculadas: {pares_procesados} pares procesados (método iterativo)")
    
    # 6. Crear estructura JSON
    datos_json = {
        'metadata': {
            'fecha_exportacion': datetime.now().isoformat(),
            'periodo': periodo,
            'intervalo': intervalo,
            'total_fechas': len(fechas),
            'total_activos': len(activos_disponibles),
            'total_factores': len(factores_disponibles),
            'fecha_inicio': fechas[0] if fechas else None,
            'fecha_fin': fechas[-1] if fechas else None
        },
        'fechas': fechas,
        'activos': {
            'lista': activos_disponibles,
            'precios': precios_activos
        },
        'factores': {
            'lista': list(factores_disponibles.keys()),
            'nombres': factores_disponibles,
            'precios': precios_factores
        },
        'sectores': activos_por_sector,
        'monedas': monedas_tickers,  # Guardar monedas detectadas
        'matrices': {
            'correlacion': matriz_correlacion,  # Matriz de correlación entre todos los activos
            'r2': matriz_r2  # Matriz de R² entre todos los activos
        }
    }
    
    # 5. Guardar JSON
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, indent=2, ensure_ascii=False, default=str)
        
        tamaño_mb = output_path.stat().st_size / 1024 / 1024
        print(f"✅ Archivo JSON generado exitosamente")
        print(f"   Tamaño: {tamaño_mb:.2f} MB")
        print(f"   Activos: {len(activos_disponibles)}")
        print(f"   Factores: {len(factores_disponibles)}")
        print(f"   Fechas: {len(fechas)}")
        print(f"   Matrices: Correlación y R² calculadas para {len(activos_disponibles)} activos")
        return True
    except Exception as e:
        print(f"❌ Error guardando JSON: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal del script"""
    print("=" * 70)
    print("📥 DESCARGADOR Y EXPORTADOR DE SERIES HISTÓRICAS")
    print("=" * 70)
    
    # Mostrar información sobre formato de caché
    if _SOPORTE_PARQUET:
        print(f"\n💾 Formato de caché: Parquet (eficiente)")
    else:
        print(f"\n💾 Formato de caché: CSV (Parquet no disponible)")
        print(f"   💡 Para usar Parquet, instala: pip install pyarrow")
    
    # Obtener todos los tickers
    print("\n🔍 Recolectando tickers de todas las categorías...")
    tickers_dict = obtener_todos_tickers()
    
    print(f"\n📋 Resumen de tickers por categoría:")
    for categoria, tickers in tickers_dict.items():
        if categoria != 'todos_unicos':
            print(f"   • {categoria.replace('_', ' ').title()}: {len(tickers)} tickers")
    
    print(f"\n   📊 TOTAL ÚNICO: {len(tickers_dict['todos_unicos'])} tickers")
    
    # Mostrar algunos ejemplos
    print(f"\n   Ejemplos de tickers:")
    ejemplos = tickers_dict['todos_unicos'][:10]
    print(f"   {', '.join(ejemplos)}...")
    
    # Configuración de descarga
    periodo = '5y'  # Puedes cambiar a '1y', '2y', '10y', 'max'
    intervalo = '1d'  # '1d', '1wk', '1mo'
    directorio_salida = 'datos_series'
    batch_size = 50  # Tickers por lote (ajustar según conexión)
    usar_cache = True  # Habilitar caché automático
    max_edad_cache_horas = 24  # Actualizar caché si tiene más de 24 horas
    
    # Preguntar confirmación
    print(f"\n⚙️ Configuración de descarga:")
    print(f"   Período: {periodo}")
    print(f"   Intervalo: {intervalo}")
    print(f"   Directorio de salida: {directorio_salida}")
    print(f"   Tamaño de lote: {batch_size}")
    print(f"   Caché automático: {'✅ Habilitado' if usar_cache else '❌ Deshabilitado'}")
    if usar_cache:
        print(f"   Max. edad caché: {max_edad_cache_horas} horas")
    
    respuesta = input(f"\n¿Continuar con la descarga? (s/n): ").strip().lower()
    if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Descarga cancelada por el usuario")
        return
    
    # Descargar series
    resultado = descargar_series_tickers(
        tickers=tickers_dict['todos_unicos'],
        periodo=periodo,
        intervalo=intervalo,
        directorio_salida=directorio_salida,
        batch_size=batch_size,
        usar_cache=usar_cache,
        max_edad_cache_horas=max_edad_cache_horas
    )
    
    # Resumen final
    print("\n" + "=" * 70)
    print("📊 RESUMEN FINAL")
    print("=" * 70)
    print(f"   ✅ Tickers exitosos: {len(resultado['exitosos'])}")
    
    if usar_cache:
        if 'tickers_en_cache' in resultado:
            print(f"      • Del caché: {len(resultado['tickers_en_cache'])}")
        if 'tickers_descargados' in resultado:
            print(f"      • Descargados ahora: {len(resultado['tickers_descargados'])}")
    
    print(f"   ❌ Tickers fallidos: {len(resultado['fallidos'])}")
    
    if resultado.get('desde_cache', False):
        print(f"\n   💡 Todos los datos provienen del caché (no se descargó nada)")
    
    if resultado['fallidos']:
        print(f"\n   ⚠️ Tickers fallidos (primeros 10):")
        for ticker in resultado['fallidos'][:10]:
            error = resultado['errores'].get(ticker, 'Error desconocido')
            print(f"      • {ticker}: {error[:80]}")
    
    # ========================================================================
    # PASO 5: Exportar a JSON (formato requerido por HTML)
    # ========================================================================
    print("\n" + "=" * 70)
    print("📤 EXPORTANDO A JSON")
    print("=" * 70)
    
    # Cargar datos completos desde el caché para exportar
    df_completo_para_json, _ = cargar_cache(periodo, intervalo, directorio_salida)
    
    if df_completo_para_json is not None and not df_completo_para_json.empty:
        output_json = Path(directorio_salida) / 'series_historicas.json'
        exito_exportacion = exportar_a_json(
            df_completo_para_json,
            periodo=periodo,
            intervalo=intervalo,
            output_file=str(output_json)
        )
        
        if exito_exportacion:
            print(f"\n💡 El archivo JSON está listo para usar en el HTML:")
            print(f"   {output_json.absolute()}")
    else:
        print("⚠️ No se pudo cargar datos para exportar a JSON")
    
    print("\n✅ Proceso completado!")
    print(f"   Los datos se guardaron en: {directorio_salida}/")
    
    if usar_cache:
        # Verificar ambos formatos posibles
        cache_file_parquet = Path(directorio_salida) / obtener_nombre_cache(periodo, intervalo, usar_parquet=True)
        cache_file_csv = Path(directorio_salida) / obtener_nombre_cache(periodo, intervalo, usar_parquet=False)
        
        if cache_file_parquet.exists():
            print(f"   💾 Caché actualizado: {cache_file_parquet.name}")
        elif cache_file_csv.exists():
            print(f"   💾 Caché actualizado: {cache_file_csv.name}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)