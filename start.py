"""Run both local services. Ctrl+C stops only processes started by this launcher."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/'.runtime'
RUNTIME.mkdir(exist_ok=True)

def response(url):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:return r.read().decode('utf-8')
    except (OSError,urllib.error.URLError):return None

def python_path():
    for folder in [ROOT/'.venv',ROOT.parent/'.venv']:
        p=folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if p.is_file():return str(p)
    return sys.executable

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=5173,help='Local frontend port; backend stays on 8000.')
    args=parser.parse_args()
    if not 1024 <= args.port <= 65535 or args.port == 8000:
        parser.error('Choose a frontend port between 1024 and 65535 other than 8000.')
    frontend_url=f'http://127.0.0.1:{args.port}/'
    node=shutil.which('node')
    if not node or not (ROOT/'node_modules/vite/bin/vite.js').is_file():
        raise SystemExit('Node.js or frontend dependencies are missing. Run npm ci in the project folder first.')
    if not (ROOT/'dist/index.html').is_file():
        raise SystemExit('The application build is missing. Run npm run build first.')
    backend=response('http://127.0.0.1:8000/api/health')
    if backend and json.loads(backend).get('app')!='prihoda-concept-studio':
        raise SystemExit('Port 8000 is used by another application. Close it or change the configured ports.')
    frontend=response(frontend_url)
    if frontend and 'AI Concept Studio' not in frontend:
        raise SystemExit(f'Port {args.port} is used by another application. Select another port with --port.')
    processes=[]
    logs=[]
    try:
        for name,existing,command,url in [
            ('backend',backend,[python_path(),'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000'],'http://127.0.0.1:8000/api/health'),
            ('frontend',frontend,[node,str(ROOT/'node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port',str(args.port)],frontend_url),
        ]:
            if existing:
                print(name+': already running',flush=True)
                continue
            log=(RUNTIME/(name+'.log')).open('w',encoding='utf-8')
            logs.append(log)
            local_env = dict(os.environ, STUDIO_LOCAL_DEVELOPMENT='1')
            proc=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=local_env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            processes.append(proc)
            deadline=time.monotonic()+30
            while not response(url):
                if proc.poll() is not None:raise RuntimeError(name+' failed to start. See .runtime/'+name+'.log')
                if time.monotonic()>deadline:raise RuntimeError(name+' did not respond. See .runtime/'+name+'.log')
                time.sleep(.2)
            print(name+': ready',flush=True)
        print('PŘÍHODA AI Concept Studio: '+frontend_url,flush=True)
        print('Keep this launcher running. Press Ctrl+C to stop the services it started.',flush=True)
        if not args.no_browser:webbrowser.open(frontend_url)
        while processes:
            for proc in processes:
                if proc.poll() is not None:raise RuntimeError('A service stopped. Check the .runtime logs.')
            time.sleep(1)
    except KeyboardInterrupt:
        print('Stopping local services.',flush=True)
    finally:
        for proc in processes:
            if proc.poll() is None:proc.terminate()
        for proc in processes:
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill()
        for log in logs:log.close()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Could not start the studio: '+str(exc),file=sys.stderr)
        sys.exit(1)
