"""Production only. Local development continues to use start.py."""
import os
import uvicorn

if __name__ == '__main__':
    # Never trust forwarded headers for authentication or enable a local bypass.
    os.environ['STUDIO_LOCAL_DEVELOPMENT'] = '0'
    uvicorn.run('backend.app.production:app', host='0.0.0.0',
                port=int(os.environ.get('PORT', '8080')), workers=1,
                proxy_headers=False, timeout_graceful_shutdown=30)
