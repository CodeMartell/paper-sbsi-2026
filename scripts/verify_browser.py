"""Optional local end-to-end check. Requires installed Playwright Chromium."""
from dataclasses import replace
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.config import Settings
from src.pipeline import execute
from src.provenance import write_json
from playwright.sync_api import sync_playwright


def main():
    output = ROOT / "output" / "browser-verification" / uuid.uuid4().hex
    data = output / "data"
    shutil.copytree(ROOT / "data", data)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "gerp_fake_server")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    streamlit = None
    try:
        cfg = replace(Settings(), data_dir=data, output_dir=output, logs_dir=output / "logs", headless=True,
                      gerp_url=f"http://127.0.0.1:{server.server_port}/web/gerp_fake.html")
        folder, result = execute(cfg)
        assert result["sources"]["finance"]["mode"] == "current_extraction", result
        assert result["sources"]["finance"]["metadata"]["reference_basis"]
        assert len(result["operational"]) == 3
        assert result["state"] == "provisional"  # fixture period 2026-W34
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(os.environ, OUTPUT_DIR=str(output))
        with (output / "streamlit.log").open("w", encoding="utf-8") as log:
            streamlit = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "src/dashboard.py", f"--server.port={port}"],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            for _ in range(60):
                try:
                    with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(.25)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1050})
                page.goto(f"http://127.0.0.1:{port}")
                page.get_by_text("PROVISIONAL — relatório provisório.", exact=False).wait_for(timeout=20000)
                page.get_by_role("heading", name="Revisão humana", exact=True).wait_for()
                page.screenshot(path=str(output / "dashboard.png"), full_page=True)
                assert not page.locator('[data-testid="stException"]').count()
                browser.close()
        write_json(output / "verification.json", dict(extraction="passed", dashboard="passed", run_id=result["run_id"],
                                                       screenshot="dashboard.png"))
        print(output)
    finally:
        server.shutdown()
        server.server_close()
        if streamlit:
            streamlit.terminate()
            streamlit.wait(timeout=10)


if __name__ == "__main__":
    main()
