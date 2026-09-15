import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from backend.app import access
from backend.app.main import app

ORIGIN = 'https://studio.example.test'
CODE = 'test-fixture-private-access-2026'

class AccessTests(unittest.TestCase):
    def setUp(self):
        # No dependency on local, ignored Blender outputs in a clean checkout.
        self.assets = tempfile.TemporaryDirectory()
        self.addCleanup(self.assets.cleanup)
        folder = Path(self.assets.name) / 'demo'
        folder.mkdir()
        (folder / 'manifest.json').write_text('{}')
        output_route = next(route for route in app.routes if route.path == '/output')
        asset_patch = patch.object(output_route, 'app', StaticFiles(directory=self.assets.name))
        asset_patch.start()
        self.addCleanup(asset_patch.stop)
        self.settings = {'STUDIO_PUBLIC_ORIGIN': ORIGIN, 'STUDIO_ACCESS_CODE': CODE}
        self.config = patch.object(access, 'setting', side_effect=lambda key: self.settings.get(key, ''))
        self.config.start()
        self.addCleanup(self.config.stop)
        access.ATTEMPTS.clear()
        self.client = TestClient(app, base_url=ORIGIN, headers={'Origin': ORIGIN})

    def login(self):
        return self.client.post('/api/auth/login', json={'code': CODE})

    def test_default_server_is_closed_even_on_localhost(self):
        self.settings.clear()
        client = TestClient(app, base_url='http://127.0.0.1', client=('127.0.0.1', 40000))
        self.assertEqual(client.get('/api/demo').status_code, 401)
        self.assertFalse(client.get('/api/auth/session').json()['authenticated'])
        self.assertEqual(client.post('/api/auth/login', json={'code': CODE}).status_code, 503)

    def test_guest_cannot_read_projects_models_or_invoke_generation(self):
        with patch('backend.app.main.generate') as generate, patch('backend.app.main.storage.list_projects') as projects:
            for path in ('/api/demo', '/api/status', '/api/projects', '/api/jobs/demo', '/api/connections', '/output/demo/preview.png', '/output/demo/model.glb', '/output/demo/scene.blend', '/docs', '/openapi.json'):
                with self.subTest(path=path):
                    r = self.client.get(path)
                    self.assertEqual(r.status_code, 401)
                    self.assertEqual(r.headers['Cache-Control'], 'no-store')
            self.assertEqual(self.client.post('/api/generate', json={}).status_code, 401)
            self.assertEqual(self.client.post('/api/export-preview', content=b'test').status_code, 401)
            generate.assert_not_called()
            projects.assert_not_called()

    def test_login_cookie_allows_api_and_private_model_then_logout_closes_both(self):
        r = self.login()
        self.assertEqual(r.status_code, 200)
        for attribute in ('HttpOnly', 'Secure', 'SameSite=strict', 'Max-Age=28800'):
            self.assertIn(attribute, r.headers['set-cookie'])
        self.assertNotIn(CODE, r.text + r.headers['set-cookie'])
        self.assertTrue(self.client.get('/api/auth/session').json()['authenticated'])
        self.assertEqual(self.client.get('/api/demo').json()['ducts']['count'], 2)
        asset = self.client.get('/output/demo/manifest.json')
        self.assertEqual(asset.status_code, 200)
        self.assertEqual(asset.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.client.post('/api/auth/logout').status_code, 200)
        self.assertFalse(self.client.get('/api/auth/session').json()['authenticated'])
        self.assertEqual(self.client.get('/output/demo/manifest.json').status_code, 401)

    def test_wrong_code_and_throttling(self):
        for _ in range(5):
            self.assertEqual(self.client.post('/api/auth/login', json={'code':'wrong'}).status_code, 401)
        r = self.login()
        self.assertEqual(r.status_code, 429)
        self.assertIn('Retry-After', r.headers)
        with patch.object(access.time, 'monotonic', return_value=10**12):
            self.assertEqual(self.login().status_code, 200)

    def test_tampered_expired_and_revoked_sessions_are_rejected(self):
        self.login()
        valid = self.client.cookies.get(access.COOKIE)
        for token in ('123.bad.bad', valid[:-1] + ('a' if valid[-1]!='a' else 'b'), 'x'*1000):
            self.client.cookies.clear()
            self.client.cookies.set(access.COOKIE, token)
            self.assertEqual(self.client.get('/api/demo').status_code, 401)
        self.client.cookies.clear()
        self.login()
        with patch.object(access.time, 'time', return_value=10**12):
            self.assertEqual(self.client.get('/api/demo').status_code, 401)
        self.settings['STUDIO_ACCESS_CODE'] = CODE + '-rotated'
        self.assertEqual(self.client.get('/api/demo').status_code, 401)

    def test_cross_site_mutations_rejected_and_remote_settings_read_only(self):
        self.login()
        for path in ('/api/auth/login', '/api/auth/logout', '/api/generate', '/api/connections'):
            self.assertEqual(self.client.post(path, json={}, headers={'Origin':'https://attacker.example'}).status_code, 403)
        with patch('backend.app.main.configure') as configure:
            self.assertEqual(self.client.post('/api/connections', json={'OPENAI_API_KEY':'injected'}).status_code, 403)
            self.assertEqual(self.client.post('/api/connections/test').status_code, 403)
            configure.assert_not_called()

    def test_development_bypass_requires_explicit_flag_local_peer_and_local_host(self):
        self.settings.clear()
        self.settings['STUDIO_LOCAL_DEVELOPMENT'] = '1'
        local = TestClient(app, base_url='http://127.0.0.1:5173', client=('127.0.0.1', 40000))
        self.assertTrue(local.get('/api/auth/session').json()['local'])
        self.assertEqual(local.get('/api/demo').status_code, 200)
        self.assertEqual(local.get('/api/demo', headers={'Host':'public.example'}).status_code, 401)
        self.assertEqual(local.get('/api/demo', headers={'X-Forwarded-For':'127.0.0.1'}).status_code, 401)
        remote = TestClient(app, base_url='http://127.0.0.1:5173', client=('10.0.0.8', 40000))
        self.assertEqual(remote.get('/api/demo').status_code, 401)
        self.settings.update({'STUDIO_PUBLIC_ORIGIN': ORIGIN, 'STUDIO_ACCESS_CODE': CODE})
        self.assertEqual(local.get('/api/demo').status_code, 401)

    def test_invalid_public_configuration_stays_closed(self):
        for origin, code in (('http://public.example', CODE), (ORIGIN, 'weak'), ('https://[', CODE), ('https://example.test/path', CODE)):
            with self.subTest(origin=origin):
                self.settings.update({'STUDIO_PUBLIC_ORIGIN':origin, 'STUDIO_ACCESS_CODE':code})
                self.assertFalse(self.client.get('/api/auth/session').json()['configured'])
                self.assertEqual(self.client.get('/api/demo').status_code, 401)

    def test_alternate_local_preview_port_accepts_only_its_same_origin(self):
        self.settings = {'STUDIO_LOCAL_DEVELOPMENT':'1'}
        local = TestClient(app, base_url='http://127.0.0.1:5174', client=('127.0.0.1',40000))
        from backend.app.schemas import DEMO
        self.assertEqual(local.post('/api/validate', json=DEMO.model_dump(), headers={'Origin':'http://127.0.0.1:5174'}).status_code, 200)
        self.assertEqual(local.post('/api/validate', json=DEMO.model_dump(), headers={'Origin':'https://attacker.example'}).status_code, 403)

    def test_health_is_public_without_configuration_or_private_details(self):
        self.settings.clear()
        self.assertEqual(self.client.get('/api/health').json(), {'app':'prihoda-concept-studio','ok':True})

if __name__ == '__main__':
    unittest.main()
