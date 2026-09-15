import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/postcss'
import { fileURLToPath, URL } from 'node:url'
// Preserve the incoming host so FastAPI can distinguish a local preview from
// a request forwarded through another address. Vite's string shorthand rewrites it.
const studioProxy={
 '/api':{target:'http://127.0.0.1:8000',changeOrigin:false},
 '/output':{target:'http://127.0.0.1:8000',changeOrigin:false},
}
export default defineConfig({
 plugins:[react()],
 resolve:{alias:{'@':fileURLToPath(new URL('.',import.meta.url))}},
 css:{postcss:{plugins:[tailwindcss()]}},
 server:{host:'127.0.0.1',port:5173,strictPort:true,proxy:studioProxy},
 preview:{host:'127.0.0.1',port:5173,strictPort:true,proxy:studioProxy},
 build:{outDir:'dist',chunkSizeWarningLimit:1200}
})
