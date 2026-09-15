import json, os, unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.app.main import app
from backend.app.schemas import DEMO, Project, Patch, Change, apply_patch
from backend.app.ai import DemoProvider
from backend.app.services import find_blender
COMMAND='Use three red ducts, move them one metre higher and point the nozzles 35 degrees downward.'
class ConceptTests(unittest.TestCase):
    def setUp(self):
        access_config=patch('backend.app.access.setting',side_effect=lambda key:'1' if key=='STUDIO_LOCAL_DEVELOPMENT' else '')
        access_config.start();self.addCleanup(access_config.stop)
        self.client=TestClient(app,base_url='http://127.0.0.1:5173',client=('127.0.0.1',50000))
        self.provider=DemoProvider()
    def test_required_demo_command(self):
        changes=self.provider.modify_project(COMMAND,DEMO)
        p=apply_patch(DEMO,changes)
        self.assertEqual(len(changes.changes),4)
        self.assertEqual((p.ducts.count,p.ducts.color,p.ducts.installation_height_m,p.distribution.angle_deg),(3,'#d71920',5.5,35))
        self.assertEqual(DEMO.ducts.count,2)
    def test_commands_and_czech(self):
        for command,path,value in [('Move the ducts 1 m lower','ducts.installation_height_m',3.5),('Increase diameter to 800 mm','ducts.diameter_mm',800),('Make the hall 40 m long','room.length_m',40),('Pouzij tri cervena potrubi a posun je o jeden metr vys','ducts.count',3),('Point the nozzles 35° downward','distribution.angle_deg',35)]:
            with self.subTest(command=command):
                data=apply_patch(DEMO,self.provider.modify_project(command,DEMO)).model_dump()
                s,k=path.split('.');self.assertEqual(data[s][k],value)
    def test_exact_czech_landing_command(self):
        command='Použij tři červená potrubí, posuň je o metr výš a natoč trysky 35° dolů.'
        changes=self.provider.modify_project(command,DEMO)
        result=apply_patch(DEMO,changes)
        self.assertEqual(len(changes.changes),4)
        self.assertEqual((result.ducts.count,result.ducts.color,result.ducts.installation_height_m,result.distribution.angle_deg),(3,'#d71920',5.5,35))
    def test_parse_provenance(self):
        d=self.provider.parse_customer_request('Hall 30 × 15 × 6 m, airflow 7,000 m³/h, two ducts 4.5 m above the floor.')
        self.assertEqual(d['project'].air.airflow_m3h,7000)
        self.assertIsNone(d['project'].air.static_pressure_pa)
        self.assertIn('air.static_pressure_pa',d['unconfirmed'])
        self.assertIn('room.length_m',d['extracted'])
        self.assertIn('ducts.diameter_mm',d['unconfirmed'])
    def test_temperatures_are_not_nozzle_angles(self):
        text='We have a production hall 30 × 15 × 6 m. Required airflow is 7,000 m³/h. We are considering two circular fabric ducts, diameter 600 mm, 22 m long, installed 4.5 m above the floor. Supply temperature 16 °C, room temperature 22 °C. Use large nozzles angled 30° downward.'
        p=self.provider.parse_customer_request(text)['project']
        self.assertEqual((p.air.supply_temperature_c,p.air.room_temperature_c,p.distribution.angle_deg),(16,22,30))
        for unit in ('°C','°F','degrees Celsius','degrees Fahrenheit'):
            with self.subTest(unit=unit):
                parsed=self.provider.parse_customer_request('Hall 30 × 15 × 6 m, supply temperature 16 '+unit)
                self.assertNotIn('distribution.angle_deg',parsed['extracted'])
    def test_invalid_geometry(self):
        for field,value in [('count',0),('count',9),('installation_height_m',9),('diameter_mm',3000),('length_m',45),('spacing_m',.3)]:
            with self.subTest(field=field):
                d=DEMO.model_dump();d['ducts'][field]=value
                with self.assertRaises(ValidationError):Project.model_validate(d)
    def test_patch_allowlist_and_stale(self):
        for path,old,new in [('__proto__.file',None,'bad'),('ducts.count',7,3),('ducts.color','#eeeeee','javascript:alert(1)')]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    apply_patch(DEMO,Patch(changes=[Change(path=path,old_value=old,new_value=new)]))
    def test_unknown_instruction(self):
        with self.assertRaises(ValueError):self.provider.modify_project('Build me a helicopter',DEMO)
    def test_invalid_json_error(self):
        r=self.client.post('/api/generate',content='{ broken',headers={'Content-Type':'application/json'})
        self.assertEqual(r.status_code,422)
        self.assertNotIn('Traceback',r.text)
    def test_wrong_blender_path(self):
        with patch.dict(os.environ,{'BLENDER_PATH':'C:/missing/blender.exe'}):
            self.assertIsNone(find_blender())
            r=self.client.post('/api/generate',json=DEMO.model_dump())
            self.assertEqual(r.status_code,503)
            self.assertIn('demo preview',r.json()['detail'])
    def test_api_unavailable(self):
        class Unavailable:
            def modify_project(self,*args):raise httpx.ConnectError('offline')
        with patch('backend.app.main.provider',return_value=Unavailable()):
            r=self.client.post('/api/modify',json={'command':COMMAND,'project':DEMO.model_dump()})
            self.assertEqual(r.status_code,503)
            self.assertIn('unchanged',r.json()['detail'])
    def test_endpoints(self):
        self.assertEqual(self.client.get('/api/demo').json()['ducts']['count'],2)
        self.assertEqual(self.client.get('/api/jobs/unknown').status_code,404)
        self.assertEqual(self.client.post('/api/validate',json=DEMO.model_dump()).status_code,200)
if __name__=='__main__':unittest.main(verbosity=2)
