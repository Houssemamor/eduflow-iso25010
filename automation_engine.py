"""Browser detection and CDP launch helpers for dashboard simulation.

Resolution order mirrors the requested pattern:
  1. CHROME_PATH environment variable (explicit override)
  2. Google Chrome (machine x86, machine x64, per-user)
  3. Microsoft Edge (machine x64, machine x86, per-user)
  4. Executables discoverable on PATH

The helpers are used by the local simulation test only. They are intentionally
not exposed through an HTTP endpoint: launching a process from a web request
would be a remote-code-execution risk.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

BROWSER_MISSING_MESSAGE = (
    "No supported browser found. Install Google Chrome or Microsoft Edge, "
    "or set CHROME_PATH to the browser executable."
)

CHROME_CANDIDATES = [
    os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
    os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

EDGE_CANDIDATES = [
    os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
]

CDP_PORT = 9222
CDP_ENDPOINT = f"http://127.0.0.1:{CDP_PORT}"


def _find_browser_path() -> str:
    """Return the first existing browser executable, or an empty string."""
    override = os.environ.get("CHROME_PATH")
    if override:
        return override if os.path.exists(override) else ""

    for candidate in [*CHROME_CANDIDATES, *EDGE_CANDIDATES]:
        if candidate and os.path.exists(candidate):
            return candidate

    for name in ("chrome", "google-chrome", "chromium", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    return ""


def _resolve_browser_path() -> str:
    """Named alias used by callers; keeps detection in one place."""
    return _find_browser_path()


def browser_args(user_data_dir: str) -> list[str]:
    """Launch flags, including CDP and the privacy flags from the brief."""
    return [
        f"--user-data-dir={user_data_dir}",
        f"--remote-debugging-port={CDP_PORT}",
        "--headless=new",
        "--no-first-run",
        "--no-default-browser-check",
        "--webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--enforce-webrtc-ip-permission-check",
        "--start-maximized",
        "about:blank",
    ]


def launch_cdp_browser(browser_path: str, user_data_dir: str, timeout: float = 20.0) -> subprocess.Popen:
    """Start the detected browser with CDP enabled and wait for the endpoint."""
    if not browser_path or not os.path.exists(browser_path):
        raise RuntimeError(BROWSER_MISSING_MESSAGE)
    profile = Path(user_data_dir)
    if profile.exists():
        shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)

    process = subprocess.Popen(
        [browser_path, *browser_args(str(profile))],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(f"{CDP_ENDPOINT}/json/version", timeout=1) as response:
                if response.status == 200:
                    return process
        except (URLError, OSError):
            time.sleep(0.3)
    process.terminate()
    raise RuntimeError("Browser CDP endpoint did not become ready")


def stop_browser(process: subprocess.Popen | None) -> None:
    """Terminate the launched browser and its child processes."""
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
