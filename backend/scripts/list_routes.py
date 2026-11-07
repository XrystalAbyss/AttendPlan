import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app
for route in app.routes:
    if hasattr(route, 'path'):
        methods = getattr(route, 'methods', None)
        print(f"{methods} {route.path}")
