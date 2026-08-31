import re
with open('backtest-slides.html','r',encoding='utf-8') as f:
    c = f.read()

checks = {
    'DOCTYPE': '<!DOCTYPE html>' in c,
    'html close': '</html>' in c,
    'body close': '</body>' in c,
    'No broken tags': '<///' not in c,
    'No double body': c.count('</body>') == 1,
    'No double html': c.count('</html>') == 1,
}

slides = re.findall(r'id="s(\d+)"', c)
slide_ids = sorted([int(s) for s in slides])
checks['All slides 0-11'] = slide_ids == list(range(12))
checks['No duplicate ids'] = len(slides) == len(set(slides))

fstring_leftovers = re.findall(r'\$\{[^}]+\}', c)
checks['No f-string leftovers'] = len(fstring_leftovers) == 0

section_open = c.count('<section class=')
section_close = c.count('</section>')
checks['Section tags balanced'] = section_open == section_close

for check, result in checks.items():
    print(f'{"OK" if result else "FAIL"} {check}')

print(f'\nSlides: {slide_ids}')
print(f'Size: {len(c)} bytes, {c.count(chr(10))} lines')