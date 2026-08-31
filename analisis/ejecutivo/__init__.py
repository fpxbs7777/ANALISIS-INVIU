# -*- coding: utf-8 -*-
"""analisis.ejecutivo: herramientas para analisis rapido diario y decision.

- MurphyDaily: corre todos (o una seleccion) de los capitulos del libro.
- generar_informe_decision: genera DECISION_INVERSION.md.

Nota: no importamos decision/diario aqui para evitar imports circulares
al ejecutar modulos como scripts.
"""

__all__ = ["MurphyDaily", "generar_informe_decision"]