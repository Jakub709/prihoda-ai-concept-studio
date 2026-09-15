import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app import config, services
from backend.app.production import mount_frontend
from backend.app.schemas import DEMO


class ProductionTests(unittest.TestCase):
    def test_only_built_public_files_are_served(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dist = root / 'dist'
            dist.mkdir()
            (dist / 'index.html').write_text('<html>Landing and studio</html>')
            (dist / 'asset.js').write_text('public asset')
            (root / '.env').write_text('PRIVATE_FIXTURE')
            application = FastAPI()
            mount_frontend(application, dist)
            client = TestClient(application)
            for route in ('/', '/studio', '/studio/'):
                self.assertEqual(client.get(route).status_code, 200)
                self.assertEqual(client.get(route).headers['cache-control'], 'no-cache')
            self.assertEqual(client.get('/asset.js').text, 'public asset')
            for route in ('/.env', '/%2e%2e/.env', '/backend/app/config.py', '/api/missing', '/missing.js'):
                response = client.get(route)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn('PRIVATE_FIXTURE', response.text)

    def test_environment_overrides_dotenv_including_empty_values(self):
        with patch.object(config, 'dotenv_values', return_value={'TEST_SETTING':'file'}):
            with patch.dict(os.environ, {'TEST_SETTING':'server'}):
                self.assertEqual(config.setting('TEST_SETTING'), 'server')
            with patch.dict(os.environ, {'TEST_SETTING':''}):
                self.assertEqual(config.setting('TEST_SETTING'), '')

    def test_current_project_uses_volume_and_engine_changes_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {'STUDIO_DATA_DIR':temp, 'BLENDER_RENDER_ENGINE':'CYCLES'}):
                services.save_current(DEMO)
                self.assertTrue((Path(temp) / 'projects/current_project.json').is_file())
                cycles = services.job_key(DEMO, True)
            with patch.dict(os.environ, {'BLENDER_RENDER_ENGINE':'BLENDER_EEVEE_NEXT'}):
                self.assertNotEqual(cycles, services.job_key(DEMO, True))
