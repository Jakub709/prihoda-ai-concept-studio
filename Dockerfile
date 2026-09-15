# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY tsconfig.json vite.config.ts index.html ./
COPY app ./app
COPY components ./components
COPY hooks ./hooks
COPY lib ./lib
COPY public ./public
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    STUDIO_DATA_DIR=/data STUDIO_LOCAL_DEVELOPMENT=0 \
    BLENDER_PATH=/opt/blender/blender BLENDER_RENDER_ENGINE=CYCLES
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl xz-utils libx11-6 libxi6 libxrender1 libxfixes3 \
    libxkbcommon0 libsm6 libice6 libgl1 libegl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp/blender-download
# Same Blender version as the locally verified generator; Linux x86_64 build.
RUN curl -fSL --retry 3 https://download.blender.org/release/Blender4.5/blender-4.5.0-linux-x64.tar.xz -o blender-4.5.0-linux-x64.tar.xz \
    && echo '1188b95cc12321c770b631939f7c25a096910b6f884a990bf9c0f62d52b38aec  blender-4.5.0-linux-x64.tar.xz' | sha256sum --check --strict - \
    && mkdir /opt/blender \
    && tar -xf blender-4.5.0-linux-x64.tar.xz --strip-components=1 -C /opt/blender \
    && /opt/blender/blender --background --version \
    && rm -rf /tmp/blender-download
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend ./backend
COPY blender ./blender
COPY supabase ./supabase
COPY projects/demo.json ./projects/demo.json
COPY serve.py ./
COPY --from=frontend /build/dist ./dist
# Verify native Blender + glTF export at build time; no keys or customer data.
RUN /opt/blender/blender --background --factory-startup --python-exit-code 1 \
    --python blender/generate_scene.py -- --project projects/demo.json --output demo-seed \
    && cp dist/demo/preview.png demo-seed/preview.png \
    && mkdir -p /data
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/api/health',timeout=4)"
CMD ["python", "serve.py"]
