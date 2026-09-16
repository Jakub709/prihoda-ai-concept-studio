import unittest
from unittest.mock import patch
from backend.app.ai import OpenAIProvider
from backend.app.schemas import DEMO, Change, Patch, apply_patch, patch_response_schema, ALLOWED_PATHS

class AIPathTests(unittest.TestCase):
    def test_ai_schema_enumerates_supported_paths_and_excludes_original_request(self):
        paths = patch_response_schema()['$defs']['Change']['properties']['path']['enum']
        self.assertEqual(set(paths), ALLOWED_PATHS)
        self.assertIn('project_name', paths)
        self.assertNotIn('original_request', paths)
        self.assertNotIn('room.number_of_courts', paths)

    def test_named_customer_request_keeps_name(self):
        response = {'changes':[
            {'path':'project_name','old_value':'Customer concept','new_value':'Blue Court'},
            {'path':'room.type','old_value':'production_hall','new_value':'sports_hall'}]}
        with patch.object(OpenAIProvider, 'ask', return_value=response):
            ai = OpenAIProvider(); ai.receipt = {'provider':'test'}
            result = ai.parse_customer_request('Sportovní hala. Projekt pojmenuj Blue Court.')
        self.assertEqual(result['project'].project_name, 'Blue Court')
        self.assertEqual(result['project'].room.type, 'sports_hall')
        self.assertEqual(DEMO.project_name, 'Production Hall Demo')

    def test_duplicate_and_protected_changes_remain_rejected_atomically(self):
        change = Change(path='ducts.count',old_value=2,new_value=3)
        for changes in ([change,change], [Change(path='original_request',old_value=None,new_value='overwrite')]):
            with self.assertRaises(ValueError):apply_patch(DEMO, Patch(changes=changes))
        self.assertEqual(DEMO.ducts.count, 2)

    def test_rename_checks_old_value_and_name_validation(self):
        for old,new in [('wrong','New name'), (DEMO.project_name,'')]:
            with self.assertRaises(ValueError):
                apply_patch(DEMO,Patch(changes=[Change(path='project_name',old_value=old,new_value=new)]))
