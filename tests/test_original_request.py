import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.ai import DemoProvider
from backend.app.schemas import DEMO, Project, Patch, Change, apply_patch
from backend.app import storage


class OriginalRequestTests(unittest.TestCase):
    def test_parse_keeps_exact_source_and_modification_preserves_it(self):
        text = '  Výrobní hala 36 × 18 × 7 m.\nDvě bílá potrubí.  '
        with patch('backend.app.access.setting', side_effect=lambda key: '1' if key == 'STUDIO_LOCAL_DEVELOPMENT' else ''), patch('backend.app.main.provider', return_value=DemoProvider()):
            client = TestClient(app, base_url='http://127.0.0.1:5174', client=('127.0.0.1', 50000))
            response = client.post('/api/parse', json={'text': text})
            self.assertEqual(response.status_code, 200)
            project = response.json()['project']
            self.assertEqual(project['original_request'], text)
            changed = client.post('/api/modify', json={'command': 'Use three red ducts', 'project': project})
            self.assertEqual(changed.status_code, 200)
            self.assertEqual(changed.json()['project']['original_request'], text)
            self.assertIsNone(DEMO.original_request)

    def test_ai_cannot_patch_original_request(self):
        with self.assertRaises(ValueError):
            apply_patch(DEMO, Patch(changes=[Change(path='original_request', old_value=None, new_value='invented')]))

    def test_legacy_project_has_no_invented_source(self):
        legacy = DEMO.model_dump(exclude={'original_request'})
        self.assertIsNone(Project.model_validate(legacy).original_request)

    def test_cloud_load_restores_source_of_selected_version(self):
        project_id = str(uuid4())
        for source in ('Původní zákaznické zadání\nse dvěma řádky.', None):
            data = DEMO.model_dump(exclude={'original_request'})
            if source is not None:
                data['original_request'] = source
            row = {'id': str(uuid4()), 'parameters': data, 'assets': {}, 'version': 1}
            with self.subTest(source=source), patch.object(storage, 'call', side_effect=[[row], [{'latest_version': 2}]]), patch.object(storage, 'connection', return_value=('https://example.supabase.co', {})):
                restored = storage.load_project(project_id, 1)
                self.assertEqual(restored['project']['original_request'], source)
                self.assertEqual(restored['version'], 1)
                self.assertEqual(restored['latest_version'], 2)
