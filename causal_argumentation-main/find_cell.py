import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('simple_workflow.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Print cells 15-19 and 49-52 to see structure
for i in list(range(15, 20)) + list(range(48, 53)):
    cell = nb['cells'][i]
    src = ''.join(cell.get('source', []))
    # Show only first 400 chars
    preview = src[:400].replace('\n', '\n    ')
    print(f"\n{'='*60}")
    print(f"Cell {i} [{cell['cell_type']}]:")
    print(f"    {preview}")
    if len(src) > 400:
        print("    ...")
