import base64
import json
import os
from pathlib import Path
import subprocess
import sysconfig
import tempfile
import unittest
from cursorsnapshot import Client, export_records, initialize, put_order
from test_workflow import KEY, record


class CLI(unittest.TestCase):
    def test_process_restart_and_registered_cli(self):
        console = Path(sysconfig.get_path('scripts'))/('cursorsnapshot.exe' if os.name == 'nt' else 'cursorsnapshot')
        with tempfile.TemporaryDirectory(prefix='cursor-cli-', dir=Path(__file__).parent) as folder:
            root = Path(folder); source, store, output = root/'source.sqlite', root/'store.sqlite', root/'export.sqlite'
            initialize(source, 'source'); initialize(store, 'manager')
            for i in range(1, 8):
                put_order(source, record(i))
            expected = sorted([record(i) for i in range(1, 8)], key=lambda r: r['order_id'])
            key_file = root/'lab-key.txt'; key_file.write_bytes(b'cskey_'+base64.urlsafe_b64encode(KEY))
            def serve(port):
                process = subprocess.Popen([str(console), 'serve', '--source', str(source), '--store', str(store), '--key-file', str(key_file), '--port', str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                ready = json.loads(process.stdout.readline()); self.assertTrue(ready['ready'])
                return process, ready['port']
            process, port = serve(0)
            try:
                command = [str(console), 'export', '--endpoint', f'http://127.0.0.1:{port}', '--tenant', 'shop', '--output', str(output), '--sort', 'order_id', '--page-size', '2', '--max-pages', '1']
                result = subprocess.run(command, capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(json.loads(result.stdout)['done'])
                process.kill(); process.communicate(timeout=5)
                changed = record(1); changed['total_cents'] = 1234; put_order(source, changed); put_order(source, record(9))
                process, same_port = serve(port); self.assertEqual(same_port, port)
                result = subprocess.run([str(console), 'resume', '--output', str(output), '--page-size', '2'], capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(json.loads(result.stdout)['released'])
                self.assertEqual(list(export_records(output)), expected)
                dumped = subprocess.run([str(console), 'dump', '--output', str(output)], capture_output=True, timeout=20)
                self.assertEqual(dumped.returncode, 0)
                self.assertEqual([json.loads(line) for line in dumped.stdout.splitlines()], expected)
                self.assertNotIn(KEY, result.stdout+result.stderr)
            finally:
                process.kill(); process.communicate(timeout=5)

    def test_invalid_endpoint(self):
        for endpoint in ('http://example.com', 'file:///tmp/a', 'http://127.0.0.1:1/?x=1', 'http://user@127.0.0.1:1'):
            with self.assertRaises(ValueError):
                Client(endpoint, 'shop')


if __name__ == '__main__':
    unittest.main()
