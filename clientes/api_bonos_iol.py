from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import importlib.util
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import signal
import sys

# Importar el módulo de scraping dinámicamente debido al nombre con espacios
spec = importlib.util.spec_from_file_location("scraper", "scrapper datos tecnicos bonos iol.py")
scraper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper_module)
obtener_bono_completo = scraper_module.obtener_bono_completo

# Timeout para las solicitudes de scraping (en segundos)
SCRAPING_TIMEOUT = 30

app = FastAPI(
    title="API de Datos Técnicos de Bonos IOL",
    description="API local para obtener datos técnicos de bonos desde InvertirOnline",
    version="1.0.0"
)

# Modelo para los parámetros de solicitud
class BonoRequest(BaseModel):
    mercado: str
    simbolo: str

class BonosRequest(BaseModel):
    bonos: List[dict]  # Lista de dicts con "mercado" y "simbolo"

# Executor para ejecutar tareas síncronas en un thread pool
executor = ThreadPoolExecutor(max_workers=2)

@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "mensaje": "API de Datos Técnicos de Bonos IOL",
        "version": "1.0.0",
        "endpoints": {
            "datos_tecnicos": "/api/v1/datos-tecnicos (POST)",
            "salud": "/health (GET)"
        }
    }

@app.get("/health")
async def health():
    """Endpoint de verificación de salud"""
    return {"status": "ok", "servicio": "API Bonos IOL"}

@app.post("/api/v1/datos-tecnicos")
async def obtener_datos_tecnicos(request: BonoRequest):
    """
    Obtiene los datos técnicos de un bono desde IOL.
    
    Parámetros:
    - mercado: Código del mercado (ej: BCBA)
    - simbolo: Símbolo del título (ej: AL30)
    
    Retorna:
    - JSON con los datos técnicos del bono (incluye tasas y amortizaciones)
    """
    try:
        # Ejecutar la función de scraping en un thread pool con timeout
        loop = asyncio.get_event_loop()
        datos = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                obtener_bono_completo,
                request.mercado,
                request.simbolo,
                None,  # codigo_isin
                0  # dias_cache (sin cache para datos frescos)
            ),
            timeout=SCRAPING_TIMEOUT
        )
        
        if "error" in datos:
            raise HTTPException(status_code=500, detail=datos["error"])
        
        return {
            "status": "success",
            "data": datos,
            "metadata": {
                "mercado": request.mercado,
                "simbolo": request.simbolo
            }
        }
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Timeout: La solicitud de scraping excedió el tiempo límite")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/api/v1/datos-tecnicos/{mercado}/{simbolo}")
async def obtener_datos_tecnicos_get(mercado: str, simbolo: str):
    """
    Obtiene los datos técnicos de un bono usando parámetros de ruta (GET).
    
    Parámetros de ruta:
    - mercado: Código del mercado (ej: BCBA)
    - simbolo: Símbolo del título (ej: AL30)
    
    Retorna:
    - JSON con los datos técnicos del bono
    """
    try:
        loop = asyncio.get_event_loop()
        datos = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                obtener_bono_completo,
                mercado,
                simbolo,
                None,  # codigo_isin
                0  # dias_cache
            ),
            timeout=SCRAPING_TIMEOUT
        )
        
        if "error" in datos:
            raise HTTPException(status_code=500, detail=datos["error"])
        
        return {
            "status": "success",
            "data": datos,
            "metadata": {
                "mercado": mercado,
                "simbolo": simbolo
            }
        }
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Timeout: La solicitud de scraping excedió el tiempo límite")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/api/v1/datos-tecnicos/multiple")
async def obtener_datos_tecnicos_multiple(request: BonosRequest):
    """
    Obtiene los datos técnicos de múltiples bonos desde IOL.
    
    Parámetros:
    - bonos: Lista de dicts con "mercado" y "simbolo"
    
    Ejemplo:
    {
        "bonos": [
            {"mercado": "BCBA", "simbolo": "AL30"},
            {"mercado": "BCBA", "simbolo": "AE38"}
        ]
    }
    
    Retorna:
    - JSON con los datos técnicos de todos los bonos
    """
    try:
        resultados = {}
        errores = []
        
        for bono in request.bonos:
            mercado = bono.get("mercado")
            simbolo = bono.get("simbolo")
            
            if not mercado or not simbolo:
                errores.append(f"Datos inválidos para bono: {bono}")
                continue
            
            try:
                loop = asyncio.get_event_loop()
                datos = await asyncio.wait_for(
                    loop.run_in_executor(
                        executor,
                        obtener_bono_completo,
                        mercado,
                        simbolo,
                        None,  # codigo_isin
                        0  # dias_cache
                    ),
                    timeout=SCRAPING_TIMEOUT
                )
                
                if "error" in datos:
                    errores.append(f"{simbolo}: {datos['error']}")
                else:
                    resultados[simbolo] = datos
                    
            except asyncio.TimeoutError:
                errores.append(f"{simbolo}: Timeout")
            except Exception as e:
                errores.append(f"{simbolo}: {str(e)}")
        
        return {
            "status": "success",
            "data": resultados,
            "errores": errores,
            "metadata": {
                "total_bonos": len(request.bonos),
                "exitosos": len(resultados),
                "fallidos": len(errores)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
