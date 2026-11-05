import os
import sys
import time
import threading
import urllib.request
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
import main
from admin_portal import initialize_admin_and_notification_database

TEST_PORT = int(os.environ.get("SBDS_TEST_PORT", "8008"))
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

class UvicornServerThread(threading.Thread):
    def __init__(self, host="127.0.0.1", port=TEST_PORT):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        config = uvicorn.Config(
            app=main.app,
            host=self.host,
            port=self.port,
            log_level="error",
            access_log=False
        )
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

_global_server = None

def start_test_server(port: int = TEST_PORT, timeout: float = 10.0) -> str:
    global _global_server
    if _global_server is not None:
        return f"http://127.0.0.1:{port}"

    # Initialize SQLite databases
    main.initialize_auth_database()
    main.initialize_urgent_database()
    initialize_admin_and_notification_database()

    server = UvicornServerThread(port=port)
    server.start()
    _global_server = server

    # Poll until server is ready
    start_time = time.time()
    url = f"http://127.0.0.1:{port}/"
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    return f"http://127.0.0.1:{port}"
        except Exception:
            time.sleep(0.3)

    raise RuntimeError(f"Server on port {port} failed to start within {timeout} seconds.")

def stop_test_server():
    global _global_server
    if _global_server is not None:
        _global_server.stop()
        _global_server = None
        time.sleep(0.5)

