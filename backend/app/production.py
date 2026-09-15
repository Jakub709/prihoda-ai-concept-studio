"""Single-process production entry point: protected API + built public website."""
from pathlib import Path
import shutil

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT
from .main import app
from .services import OUTPUT


def mount_frontend(application, directory: Path):
    directory = directory.resolve()
    if not (directory / 'index.html').is_file():
        raise RuntimeError('Frontend build missing. Run npm run build before starting production.')

    @application.api_route('/', methods=['GET', 'HEAD'], include_in_schema=False)
    @application.api_route('/studio', methods=['GET', 'HEAD'], include_in_schema=False)
    @application.api_route('/studio/', methods=['GET', 'HEAD'], include_in_schema=False)
    def frontend():
        return FileResponse(directory / 'index.html', headers={'Cache-Control': 'no-cache'})

    # Unknown API routes must never fall through to HTML or public assets.
    @application.api_route('/api/{path:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'], include_in_schema=False)
    def missing_api(path: str):
        raise HTTPException(404, 'API endpoint not found.')

    application.mount('/', StaticFiles(directory=directory), name='website')


# Docker bakes only the bundled demo into the image. User output lives on /data.
seed = ROOT / 'demo-seed'
if seed.is_dir():
    destination = OUTPUT / 'demo'
    destination.mkdir(parents=True, exist_ok=True)
    for source in seed.iterdir():
        if source.is_file():
            shutil.copy2(source, destination / source.name)

mount_frontend(app, ROOT / 'dist')
