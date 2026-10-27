#!/usr/bin/env python3
"""Exercise focused-window polling through Fish against real XFCE/X11 (CI only)."""
import importlib.util
import re
from pathlib import Path
import subprocess
import time

spec = importlib.util.spec_from_file_location('vm_install', Path(__file__).with_name('vm-install.py'))
vmi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vmi)
processes = []
try:
    processes.append(subprocess.Popen(['xfwm4', '--compositor=off']))
    time.sleep(2)
    processes.append(subprocess.Popen(['xfce4-appfinder', '--collapsed', '--disable-server']))
    time.sleep(2)
    active = subprocess.check_output(['xprop', '-root', '_NET_ACTIVE_WINDOW'], text=True)
    print('Active property:', repr(active), flush=True)
    window = re.search(r'0x[0-9a-fA-F]+', active).group()
    print(subprocess.check_output(['xprop', '-id', window, 'WM_CLASS'], text=True), flush=True)
    # Preserve xvfb-run's DISPLAY and temporary XAUTHORITY for this host probe.
    body = vmi.window_probe('xfce4-appfinder').replace(
        'export DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority";', '')
    result = subprocess.run(['fish', '-c', vmi.user_probe(body, 'FOCUSED_WINDOW_OK')],
                            capture_output=True, text=True, timeout=55)
    print(result.stdout, result.stderr, flush=True)
    if result.returncode != 0 or '\nFOCUSED_WINDOW_OK\n' not in result.stdout:
        raise RuntimeError('Real XFCE focused-window probe failed through Fish')
finally:
    for process in reversed(processes):
        process.terminate()
        process.wait(timeout=10)
