# -*- coding: utf-8 -*-
"""analisis.libro: clases reutilizables para aplicar cada capitulo del libro
Intermarket Analysis de John J. Murphy al contexto actual.

Cada clase hereda de CapituloBase y expone:
  - datos: dict {clave: Serie} cargado por load()
  - resultados: dict con los hallazgos clave del capitulo
  - run(): carga datos + ejecuta analisis + devuelve resultados
  - texto(): imprime el analisis formateado (modo verbose)
"""
from .base import CapituloBase
from .capitulos import (
    Capitulo1, Capitulo2, Capitulo3, Capitulo4, Capitulo5, Capitulo6, Capitulo7,
    Capitulo8, Capitulo9, Capitulo10, Capitulo11, Capitulo12,
    Capitulo13, Capitulo14, Capitulo15,
)

__all__ = [
    "CapituloBase",
    "Capitulo1", "Capitulo2", "Capitulo3", "Capitulo4", "Capitulo5", "Capitulo6", "Capitulo7",
    "Capitulo8", "Capitulo9", "Capitulo10", "Capitulo11", "Capitulo12",
    "Capitulo13", "Capitulo14", "Capitulo15",
]