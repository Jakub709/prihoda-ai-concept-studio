import json
import os
import re
import unicodedata
import time
from typing import Protocol
import httpx
from .schemas import DEMO, Project, Patch, Change, apply_patch
from .config import setting
from .network import tls_context

class AIProvider(Protocol):
    def parse_customer_request(self, text: str) -> dict: ...
    def modify_project(self, command: str, project: Project) -> Patch: ...

def normalize(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')
    words = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8',
             'jeden': '1', 'jednu': '1', 'jednim': '1', 'jedno': '1', 'jedny': '1', 'dva': '2', 'dve': '2', 'tri': '3', 'ctyri': '4', 'pet': '5'}
    for word, value in words.items():
        text = re.sub(r'\b' + word + r'\b', value, text)
    text = re.sub(r'\bo\s+metr(?=\s+(?:vys|niz))', 'o 1 metr', text)
    text = re.sub(r'(\d)[, ](?=\d{3}\b)', r'\1', text)
    return re.sub(r'(\d),(\d)', r'\1.\2', text)

class DemoProvider:
    def values(self, text, project):
        t = normalize(text)
        result = {}
        def capture(path, patterns, transform=float):
            for pattern in patterns:
                m = re.search(pattern, t)
                if m:
                    result[path] = transform(m.group(1))
                    break
        n = r'(\d+(?:\.\d+)?)'
        dims = re.search(n + r'\s*[x×]\s*' + n + r'\s*[x×]\s*' + n, t)
        if dims:
            result.update(dict(zip(['room.length_m', 'room.width_m', 'room.height_m'], map(float, dims.groups()))))
        capture('ducts.count', [r'\b(\d+)\s+(?:(?:red|white|blue|grey|green|black|cerven\w*|bil\w*|modr\w*)\s+)?(?:circular\s+)?(?:fabric\s+)?(?:ducts?|potrubi|vyustk\w*)\b', r'(?:number of ducts|duct count|pocet potrubi)\D{0,10}(\d+)'], int)
        capture('ducts.diameter_mm', [r'(?:diameter|prumer|ø)\D{0,12}' + n, n + r'\s*mm'])
        capture('ducts.length_m', [r'(?:ducts? (?:length|to)|delka potrubi)\D{0,8}' + n, r'(?:ducts?|potrubi)[^.;]{0,30}?' + n + r'\s*m\s*(?:long|dlouh)'])
        capture('ducts.spacing_m', [r'(?:spacing|roztec)\D{0,12}' + n])
        capture('ducts.installation_height_m', [r'(?:installation height|vyska instalace|ve vysce)\D{0,10}' + n, n + r'\s*m(?:et(?:er|re)s?)?\s*(?:above (?:the )?floor|nad podlahou)'])
        movement = re.search(n + r'\s*(?:m|metres?|meters?|metr\w*)\s*(higher|lower|vys|niz)', t)
        if movement:
            sign = -1 if movement.group(2) in ('lower', 'niz') else 1
            result['ducts.installation_height_m'] = round(project.ducts.installation_height_m + sign * float(movement.group(1)), 4)
        for color, pattern in [('#d71920', r'\b(?:red|cerven\w*)\b'), ('#eeeeee', r'\b(?:white|bil\w*|light grey)\b'), ('#2874ad', r'\b(?:blue|modr\w*)\b'), ('#475c50', r'\b(?:green|zelen\w*)\b'), ('#50565d', r'\b(?:grey|gray|sed\w*)\b'), ('#25282c', r'\b(?:black|cern\w*)\b')]:
            if re.search(pattern, t): result['ducts.color'] = color
        hex_color = re.search(r'#[0-9a-f]{6}\b', t)
        if hex_color: result['ducts.color'] = hex_color.group(0)
        capture('distribution.angle_deg', [n + r'\s*(?:°|degrees?\b|stupn\w*\b)(?!\s*(?:[cf]\b|celsius\b|fahrenheit\b))', r'(?:angle|uhel)\D{0,10}' + n])
        if 'distribution.angle_deg' in result:
            result['distribution.direction'] = 'angled_down'
        elif re.search(r'\b(?:horizontal|horizontalne)\b', t):
            result.update({'distribution.direction': 'horizontal', 'distribution.angle_deg': 0})
        elif re.search(r'\b(?:straight down|svisle dolu)\b', t):
            result.update({'distribution.direction': 'downward', 'distribution.angle_deg': 90})
        for key, patterns in {
            'room.length_m': [r'(?:hall|room|hala|halu)[^.;]{0,12}?' + n + r'\s*m\s*(?:long|dlouh)', r'(?:hall length|room length|delka haly)\D{0,10}' + n],
            'room.width_m': [r'(?:hall|room|hala|halu)[^.;]{0,12}?' + n + r'\s*m\s*(?:wide|sirok)', r'(?:hall width|room width|sirka haly)\D{0,10}' + n],
            'room.height_m': [r'(?:hall|room|hala|halu)[^.;]{0,12}?' + n + r'\s*m\s*(?:high|tall|vysok)', r'(?:hall height|room height|vyska haly)\D{0,10}' + n],
            'air.airflow_m3h': [r'(?:airflow|prutok)\D{0,12}' + n, n + r'\s*m[³3]/h'],
            'air.supply_temperature_c': [r'(?:supply temperature|privodni teplota)\D{0,10}' + n],
            'air.room_temperature_c': [r'(?:room temperature|teplota mistnosti)\D{0,10}' + n],
            'air.static_pressure_pa': [r'(?:static pressure|staticky tlak)\D{0,10}' + n],
        }.items(): capture(key, patterns)
        for label, value in [('microperforation','microperforation'), ('mikroperforace','microperforation'), ('small nozzles','small_nozzles'), ('male trysky','small_nozzles'), ('large nozzles','large_nozzles'), ('velke trysky','large_nozzles')]:
            if label in t: result['distribution.type'] = value
        if re.search(r'\bperforation\b|\bperforace\b', t): result['distribution.type'] = 'perforation'
        if 'semicircular' in t or 'pulkruh' in t: result['ducts.shape'] = 'semicircular'
        elif 'circular' in t or 'kruhove' in t: result['ducts.shape'] = 'circular'
        return result

    def modify_project(self, command, project):
        values = self.values(command, project)
        original = project.model_dump()
        changes = [Change(path=path, old_value=original[path.split('.')[0]][path.split('.')[1]], new_value=value)
                   for path, value in values.items() if original[path.split('.')[0]][path.split('.')[1]] != value]
        if not changes:
            raise ValueError('No supported change detected. Try “Use three red ducts” or “Move the ducts 1 m higher”. Demo mode supports dimensions, count, colour, diameter and nozzle angle.')
        patch = Patch(changes=changes)
        apply_patch(project, patch)
        return patch

    def parse_customer_request(self, text):
        values = self.values(text, DEMO)
        if not values:
            raise ValueError('No parameters found. Include hall dimensions, for example “30 × 15 × 6 m”, or enter parameters manually.')
        data = DEMO.model_dump()
        data['project_name'] = 'Customer concept'
        data['air'] = {key: None for key in data['air']}
        for path, value in values.items():
            section, field = path.split('.')
            data[section][field] = value
        missing = [f'{section}.{key}' for section in ['room','air','ducts','distribution'] for key in data[section] if f'{section}.{key}' not in values]
        return {'project': Project.model_validate(data), 'extracted': list(values), 'unconfirmed': missing, 'provider': 'demo'}

