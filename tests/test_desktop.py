"""Regression tests for first-login wallpaper setup without an X server."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DesktopInitialization(unittest.TestCase):
    def run_desktop(self, existing=None, fail=False, initialized=False):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            wallpaper = tmp / 'city.jpg'
            wallpaper.touch()
            state = tmp / 'state.json'
            state.write_text(json.dumps(existing or {}))
            marker = tmp / '.config/ravnux/wallpaper-initialized'
            if initialized:
                marker.parent.mkdir(parents=True)
                marker.touch()
            query = tmp / 'xfconf-query'
            query.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
p = Path(os.environ['TEST_STATE'])
a = sys.argv[1:]
if os.environ.get('TEST_FAIL') == '1':
    sys.exit(1)
s = json.loads(p.read_text())
if '-l' in a:
    print('\\n'.join(s))
else:
    key = a[a.index('-p') + 1]
    if '-s' in a:
        s[key] = a[a.index('-s') + 1]
        p.write_text(json.dumps(s))
    else:
        print(s[key])
''')
            query.chmod(0o755)
            xrandr = tmp / 'xrandr'
            xrandr.write_text('''#!/bin/sh
printf '%s\\n' 'Screen 0: minimum 8 x 8, current 3840 x 1080, maximum 32767 x 32767' 'eDP-1 connected primary 1920x1080+0+0' 'HDMI-1 connected 1920x1080+1920+0' 'DP-1 disconnected'
''')
            xrandr.chmod(0o755)
            sleep = tmp / 'sleep'
            sleep.write_text('#!/bin/sh\nexit 0\n')
            sleep.chmod(0o755)
            script = (ROOT / 'overlay/common/usr/local/bin/ravnux-desktop').read_text()
            script = script.replace('/usr/share/backgrounds/ravnux/cyberpunk-city.jpg', str(wallpaper))
            result = subprocess.run(['bash'], input=script, text=True, capture_output=True,
                                    env=dict(os.environ, HOME=str(tmp), TEST_STATE=str(state),
                                             TEST_FAIL=str(int(fail)), PATH=f'{tmp}:' + os.environ['PATH']))
            return result, json.loads(state.read_text()), marker.exists(), str(wallpaper)

    def test_fresh_profile_initializes_both_active_monitors(self):
        result, state, marked, wallpaper = self.run_desktop()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(marked)
        for connector in ('eDP-1', 'HDMI-1'):
            prefix = f'/backdrop/screen0/monitor{connector}/workspace0'
            self.assertEqual(state[prefix + '/last-image'], wallpaper)
            self.assertEqual(state[prefix + '/image-style'], '5')
        self.assertFalse(any('monitorDP-1/' in key for key in state))
        self.assertEqual(state['/backdrop/single-workspace-mode'], 'true')

    def test_replaces_xfce_default_created_before_first_login_helper(self):
        key = '/backdrop/screen0/monitoreDP-1/workspace0/last-image'
        result, state, marked, wallpaper = self.run_desktop({key: '/usr/share/backgrounds/xfce/xfce-blue.jpg'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state[key], wallpaper)
        self.assertEqual(state['/backdrop/single-workspace-mode'], 'true')
        self.assertTrue(marked)

    def test_preserves_user_wallpaper_and_workspace_preferences(self):
        key = '/backdrop/screen0/monitoreDP-1/workspace0/last-image'
        result, state, marked, _ = self.run_desktop({key: '/my/photo.jpg'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state[key], '/my/photo.jpg')
        self.assertNotIn('/backdrop/single-workspace-mode', state)
        self.assertTrue(marked)

    def test_failed_bus_does_not_mark_success(self):
        result, _, marked, _ = self.run_desktop(fail=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marked)
        self.assertIn('initialization failed', result.stderr)

    def test_large_property_list_preserves_user_wallpaper_and_workspace_mode(self):
        key = '/backdrop/screen0/monitoreDP-1/workspace0/last-image'
        existing = {key: '/my/photo.jpg', '/backdrop/single-workspace-mode': 'false'}
        existing.update({f'/other/settings/property-{i}': 'value' for i in range(10000)})
        result, state, marked, _ = self.run_desktop(existing)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state[key], '/my/photo.jpg')
        self.assertEqual(state['/backdrop/single-workspace-mode'], 'false')
        self.assertTrue(marked)

    def test_later_login_keeps_user_settings(self):
        existing = {'/backdrop/custom': 'unchanged'}
        result, state, _, _ = self.run_desktop(existing, initialized=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(state, existing)
