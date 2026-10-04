import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.graph import run_graph
from app.github.demo_files import DEMO_FILES

# Build a fake diff from the demo files (no GitHub needed)
parts = []
for name, code in DEMO_FILES.items():
    added = "\n".join("+" + line for line in code.splitlines())
    parts.append(f"--- file: review_demo/{name}\n@@ -0,0 +1,{len(code.splitlines())} @@\n{added}")
diff = "\n\n".join(parts)

result = run_graph({"diff": diff, "errors": []})

print("VERDICT:", result["final_verdict"])
print("COUNTS:", result["counts"])
print("SUMMARY:", result["review_summary"])
print("ERRORS:", result.get("errors"))
print()
for f in result["all_findings"]:
    print(f"[{f['severity'].upper()}] ({f['category']}) {f['file']} line {f['line']}: {f['title']}")
    print("   why:", f["explanation"])
    print("   fix:", f["fix"])