class OpenAIProvider:
    """Optional provider. Outputs are validated data, never executable code."""
    def project_rules(self):
        return ('Use section.field paths and values that satisfy this project schema: '
                + json.dumps(Project.model_json_schema())
                + '\nCopy old_value exactly from the provided project, preserving its JSON type. '
                'Use numbers for numeric fields, booleans for switches, and the exact enum strings. '
                'Colour names must be converted to six-digit hex codes: red #d71920, white #eeeeee, '
                'blue #2874ad, green #475c50, grey/gray #50565d, black #25282c. '
                'Preserve an explicitly requested custom hex code. '
                'A relative height change is added to the existing installation_height_m. '
                'An angle measured downward uses direction angled_down; straight down uses downward and 90; '
                'horizontal uses horizontal and 0. Do not confuse temperatures with nozzle angles. '
                'Include only requested fields and necessary direction/angle consistency changes.\n')
    def ask(self, instruction, schema):
        start = time.monotonic()
        response = httpx.post('https://api.openai.com/v1/chat/completions', timeout=35, verify=tls_context(),
            headers={'Authorization': 'Bearer ' + setting('OPENAI_API_KEY')},
            json={'model': setting('OPENAI_MODEL', 'gpt-5.6-terra'),
                'messages': [{'role':'system','content':'You structure conceptual HVAC data. Never generate code. Only use explicitly requested values. Do not infer engineering calculations.'}, {'role':'user','content':instruction}],
                'response_format': {'type':'json_schema','json_schema': {'name':'result','strict':True,'schema':schema}}})
        response.raise_for_status()
        payload = response.json()
        self.receipt = {'provider':'openai', 'model':payload.get('model',setting('OPENAI_MODEL','gpt-5.6-terra')),
                        'request_id':payload.get('id'), 'latency_ms':round((time.monotonic()-start)*1000),
                        'tokens':payload.get('usage',{}).get('total_tokens')}
        choice=payload['choices'][0]
        if choice['message'].get('refusal'):
            raise ValueError('The AI provider declined this instruction. Your concept is unchanged.')
        if choice.get('finish_reason')!='stop' or not choice['message'].get('content'):
            raise ValueError('The AI response was incomplete. Your concept is unchanged. Try again.')
        return json.loads(choice['message']['content'])

    def modify_project(self, command, project):
        patch = Patch.model_validate(self.ask(self.project_rules() + 'Return changes for this project. Project: ' + project.model_dump_json() + '\nInstruction: ' + command, Patch.model_json_schema()))
        apply_patch(project, patch)
        return patch

    def parse_customer_request(self, text):
        baseline = DEMO.model_copy(deep=True)
        for key in type(baseline.air).model_fields: setattr(baseline.air, key, None)
        patch = Patch.model_validate(self.ask(self.project_rules() + 'Extract only explicitly stated values as patches to this baseline: ' + baseline.model_dump_json() + '\nRequest: ' + text, Patch.model_json_schema()))
        project = apply_patch(baseline, patch)
        project.project_name = 'Customer concept'
        extracted = [c.path for c in patch.changes]
        return {'project':project, 'extracted':extracted, 'unconfirmed':[f'{s}.{k}' for s in ['room','air','ducts','distribution'] for k in project.model_dump()[s] if f'{s}.{k}' not in extracted], 'provider':'openai', 'receipt':self.receipt}

def provider():
    return OpenAIProvider() if setting('OPENAI_API_KEY') else DemoProvider()
