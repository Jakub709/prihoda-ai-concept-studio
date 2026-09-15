"""Run inside the built image. Uses only bundled demo data, no paid API calls."""
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, '/app')
os.environ['STUDIO_PUBLIC_ORIGIN'] = 'https://studio.example.test'
os.environ['STUDIO_ACCESS_CODE'] = 'container-test-only-not-a-real-secret'
os.environ['STUDIO_LOCAL_DEVELOPMENT'] = '0'
from fastapi.testclient import TestClient
from backend.app.production import app

with TestClient(app, base_url=os.environ['STUDIO_PUBLIC_ORIGIN'],
                headers={'Origin':os.environ['STUDIO_PUBLIC_ORIGIN']}) as client:
    assert client.get('/').status_code == 200
    assert client.get('/studio').status_code == 200
    assert client.get('/api/health').json()['ok']
    assert client.get('/api/status').status_code == 401
    assert client.get('/output/demo/scene.blend').status_code == 401
    assert client.get('/.env').status_code == 404
    assert client.post('/api/auth/login', json={'code':os.environ['STUDIO_ACCESS_CODE']}).status_code == 200
    assert client.get('/api/status').json()['blender_ready']
    assert client.get('/output/demo/scene.blend').status_code == 200
    project = client.get('/api/demo').json()
    response = client.post('/api/generate?render=true', json=project)
    assert response.status_code == 200, response.text
    job = response.json()
    deadline = time.monotonic() + 650
    while job['state'] not in ('ready', 'error'):
        assert time.monotonic() < deadline, 'Blender render timed out'
        time.sleep(1)
        job = client.get('/api/jobs/' + job['id']).json()
    assert job['state'] == 'ready', job
    assert client.get(job['model_url']).content[:4] == b'glTF'
    assert client.get(job['preview_url']).content[:8] == b'\x89PNG\r\n\x1a\n'
    assert (Path(os.environ['STUDIO_DATA_DIR']) / 'projects/current_project.json').is_file()
    print('PASS: production routes, login, private output, volume paths, Blender CPU PNG + GLB')
