import os
import sys
import shutil
from pathlib import Path

# Add project root to sys.path so all imports (main, db, etc.) resolve properly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Mark environment as Vercel / Serverless
os.environ["VERCEL"] = "1"

# On Vercel, the file system is read-only except /tmp
TMP_DIR = Path("/tmp")
if TMP_DIR.exists():
    bundled_auth = ROOT_DIR / "auth.db"
    tmp_auth = TMP_DIR / "auth.db"
    if bundled_auth.exists() and not tmp_auth.exists():
        try:
            shutil.copy2(bundled_auth, tmp_auth)
        except Exception:
            pass

    bundled_urgent = ROOT_DIR / "urgent_requests.db"
    tmp_urgent = TMP_DIR / "urgent_requests.db"
    if bundled_urgent.exists() and not tmp_urgent.exists():
        try:
            shutil.copy2(bundled_urgent, tmp_urgent)
        except Exception:
            pass

# Import the FastAPI application
from main import app
