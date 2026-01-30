import subprocess, sys, os

subprocess.call([
    sys.executable,
    "-m", "streamlit", "run",
    os.path.join(os.path.dirname(__file__), "app.py"),
    "--server.headless=true"
])
