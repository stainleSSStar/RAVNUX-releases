"""Production probes must fail honestly and the monitor must frame replies correctly."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

vmi = module('production_install', 'vm-install.py')
qmp = module('production_qmp', 'vm-qmp.py')


class ProductionProbes(unittest.TestCase):
    def test_disk_controllers(self):
        for bus, expected in [('virtio', 'if=virtio'), ('sata', 'ide-hd,drive=systemdisk,bus=sata.0'),
                              ('nvme', 'nvme,drive=systemdisk,serial=RAVNUX-CI')]:
            command = vmi.qemu_command('/test/disk', '/test/socket', disk_bus=bus)
            self.assertIn(expected, ' '.join(command))
        with self.assertRaises(ValueError):
            vmi.qemu_command('/test/disk', '/test/socket', disk_bus='invalid')

    def test_audio_probe_requires_every_service(self):
        script = vmi.vm_smoke.PRODUCTION_DESKTOP_CHECKS
        # A PulseAudio client must be started before checking socket-activated services.
        self.assertLess(script.index('pavucontrol'), script.index('systemctl --user'))
        mocks = """wpctl() { :; }
pgrep() { echo 1; }
pavucontrol() { sleep 5; }
sleep() { :; }
systemctl() { case "$*" in *wireplumber*) return 1;; *) return 0;; esac; }
"""
        result = subprocess.run(['bash', '-ec', mocks + script], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_all_guest_scripts_parse(self):
        for body in (vmi.MANUAL_GREETER, vmi.GRAPHICAL_VERIFY, vmi.ROOT_PRODUCTION_CHECKS,
                     vmi.vm_smoke.guest_script(True), vmi.window_probe('polkit'), vmi.user_probe('false', 'NEVER_PASS')):
            result = subprocess.run(['bash', '-n'], input=body, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_window_probe_waits_for_the_requested_application(self):
        mocks = """xprop() { if [[ $1 == -root ]]; then echo 'WINDOW: 0x123, 0x0'; else echo 'WM_CLASS = xfce4-terminal'; fi; }
sleep() { :; }
"""
        for pattern, code in [('xfce4-terminal', 0), ('polkit', 1)]:
            result = subprocess.run(['bash', '-ec', mocks + vmi.window_probe(pattern)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, code, result.stderr)

    def test_probe_never_passes_after_failure(self):
        result = subprocess.run(['bash', '-c', vmi.user_probe('false', 'NEVER_PASS')],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('\nRAVNUX_VM_FAIL\n', result.stdout)
        self.assertNotIn('NEVER_PASS', result.stdout)

    def test_probe_preserves_literal_shell_metacharacters(self):
        result = subprocess.run(['bash', '-c', vmi.user_probe('test "a; $" = "a; $"', 'PROBE_OK')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('\nPROBE_OK\n', result.stdout)

    def test_busy_mount_cannot_pass_via_lazy_unmount(self):
        mocks = '''umount() { echo "UNMOUNT $*"; case "$1" in -Rl) return 0;; *) return 1;; esac; }
sync() { :; }
grep() { return 1; }
poweroff() { echo POWERED_OFF; }
'''
        result = subprocess.run(['bash', '-c', mocks + vmi.POWER_OFF], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('UMOUNTED', result.stdout)
        self.assertNotIn('POWERED_OFF', result.stdout)
        self.assertNotIn('UNMOUNT -Rl', result.stdout)
        self.assertIn('RAVNUX_VM_FAIL', result.stdout)

    def test_serial_connect_timeout_terminates_qemu_and_closes_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            process = Mock()
            process.poll.return_value = None
            connection = Mock()
            with patch.object(vmi.subprocess, 'Popen', return_value=process), \
                 patch.object(vmi.socket, 'socket', return_value=connection):
                with self.assertRaisesRegex(RuntimeError, 'never appeared'):
                    vmi.start_vm(['qemu-test'], Path(directory) / 'serial.sock',
                                 Path(directory) / 'qemu.log', timeout=-1)
            connection.close.assert_called_once()
            process.terminate.assert_called_once()
            process.wait.assert_called_once_with(timeout=10)


class QMPFraming(unittest.TestCase):
    def client(self, chunks):
        connection = Mock()
        connection.recv.side_effect = chunks
        with patch.object(qmp.socket, 'socket', return_value=connection):
            client = qmp.QMPClient('/test/monitor')
        self.addCleanup(client.close)
        return client, connection

    def test_split_greeting_events_and_multiple_responses(self):
        client, connection = self.client([
            b'{"QM', b'P":{}}\r\n{"event":"READY"}\r\n{"return":{},"id":1}\r\n',
            b'{"event":"RESET"}\r\n{"return":{"status":"running"},"id":2}\r\n'])
        self.assertEqual(client.command('query-status'), {'status': 'running'})
        sent = [json.loads(call.args[0]) for call in connection.sendall.call_args_list]
        self.assertEqual([item['execute'] for item in sent], ['qmp_capabilities', 'query-status'])

    def test_command_error_is_not_success(self):
        client, _ = self.client([b'{"QMP":{}}\n{"return":{},"id":1}\n',
                                b'{"error":{"desc":"bad command"},"id":2}\n'])
        with self.assertRaisesRegex(RuntimeError, 'bad command'):
            client.command('invalid')

    def test_greeting_failure_closes_socket(self):
        connection = Mock()
        connection.recv.return_value = b''
        with patch.object(qmp.socket, 'socket', return_value=connection):
            with self.assertRaisesRegex(RuntimeError, 'closed'):
                qmp.QMPClient('/test/monitor')
        connection.close.assert_called_once()

    def test_keyboard_quotes_and_shift_are_explicit(self):
        client = qmp.QMPClient.__new__(qmp.QMPClient)
        client.press = Mock()
        client.type_text('aA_ /\n')
        self.assertEqual([call.args for call in client.press.call_args_list],
                         [('a',), ('shift', 'a'), ('shift', 'minus'), ('spc',), ('slash',), ('ret',)])
        with self.assertRaises(ValueError):
            client.type_text('ą')
