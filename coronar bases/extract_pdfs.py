#!/usr/bin/env python3
"""
Extract text from all PDFs in the 'coronar bases' directory,
organize by topic / category, and write a single TXT file.
"""

import os
import sys
import fitz  # PyMuPDF
import re
from pathlib import Path

BASE_DIR = Path(r"c:/Users/boosa/Desktop/clarity-dashboard-main (5)/clarity-dashboard-main (2)/clarity-dashboard-main (6)/clarity-dashboard-main6/coronar bases")
OUTPUT_FILE = BASE_DIR / "EXTRACCION_COMPLETA_PAPERS.txt"

# ── Category mapping ────────────────────────────────────────────────
# Each entry: (path_glob_or_substring, display_category_name)
# Order matters — first match wins.

CATEGORIES = [
    # ── Root-level PDFs ──
    (lambda p: "Contabilidad-y-Finanzas-para-Dummies" in p.name,
     "CONTABILIDAD Y FINANZAS GENERALES"),
    (lambda p: "NeurocienciasenFinanzas" in p.name,
     "NEUROCIENCIAS EN FINANZAS"),
    (lambda p: "Perfil Inversor IOL" in p.name,
     "PERFIL DEL INVERSOR"),
    (lambda p: "SesindeEntrenamiento" in p.name,
     "ENTRENAMIENTO / TRADING PSICOLÓGICO"),
    (lambda p: "Tacticasparaveroportunidades" in p.name,
     "TÁCTICAS DE OPORTUNIDADES DE MERCADO"),
    (lambda p: "TcnicasparaProspectar" in p.name,
     "TÉCNICAS DE PROSPECCIÓN"),
    (lambda p: "ValueInvesting" in p.name,
     "VALUE INVESTING"),
    (lambda p: "intermarket-analysis" in p.name,
     "ANÁLISIS INTERMARKET (John Murphy)"),

    # ── labadie/arbitraje estadistico ──
    (lambda p: "arbitraje estadistico" in str(p) and "HIGH FREQUENCY TRADING" in p.name,
     "ARBITRAJE ESTADÍSTICO — HIGH FREQUENCY TRADING"),
    (lambda p: "arbitraje estadistico" in str(p) and "spectral_theory" in p.name,
     "ARBITRAJE ESTADÍSTICO — TEORÍA ESPECTRAL"),
    (lambda p: "arbitraje estadistico" in str(p) and "statarb" in p.name,
     "ARBITRAJE ESTADÍSTICO — LECTURES"),

    # ── labadie/opciones ──
    (lambda p: "opciones" in str(p) and "black-scholes" in p.name,
     "OPCIONES — BLACK-SCHOLES"),
    (lambda p: "opciones" in str(p) and "stochastic" in p.name,
     "OPCIONES — PROCESOS ESTOCÁSTICOS"),

    # ── labadie/trading ──
    (lambda p: "trading" in str(p) and "market-making" in p.name and "inventory" in p.name,
     "TRADING — MARKET MAKING CON RESTRICCIONES DE INVENTARIO"),
    (lambda p: "trading" in str(p) and "market-making" in p.name,
     "TRADING — HIGH-FREQUENCY MARKET MAKING"),
    (lambda p: "trading" in str(p) and "Optimal starting times" in p.name,
     "TRADING — TIEMPOS ÓPTIMOS Y MEDIDAS DE RIESGO"),

    # ── labadie/ — general academic papers ──
    (lambda p: "1205.3482v6" in p.name,
     "LABADIE — PAPER ACADÉMICO (ID 1205.3482)"),
    (lambda p: "1303.7177v2" in p.name,
     "LABADIE — PAPER ACADÉMICO (ID 1303.7177)"),
    (lambda p: "ssrn-4053924" in p.name,
     "LABADIE — SSRN 4053924"),
    (lambda p: "machine_learning_v4" in p.name,
     "LABADIE — MACHINE LEARNING EN FINANZAS"),
    (lambda p: "electronic-trading" in p.name,
     "LABADIE — ELECTRONIC TRADING"),
    (lambda p: "financial-zoology" in p.name,
     "LABADIE — FINANCIAL ZOOLOGY / HEDGE FUNDS"),
    (lambda p: "high-frequency-trading" in p.name and "lectures" not in p.name,
     "LABADIE — HIGH FREQUENCY TRADING"),
    (lambda p: "lectures_2016_algo_trading" in p.name,
     "LABADIE — ALGORITHMIC TRADING (Lectures 2016)"),
    (lambda p: "lectures_2016_statarb" in p.name,
     "LABADIE — STATISTICAL ARBITRAGE (Lectures 2016)"),
    (lambda p: "lectures_2017_unam_etf" in p.name,
     "LABADIE — ETFs (UNAM 2017)"),
    (lambda p: "lectures_2017_unam_hft" in p.name,
     "LABADIE — HFT (UNAM 2017)"),
    (lambda p: "lectures_2017_unam_zoology" in p.name,
     "LABADIE — FINANCIAL ZOOLOGY (UNAM 2017)"),
    (lambda p: "lectures_2021_statarb" in p.name,
     "LABADIE — STATISTICAL ARBITRAGE (Lectures 2021)"),
    (lambda p: "market-microstructure" in p.name,
     "LABADIE — MICROESTRUCTURA DE MERCADO"),
    (lambda p: "memoire_master" in p.name,
     "LABADIE — TESIS / MÉMOIRE MASTER"),
    (lambda p: "optimisation_problems" in p.name,
     "LABADIE — OPTIMISATION PROBLEMS"),
    (lambda p: "seminario_geometry" in p.name,
     "LABADIE — GEOMETRÍA EN PORTAFOLIOS DE INVERSIÓN"),
]


