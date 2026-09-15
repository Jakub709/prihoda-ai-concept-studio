import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import httpx
from fastapi.testclient import TestClient
from backend.app import storage, config
from backend.app.main import app
from backend.app.schemas import DEMO

class CloudTests(unittest.TestCase):
    def test_tls_keeps_certificate_and_hostname_verification(self):
        import ssl
        from backend.app.network import tls_context
        self.assertTrue(tls_context().check_hostname)
        self.assertEqual(tls_context().verify_mode,ssl.CERT_REQUIRED)

    def test_missing_keys_cannot_fake_a_save(self):
        with patch.object(storage,'setting',return_value=''):
            with self.assertRaisesRegex(storage.StorageError,'Connect a Supabase'):
                storage.save_project(DEMO,'demo')

    def test_secret_key_stays_in_apikey_header(self):
        settings={'SUPABASE_URL':'https://example.supabase.co','SUPABASE_SECRET_KEY':'sb_secret_test'}
        with patch.object(storage,'setting',side_effect=lambda k:settings.get(k,'')):
            url,headers=storage.connection()
            self.assertEqual(headers,{'apikey':'sb_secret_test'})
            self.assertEqual(url,'https://example.supabase.co')

    def test_arbitrary_storage_hosts_are_rejected(self):
        with patch.object(storage,'setting',side_effect=lambda k:'https://attacker.example' if k=='SUPABASE_URL' else 'secret'):
            with self.assertRaises(storage.StorageError):storage.connection()

    def test_untrusted_origin_cannot_change_keys(self):
        response=TestClient(app).post('/api/connections',json={'OPENAI_API_KEY':'injected'},headers={'Origin':'https://attacker.example'})
        self.assertEqual(response.status_code,403)

    def test_public_settings_do_not_include_secrets(self):
        with patch.object(config,'setting',side_effect=lambda k,default='':'sb_secret_sentinel' if 'KEY' in k else default):
            result=config.public_settings()
            self.assertNotIn('sentinel',json.dumps(result))

    def test_only_matching_model_can_be_saved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'output/demo';folder.mkdir(parents=True)
            modified=DEMO.model_copy(deep=True);modified.ducts.color='#d71920'
            (folder/'manifest.json').write_text(json.dumps({'project':modified.model_dump()}))
            with patch.object(storage,'ROOT',root),patch.object(storage,'connection',return_value=('url',{})),patch.object(storage,'call') as call:
                with self.assertRaisesRegex(storage.StorageError,'Generate your changed'):
                    storage.save_project(DEMO,'demo')
                call.assert_not_called()

    def test_private_assets_and_expected_version_reach_atomic_rpc(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'output/demo';folder.mkdir(parents=True)
            (folder/'manifest.json').write_text(json.dumps({'project':DEMO.model_dump()}))
            for filename in ('model.glb','scene.blend'): (folder/filename).write_bytes(b'actual-fixture')
            project_id=str(uuid4())
            with patch.object(storage,'ROOT',root),patch.object(storage,'connection',return_value=('url',{})),patch.object(storage,'call',return_value={'version':3}) as call:
                result=storage.save_project(DEMO,'demo',project_id,2,'New layout')
                self.assertEqual(result['version'],3)
                requests=call.call_args_list
                self.assertEqual(len(requests),4)
                self.assertTrue(all('/storage/v1/object/prihoda-concepts/'+project_id+'/' in r.args[1] for r in requests[:3]))
                rpc=requests[-1]
                self.assertEqual(rpc.args[1],'/rest/v1/rpc/save_prihoda_version')
                self.assertEqual(rpc.kwargs['json']['p_expected'],2)
                self.assertEqual(rpc.kwargs['json']['p_parameters'],DEMO.model_dump())

    def test_uncertain_commit_never_deletes_version_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'output/demo';folder.mkdir(parents=True)
            (folder/'manifest.json').write_text(json.dumps({'project':DEMO.model_dump()}))
            for filename in ('model.glb','scene.blend'): (folder/filename).write_bytes(b'fixture')
            with patch.object(storage,'ROOT',root),patch.object(storage,'connection',return_value=('url',{})),patch.object(storage,'call',side_effect=[{}, {}, {},storage.StorageError('Timeout')]) as call:
                with self.assertRaises(storage.StorageError):storage.save_project(DEMO,'demo')
                self.assertFalse(any(c.args[0]=='DELETE' for c in call.call_args_list))

    def test_conflict_and_missing_migration_have_actionable_errors(self):
        for code,message in [('40001','newer version'),('PGRST205','migration')]:
            response=httpx.Response(400,json={'code':code})
            with patch.object(storage,'connection',return_value=('https://example.supabase.co',{})),patch.object(storage.httpx,'request',return_value=response):
                with self.assertRaisesRegex(storage.StorageError,message):storage.list_projects()

if __name__=='__main__':unittest.main(verbosity=2)
