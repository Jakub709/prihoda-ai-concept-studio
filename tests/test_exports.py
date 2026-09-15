import base64,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import main

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aN1sAAAAASUVORK5CYII=')

class ExportTests(unittest.TestCase):
    def setUp(self):
        access_config=patch('backend.app.access.setting',side_effect=lambda key:'1' if key=='STUDIO_LOCAL_DEVELOPMENT' else '')
        access_config.start();self.addCleanup(access_config.stop)
        self.client=TestClient(main.app,base_url='http://127.0.0.1:5173',client=('127.0.0.1',50000))
    def test_png_is_saved_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(main,'EXPORTS',Path(temp)):
            first=self.client.post('/api/export-preview',content=PNG)
            second=self.client.post('/api/export-preview',content=PNG)
            self.assertEqual(first.status_code,200)
            self.assertNotEqual(first.json()['filename'],second.json()['filename'])
            self.assertEqual((Path(temp)/first.json()['filename']).read_bytes(),PNG)
    def test_invalid_png_and_dimensions(self):
        self.assertEqual(self.client.post('/api/export-preview',content=b'not an image').status_code,422)
        large=bytearray(PNG);large[16:20]=struct.pack('>I',9000)
        self.assertEqual(self.client.post('/api/export-preview',content=bytes(large)).status_code,422)
    def test_payload_limit(self):
        self.assertEqual(self.client.post('/api/export-preview',content=b'x'*(10*1024*1024+1)).status_code,413)

if __name__=='__main__':unittest.main()
