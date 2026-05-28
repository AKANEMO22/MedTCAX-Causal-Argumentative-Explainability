import json
import ast
from collections import defaultdict, deque

notebook_path = "c:/Users/hachimi/Documents/GitHub/causal_argumentation_remake_DAP301m/causal_argumentation-main/causal_arg_with_tier.ipynb"

with open(notebook_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Extract code cells
code_cells = []
for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        code_cells.append("".join(cell.get("source", [])))

full_code = "\n".join(code_cells)

class DeepCallAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.defined_functions = set()
        self.call_graph = defaultdict(set) # func -> set of funcs it calls
        self.module_calls = set()
        self.current_scope = [] # stack of function names

    def visit_FunctionDef(self, node):
        self.defined_functions.add(node.name)
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def record_usage(self, name):
        if self.current_scope:
            self.call_graph[self.current_scope[-1]].add(name)
        else:
            self.module_calls.add(name)

    def visit_Name(self, node):
        self.record_usage(node.id)
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        self.record_usage(node.attr)
        self.generic_visit(node)

try:
    tree = ast.parse(full_code)
    analyzer = DeepCallAnalyzer()
    analyzer.visit(tree)
    
    # Reachability analysis (BFS)
    reachable = set()
    queue = deque(analyzer.module_calls)
    
    while queue:
        curr = queue.popleft()
        if curr in analyzer.defined_functions and curr not in reachable:
            reachable.add(curr)
            # Add all functions called by this function to the queue
            for neighbor in analyzer.call_graph[curr]:
                queue.append(neighbor)
                
    # Also find functions that are technically used by other functions, but the parent is dead code
    all_defined = analyzer.defined_functions
    dead_functions = all_defined - reachable
    
    print("--- DEEP ANALYSIS RESULTS ---")
    print(f"Total defined functions: {len(all_defined)}")
    print(f"Reachable functions from main execution path: {len(reachable)}")
    print(f"Dead functions (defined but NEVER reached in execution):")
    
    # Let's categorize the dead functions:
    # 1. Literally no references anywhere
    # 2. Referenced, but only inside other dead functions
    
    literally_no_refs = []
    dead_but_referenced_in_dead_code = []
    
    all_refs = set(analyzer.module_calls)
    for caller, callees in analyzer.call_graph.items():
        all_refs.update(callees)
        
    for fn in sorted(dead_functions):
        if fn not in all_refs:
            literally_no_refs.append(fn)
        else:
            dead_but_referenced_in_dead_code.append(fn)
            
    print("\n1. COMPLETELY UNREFERENCED:")
    for fn in literally_no_refs:
        print(f"  - {fn}")
        
    print("\n2. UNREACHABLE (Dead code - only called by other unused functions, or unused entirely):")
    for fn in dead_but_referenced_in_dead_code:
        print(f"  - {fn}")

except Exception as e:
    print(f"Error parsing code: {e}")