def extract_text(pdf_path: Path) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    text_pages = []
    try:
        doc = fitz.open(pdf_path)
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text()
            if page_text and page_text.strip():
                text_pages.append(f"[Página {page_num}]\n{page_text.strip()}")
        doc.close()
        return "\n\n".join(text_pages)
    except Exception as e:
        return f"[ERROR AL EXTRAER: {e}]"


def get_category(pdf_path: Path) -> str:
    """Return the category label for a given PDF path."""
    for matcher, label in CATEGORIES:
        if matcher(pdf_path):
            return label
    # Fallback based on directory
    parent_dir = pdf_path.parent.name
    if parent_dir == "labadie":
        return "LABADIE — OTROS"
    elif parent_dir == "arbitraje estadistico":
        return "ARBITRAJE ESTADÍSTICO — OTROS"
    elif parent_dir == "opciones":
        return "OPCIONES — OTROS"
    elif parent_dir == "trading":
        return "TRADING — OTROS"
    return "OTROS / SIN CLASIFICAR"


def human_readable_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes/1024**2:.1f} MB"


def main():
    # Find all PDFs recursively
    pdf_files = sorted(BASE_DIR.rglob("*.pdf"))
    print(f"Encontrados {len(pdf_files)} archivos PDF.")

    # Group by category
    grouped: dict[str, list[Path]] = {}
    for pdf_path in pdf_files:
        cat = get_category(pdf_path)
        grouped.setdefault(cat, []).append(pdf_path)

    total_chars = 0
    total_pages = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("═" * 72 + "\n")
        out.write("  EXTRACCIÓN COMPLETA DE PAPERS — CLARITY DASHBOARD\n")
        out.write(f"  Generado: 2026-07-25\n")
        out.write(f"  Total PDFs: {len(pdf_files)}\n")
        out.write("═" * 72 + "\n\n")

        for cat_idx, (category, pdf_list) in enumerate(grouped.items(), start=1):
            header = f"  {'='*68}  \n"
            header += f"  CATEGORÍA {cat_idx}: {category}\n"
            header += f"  {'='*68}  \n"
            out.write(header)

            for pdf_path in pdf_list:
                rel_path = pdf_path.relative_to(BASE_DIR)
                file_size = human_readable_size(pdf_path.stat().st_size)

                out.write(f"\n{'─'*70}\n")
                out.write(f"  📄 ARCHIVO: {rel_path}\n")
                out.write(f"  💾 TAMAÑO : {file_size}\n")
                out.write(f"  {'─'*70}\n\n")

                text = extract_text(pdf_path)
                # Rough page count
                page_count = text.count("[Página ")
                total_pages += page_count

                # Truncate if absurdly long (more than ~50k chars per doc)
                if len(text) > 80000:
                    out.write(text[:80000])
                    out.write(f"\n\n[... TRUNCATED — el documento continúa pero se excede el límite de extracción. "
                              f"Total páginas extraídas: {page_count} / texto completo: {len(text)} caracteres]\n")
                else:
                    out.write(text)

                out.write(f"\n\n→ FIN DEL DOCUMENTO (páginas extraídas: {page_count})\n")
                out.write(f"{'─'*70}\n\n")

                total_chars += len(text)

                # Flush periodically
                out.flush()

            out.write("\n")

        # ── Summary ──
        out.write("═" * 72 + "\n")
        out.write("  RESUMEN FINAL\n")
        out.write("═" * 72 + "\n")
        out.write(f"  Total PDFs procesados : {len(pdf_files)}\n")
        out.write(f"  Total páginas extraídas (aproximado): {total_pages}\n")
        out.write(f"  Total caracteres extraídos: {total_chars:,}\n")
        out.write(f"  Categorías: {len(grouped)}\n\n")
        out.write("  DISTRIBUCIÓN POR CATEGORÍA:\n")
        for cat, pdf_list in grouped.items():
            out.write(f"    • {cat}: {len(pdf_list)} PDF(s)\n")
        out.write("\n═" * 72 + "\n")

    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\n✅ Archivo generado: {OUTPUT_FILE}")
    print(f"   Tamaño: {size_mb:.2f} MB")
    print(f"   PDFs procesados: {len(pdf_files)}")
    print(f"   Categorías: {len(grouped)}")
    for cat, pdf_list in sorted(grouped.items()):
        print(f"     • {cat}: {len(pdf_list)} PDF(s)")


if __name__ == "__main__":
    main()
