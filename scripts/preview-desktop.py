#!/usr/bin/env python3
"""Render the shipped XFCE/GTK3 theme with real widgets, panel and terminal in Xvfb.

Development-only: dbus-run-session -- xvfb-run -s '-screen 0 1440x900x24' \
    python3 scripts/preview-desktop.py --output ci-logs/desktop.png
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
output = args.output.resolve()
output.parent.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parents[1]
common = root / 'overlay/common'

with tempfile.TemporaryDirectory(prefix='ravnux-preview-') as directory:
    home = Path(directory)
    shutil.copytree(common / 'etc/skel', home, dirs_exist_ok=True)
    (home / '.themes').mkdir()
    (home / '.themes/RAVNUX').symlink_to(common / 'usr/share/themes/RAVNUX')
    config = home / '.config/xfce4/xfconf/xfce-perchannel-xml'
    for path in config.glob('*.xml'):
        path.write_text(path.read_text().replace('/usr/share/pixmaps/ravnux-logo.png',
                       str(common / 'usr/share/pixmaps/ravnux-logo.png')))
    (home / 'Documents').mkdir()
    (home / 'Documents/Welcome.txt').write_text('RAVNUX — minimal XFCE desktop\n')
    os.environ.update(HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
                      XDG_CACHE_HOME=str(home / '.cache'), GTK_THEME='RAVNUX')
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gdk, GLib, Gtk

    errors = []
    for path in (common / 'usr/share/themes/RAVNUX').glob('*/gtk.css'):
        if path.parent.name == 'gtk-4.0':
            continue
        provider = Gtk.CssProvider()
        provider.connect('parsing-error', lambda provider, section, error: errors.append(str(error)))
        provider.load_from_path(str(path))
    if errors:
        raise RuntimeError('Theme CSS errors: ' + '; '.join(errors))

    children = []
    with output.with_suffix('.log').open('w') as log:
        def launch(*command):
            process = subprocess.Popen(command, stdout=log, stderr=log)
            children.append(process)
            return process

        launch('xfsettingsd', '--no-daemon')
        launch('xfwm4', '--compositor=on')
        launch('xfce4-panel', '--disable-wm-check')
        launch('xfdesktop', '--disable-wm-check')
        # Set a backdrop using xfdesktop's connector name once its channel exists.
        def start_apps():
            for prop in ('/backdrop/screen0/monitor0/workspace0',
                         '/backdrop/screen0/monitorscreen/workspace0'):
                subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-p', prop + '/last-image',
                                '-n', '-t', 'string', '-s', str(common / 'usr/share/backgrounds/ravnux/cyberpunk-city.jpg')], check=True)
            launch('thunar', str(home / 'Documents'))
            launch('xfce4-terminal', '--disable-server', '--geometry=88x25+610+80',
                   '--title=RAVNUX Terminal', '--hide-menubar', '--command',
                   'fish -i -c "printf \'RAVNUX  •  XFCE / XLibre\\n\\n\'; '
                   'printf \'Green text, purple glass.\\n\\n\'; '
                   'printf \'\\e[35m❯ \\e[32mwpctl status\\e[0m\\nAudio: PipeWire + WirePlumber\\n\\n\'; '
                   'printf \'\\e[35m❯ \\e[32mls ~/Documents\\e[0m\\nWelcome.txt\\n\\n\'; read -P \'❯ \'"')
            launch('notify-send', '-t', '30000', 'RAVNUX', 'One palette. A minimal desktop.')
            return False
        GLib.timeout_add(2500, start_apps)

        window = Gtk.Window(title='RAVNUX Appearance')
        window.set_default_size(720, 235)
        window.move(610, 570)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_border_width(20)
        window.add(box)
        label = Gtk.Label(label='RAVNUX  /  Purple & pink', xalign=0)
        box.pack_start(label, False, False, 0)
        entry = Gtk.Entry(text='Consistent colors across the desktop')
        box.pack_start(entry, False, False, 0)
        row = Gtk.Box(spacing=12)
        for title in ('Normal', 'Selected', 'Disabled'):
            button = Gtk.ToggleButton(label=title)
            button.set_active(title == 'Selected')
            button.set_sensitive(title != 'Disabled')
            row.pack_start(button, False, False, 0)
        row.pack_start(Gtk.CheckButton(label='Compositor enabled', active=True), False, False, 0)
        box.pack_start(row, False, False, 0)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_value(72)
        scale.set_draw_value(False)
        box.pack_start(scale, False, False, 0)
        window.show_all()

        def arrange():
            subprocess.run(['wmctrl', '-r', 'Documents', '-e', '0,30,80,540,620'], check=True)
            window.present()
            return False
        GLib.timeout_add(6500, arrange)
        result = []
        def capture():
            display = Gdk.get_default_root_window()
            shot = Gdk.pixbuf_get_from_window(display, 0, 0, display.get_width(), display.get_height())
            shot.savev(str(output), 'png', [], [])
            result.append(True)
            Gtk.main_quit()
            return False
        GLib.timeout_add(10000, capture)
        try:
            Gtk.main()
            if not result:
                raise RuntimeError('Screenshot was not captured')
        finally:
            for process in children:
                process.terminate()
            for process in children:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
