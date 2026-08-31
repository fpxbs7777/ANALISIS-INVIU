#!/usr/bin/env python3
"""Extract tickers and their vencimientos from the bonds file."""

with open('titulos publicos.txt', 'r', encoding='utf-8') as f:
    lines = [line.strip() for line in f.readlines()]

# Known section headers to identify categories
sections = {
    'Soberano CER': ['S30A6', 'S15Y6', 'S29Y6', 'TTJ26', 'T30J6', 'S17L6', 'S31L6', 'S14G6', 'S31G6', 'TTS26', 'S30S6', 'TO26', 'S30O6', 'S30N6', 'TTD26', 'T15E7', 'T30A7', 'T31Y7', 'T30J7', 'TY30P'],
    'Soberano Dólar Linked': ['X15Y6', 'X29Y6', 'TZX26', 'X31L6', 'TX26', 'X30S6', 'TZXO6', 'X30N6', 'TZXD6', 'TZXM7', 'TZXA7', 'TZXY7', 'TZX27', 'TX28', 'TZXS7', 'TZXD7', 'TZX28', 'TZXS8', 'TZXM9', 'TX31', 'DICP'],
    'Soberano Tamar': ['M30A6', 'M31G6', 'TMF27', 'TMF28'],
    'Soberano Badlar': ['PR17'],
    'Soberano Globales/Bonares': ['TVPP', 'TVPY', 'AO27', 'AL29', 'GD29', 'AL30', 'GD30', 'AO28', 'AN29', 'AE38', 'GD38', 'AL35', 'GD35', 'AL41', 'GD41', 'GD46'],
    'Soberano Bopreal/BCRA': ['BPOB7', 'BPY26', 'BPOC7', 'BPOD7', 'BPOA7', 'BPOB8', 'BPOA8'],
}

# Ticker pattern: alphanumeric, typically 4-6 chars
import re

def looks_like_ticker(s):
    """Check if string looks like a bond ticker."""
    if not s or len(s) < 3 or len(s) > 8:
        return False
    # Tickers are alphanumeric, often ending with numbers
    return bool(re.match(r'^[A-Z0-9]+$', s)) and any(c.isdigit() for c in s)

def looks_like_date(s):
    """Check if string looks like DD/MM/YYYY date."""
    return bool(re.match(r'^\d{2}/\d{2}/\d{4}$', s))

# Find all tickers and their positions
results = []
i = 0
while i < len(lines):
    line = lines[i]
    # Skip empty lines
    if not line:
        i += 1
        continue
    
    # Check if this line and next few lines form a bond entry
    if looks_like_ticker(line):
        ticker = line
        # Look ahead for vencimiento (date in format DD/MM/YYYY)
        # The vencimiento usually appears after the "Vto" header
        vto = None
        j = i
        while j < min(i + 25, len(lines)):
            if looks_like_date(lines[j]):
                potential_date = lines[j]
                # Verify this is likely a vencimiento by checking context
                # Look backwards for "Vto" within the last 10 lines
                for k in range(max(j-10, i), j):
                    if lines[k] == 'Vto':
                        vto = potential_date
                        break
                if vto:
                    break
            j += 1
        
        if vto:
            results.append((ticker, vto))
            i = j + 1
            continue
    
    i += 1

# Print results grouped by section
print("# Tickers clasificados por categoría con vencimiento\n")

for section_name, section_tickers in sections.items():
    print(f"\n## {section_name}")
    for ticker, vto in results:
        if ticker in section_tickers:
            print(f"{ticker} - Vto: {vto}")

# Print all found tickers for debugging
print("\n\n# ALL FOUND TICKERS:")
for ticker, vto in results:
    print(f"{ticker} - {vto}")
