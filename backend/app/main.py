import logging
import struct
from uuid import uuid4, UUID
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError, BaseModel, Field, ConfigDict
from .schemas import DEMO, Project, TextRequest, ModifyRequest, apply_patch
from .ai import provider, OpenAIProvider
from .services import find_blender, generate, get_job, ROOT, OUTPUT
from .config import public_settings, configure, setting
from . import storage
from .access import router as access_router, protect_studio

app=FastAPI(title='PŘÍHODA AI Concept Studio',version='2.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['GET','POST'],allow_headers=['Content-Type'])
app.mount('/output',StaticFiles(directory=OUTPUT),name='output')
EXPORTS=OUTPUT/'exports'
app.middleware('http')(protect_studio)
app.include_router(access_router)

@app.get('/api/health')
def health():
    return {'app':'prihoda-concept-studio','ok':True}

class ConnectionInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    OPENAI_API_KEY:str=Field(default='',max_length=500)
    OPENAI_MODEL:str=Field(default='',max_length=100)
    SUPABASE_URL:str=Field(default='',max_length=200)
    SUPABASE_SECRET_KEY:str=Field(default='',max_length=2000)

@app.get('/api/connections')
def connections(): return public_settings()

@app.get('/api/connections/schema')
def schema_download():
    sql=(ROOT/'supabase/migrations/202609120001_prihoda_studio.sql').read_text(encoding='utf-8')
    return PlainTextResponse(sql,headers={'Content-Disposition':'attachment; filename="prihoda-studio.sql"'})

@app.post('/api/connections')
def save_connections(values:ConnectionInput):
    if values.SUPABASE_URL:
        import re
        if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co/?',values.SUPABASE_URL.strip()):
            raise HTTPException(422,'Use the HTTPS URL of your Supabase project.')
    configure(values.model_dump())
    return public_settings()

@app.post('/api/connections/test')
def test_connections():
    results={}
    if setting('OPENAI_API_KEY'):
        try:
            ai=OpenAIProvider()
            ai.ask('Return {"connected":true}.',{'type':'object','properties':{'connected':{'type':'boolean'}},'required':['connected'],'additionalProperties':False})
            results['openai']={'connected':True,'message':'Live API response verified','receipt':ai.receipt}
        except (httpx.HTTPError, ValueError, KeyError):
            results['openai']={'connected':False,'message':'OpenAI verification failed. Check the API key, model and available API credit.'}
    else: results['openai']={'connected':False,'message':'OpenAI API key is missing.'}
    try: results['supabase']=storage.health()
    except storage.StorageError as exc: results['supabase']={'connected':False,'message':str(exc)}
    return results

class SaveProjectInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    project:Project
    model_id:str=Field(max_length=60)
    project_id:UUID|None=None
    expected_version:int=Field(default=0,ge=0)
    note:str=Field(default='',max_length=1000)
    preview_name:str|None=None

@app.exception_handler(storage.StorageError)
async def storage_error(request:Request,exc):
    return JSONResponse(status_code=503,content={'detail':str(exc)})

@app.get('/api/projects')
def projects(): return storage.list_projects()

@app.post('/api/projects')
def save_project(data:SaveProjectInput):
    return storage.save_project(**data.model_dump(mode='json',exclude={'project'}), project=data.project)

@app.get('/api/projects/{project_id}/versions')
def versions(project_id:UUID):
    return storage.project_versions(str(project_id))

@app.get('/api/projects/{project_id}')
def open_project(project_id:str,version:int|None=Query(None,ge=1)):
    try: return storage.load_project(project_id,version)
    except ValueError: raise HTTPException(422,'The project identifier is invalid.')

@app.post('/api/export-preview')
async def export_preview(request:Request):
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>10*1024*1024:
            raise HTTPException(413,'The image is too large. Reduce the viewport size and try again.')
    if len(data)<33 or data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR':
        raise HTTPException(422,'A valid PNG preview is required.')
    width,height=struct.unpack('>II',data[16:24])
    if not (1<=width<=8192 and 1<=height<=8192):
        raise HTTPException(422,'The preview dimensions are unsupported.')
    name='prihoda-concept-'+uuid4().hex[:12]+'.png'
    try:
        EXPORTS.mkdir(parents=True,exist_ok=True)
        (EXPORTS/name).write_bytes(data)
    except OSError:
        raise HTTPException(503,'The PNG could not be saved. Check available disk space and try again.')
    return {'url':'/output/exports/'+name,'filename':name}

def readable(exc):
    if isinstance(exc,(ValidationError,RequestValidationError)):
        messages=[]
        for e in exc.errors():
            path='.'.join(str(p) for p in e['loc'] if p!='body')
            messages.append((path+': ' if path else '')+e['msg'].removeprefix('Value error, '))
        return ' '.join(messages[:4])
    return str(exc)

@app.exception_handler(RequestValidationError)
async def validation_error(request:Request,exc):
    return JSONResponse(status_code=422,content={'detail':readable(exc)})

@app.get('/api/status')
def status():
    engine=find_blender()
    return {'ok':True,'app':'prihoda-concept-studio','ai_mode':'openai' if isinstance(provider(),OpenAIProvider) else 'demo','blender_ready':bool(engine),'blender_name':Path(engine).parent.name if engine else None}

@app.get('/api/demo')
def demo(): return DEMO

@app.post('/api/parse')
def parse(request:TextRequest):
    try:
        result=provider().parse_customer_request(request.text)
        result['project']=result['project'].model_copy(update={'original_request':request.text})
        return result
    except (ValueError,ValidationError) as exc: raise HTTPException(422,readable(exc))
    except httpx.HTTPError: raise HTTPException(503,'The AI service is unavailable. Remove the API key to use deterministic Demo Mode, or try again.')
    except Exception:
        logging.exception('AI extraction failed')
        raise HTTPException(503,'The request could not be interpreted. Try a more specific description or enter parameters manually.')

@app.post('/api/modify')
def modify(request:ModifyRequest):
    try:
        ai=provider()
        patch=ai.modify_project(request.command,request.project)
        updated=apply_patch(request.project,patch)
        return {'project':updated,'changes':patch.changes,'receipt':getattr(ai,'receipt',{'provider':'demo'})}
    except (ValueError,ValidationError) as exc: raise HTTPException(422,readable(exc))
    except httpx.HTTPError: raise HTTPException(503,'The AI service is unavailable. Your concept is unchanged. Retry or use Demo Mode.')
    except Exception:
        logging.exception('AI modification failed')
        raise HTTPException(503,'The instruction could not be processed. Your concept is unchanged.')

@app.post('/api/validate')
def validate(project:Project): return {'valid':True,'project':project}

@app.post('/api/generate')
def make(project:Project,render:bool=Query(False)):
    try: return generate(project,render)
    except RuntimeError as exc: raise HTTPException(503,str(exc))

@app.get('/api/jobs/{key}')
def job(key:str):
    result=get_job(key)
    if not result: raise HTTPException(404,'This generation could not be found. Please generate the concept again.')
    return result
