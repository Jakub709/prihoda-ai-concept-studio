import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from backend.app import services
from backend.app.ai import OpenAIProvider
from backend.app.schemas import DEMO

class ServiceTests(unittest.TestCase):
    def wait_job(self,key):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            job=services.get_job(key)
            if job['state'] in ('error','ready'):return job
            time.sleep(.01)
        self.fail('Worker did not finish')
    def test_process_failure_becomes_readable_error(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(services,'ROOT',Path(temp)),patch.object(services,'OUTPUT',Path(temp)/'output'),patch.dict(services.JOBS,{},clear=True),patch.object(services,'find_blender',return_value='blender'),patch.object(services.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
                # Output root is normally created at import time.
                services.OUTPUT.mkdir()
                j=services.generate(DEMO)
                result=self.wait_job(j['id'])
                self.assertEqual(result['state'],'error')
                self.assertIn('previous concept',result['error'])
    def test_export_missing_is_error_even_with_zero_exit_code(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(services,'ROOT',Path(temp)),patch.object(services,'OUTPUT',Path(temp)/'output'),patch.dict(services.JOBS,{},clear=True),patch.object(services,'find_blender',return_value='blender'),patch.object(services.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
                services.OUTPUT.mkdir()
                result=self.wait_job(services.generate(DEMO)['id'])
                self.assertEqual(result['state'],'error')
    def test_timeout_becomes_readable_error(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(services,'ROOT',Path(temp)),patch.object(services,'OUTPUT',Path(temp)/'output'),patch.dict(services.JOBS,{},clear=True),patch.object(services,'find_blender',return_value='blender'),patch.object(services.subprocess,'run',side_effect=services.subprocess.TimeoutExpired('blender',150)):
                services.OUTPUT.mkdir()
                result=self.wait_job(services.generate(DEMO)['id'])
                self.assertIn('too long',result['error'])
    def test_cached_undo_restores_current_json(self):
        key=services.job_key(DEMO,False)
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(services,'ROOT',Path(temp)),patch.dict(services.JOBS,{key:services.output_result(key,False)},clear=True),patch.object(services,'find_blender',return_value='blender'):
                changed=DEMO.model_copy(deep=True);changed.ducts.count=3
                services.save_current(changed)
                result=services.generate(DEMO)
                current=json.loads((Path(temp)/'projects/current_project.json').read_text())
                self.assertEqual(result['state'],'ready')
                self.assertEqual(current['ducts']['count'],2)
    def test_optional_provider_strict_schema_and_patch(self):
        result={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'changes':[{'path':'ducts.count','old_value':2,'new_value':3}]})}}]}
        response=httpx.Response(200,json=result,request=httpx.Request('POST','https://api.openai.com/v1/chat/completions'))
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-placeholder'}),patch('backend.app.ai.httpx.post',return_value=response) as post:
            p=OpenAIProvider().modify_project('Use three ducts',DEMO)
            self.assertEqual(p.changes[0].new_value,3)
            body=post.call_args.kwargs['json']
            self.assertTrue(body['response_format']['json_schema']['strict'])
            self.assertFalse(body['response_format']['json_schema']['schema']['additionalProperties'])
    def test_optional_provider_refusal(self):
        response=httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'refusal':'declined'}}]},request=httpx.Request('POST','https://api.openai.com/v1/chat/completions'))
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-placeholder'}),patch('backend.app.ai.httpx.post',return_value=response):
            with self.assertRaisesRegex(ValueError,'declined'):OpenAIProvider().modify_project('instruction',DEMO)
if __name__=='__main__':unittest.main(verbosity=2)
