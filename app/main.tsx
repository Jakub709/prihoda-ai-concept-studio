import React from 'react'
import { createRoot } from 'react-dom/client'
import Landing from './landing'
import StudioAccess from './access'
import '@fontsource-variable/inter'
import './globals.css'
const isStudio = /^\/studio\/?$/.test(window.location.pathname)
document.documentElement.lang = isStudio ? 'en' : 'cs'
document.title = isStudio ? 'Studio · PŘÍHODA AI Concept Studio' : 'PŘÍHODA · AI Concept Studio — Dejte svému návrhu prostor'
createRoot(document.getElementById('root')!).render(<React.StrictMode>{isStudio?<StudioAccess/>:<Landing/>}</React.StrictMode>)
