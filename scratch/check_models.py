import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    import models
    print(f"Firestore models loaded: {len([name for name in dir(models) if name[:1].isupper()])}")
except Exception as e:
    print(f"Error loading Firestore models: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
