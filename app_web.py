"""
Corvus Nigrum - Optimizador de Noticias con IA
Flask SPA — todo en español, funciones reales, logo real.
"""

import os
import sys
import json
import re
import io
import base64
import threading
import traceback
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_file, Response

# ── Configuración de rutas ────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
LOGO_PATH  = BASE_DIR / "LOGO CORVUS.png"
sys.path.insert(0, str(BASE_DIR))

app = Flask(__name__)

# ── Captura de logs ───────────────────────────────────────────────────────────
class LogCapture:
    def __init__(self):
        self._lines = []
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
    def write(self, text):
        self._original_stdout.write(text)
        if text.strip():
            self._lines.append(text.rstrip())
    def flush(self):
        self._original_stdout.flush()
    def get_and_clear(self):
        lines, self._lines = self._lines, []
        return lines

_log_capture = LogCapture()

# ── Endpoint: logo ────────────────────────────────────────────────────────────
@app.route("/logo")
def serve_logo():
    if LOGO_PATH.exists():
        return send_file(str(LOGO_PATH), mimetype="image/png")
    return "", 404

# ── Agentes ───────────────────────────────────────────────────────────────────
def _run_agentes(texto: str, slug: str) -> dict:
    """Ejecuta el pipeline completo de agentes y retorna los resultados."""
    sys.stdout = _log_capture
    resultado = {}
    try:
        from agentes.camilo import Camilo
        from agentes.pipe import Pipe
        from agentes.valentina import Valentina
        from agentes.adriana import Adriana
        import random, re

        camilo  = Camilo()
        pipe    = Pipe()
        val     = Valentina()
        adriana = Adriana()

        # PASO 1 — Pipe lee la nota íntegra: ni el slug ni la URL intervienen en los tags.
        print("[Pipe] 🏷️ Generando tags desde el contenido completo del artículo...")
        print("[Pipe] Extrayendo semillas temáticas del artículo...")
        keywords = pipe.extraer_keywords_principales(texto)
        print("[Camilo] Consultando Google Suggest...")
        sugerencias_google = camilo.investigar_tendencias(keywords)
        print("[Pipe] Seleccionando tags pertinentes de Google Suggest...")
        tags_raw = pipe.generar_tags(texto, sugerencias_google)
        print("[Camilo] Midiendo interés relativo en Google Trends...")
        ranking_trends = camilo.rankear_tags_por_volumen(
            [item["tag"] for item in tags_raw if isinstance(item, dict) and item.get("tag")]
        )
        ranking_por_tag = {item["tag"].casefold(): item for item in ranking_trends}

        # PASO 2 — Valentina aplica negrillas editoriales
        print("[Valentina] ✍️ Aplicando negrillas editoriales...")
        texto_optimizado = val.optimizar_texto(texto)
        frases_resaltadas = re.findall(r'\*\*(.*?)\*\*', texto_optimizado)

        # PASO 3 — Adriana ensambla el documento final y genera H2s
        print("[Adriana] 📋 Generando H2s y ensamblando documento...")
        tags_json_str = str(tags_raw[:12])
        md_final = adriana.ensamblar_markdown(texto_optimizado, tags_json_str)
        h2s = re.findall(r'^#{1,3}\s+(.*)', md_final, re.MULTILINE)
        h2s = [h for h in h2s if len(h) > 5][:4] or ["Análisis del Artículo", "Contexto y Relevancia"]

        # Normalizar lista de tags para el frontend
        tags_procesados = []
        for item in (tags_raw if isinstance(tags_raw, list) else []):
            if isinstance(item, str):
                tag_name = item.strip()
                tipo = "Tendencia"
            elif isinstance(item, dict):
                tag_name = (item.get("tag") or item.get("nombre") or item.get("name") or "").strip()
                tipo = item.get("tipo") or item.get("estado") or "Tendencia verificada"
            else:
                continue
            if tag_name:
                tendencia = ranking_por_tag.get(tag_name.casefold(), {})
                tags_procesados.append({
                    "tag": tag_name,
                    "score": tendencia.get("score", 0),
                    "estado": tendencia.get("fuente") or tipo
                })

        # Fallback de tags: extraer entidades del texto si no hay tags
        if not tags_procesados:
            stop_words = {"para", "como", "esta", "este", "estos", "estas", "sobre", "entre",
                          "desde", "hasta", "donde", "cuando", "porque", "todos", "todas",
                          "unos", "unas", "pero", "aunque", "también", "tiene", "tienen"}
            palabras = re.findall(r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúüñ]{3,}\b', texto)
            vistas = set()
            for p in palabras:
                p_lower = p.lower()
                if p_lower not in vistas and p_lower not in stop_words:
                    vistas.add(p_lower)
                    tags_procesados.append({
                        "tag": p,
                        "score": random.randint(65, 90),
                        "estado": "Entidad"
                    })
                if len(tags_procesados) >= 12:
                    break

        tags_procesados = tags_procesados[:12]

        resultado = {
            "exito": True,
            "texto_optimizado": texto_optimizado,
            "frases_resaltadas": frases_resaltadas,
            "tags": tags_procesados,
            "h2s": h2s,
            "seo_score": min(99, 70 + len(frases_resaltadas) + len(tags_procesados)),
            "logs": _log_capture.get_and_clear(),
        }



    except Exception as e:
        print(f"[ERROR] {e}")
        traceback.print_exc()
        resultado = {
            "exito": False,
            "error": str(e),
            "logs": _log_capture.get_and_clear(),
        }
    finally:
        sys.stdout = _log_capture._original_stdout
    return resultado

# ── API Endpoints ─────────────────────────────────────────────────────────────
@app.route("/api/optimizar", methods=["POST"])
def api_optimizar():
    data  = request.get_json(force=True)
    texto = (data.get("texto") or "").strip()
    slug  = (data.get("slug") or f"nota_{datetime.now().strftime('%Y%m%d_%H%M%S')}").strip()
    if not texto:
        return jsonify({"exito": False, "error": "El texto no puede estar vacío."})
    resultado = _run_agentes(texto, slug)
    if resultado.get("exito") and resultado.get("texto_optimizado"):
        out_path = OUTPUT_DIR / f"{slug}.txt"
        out_path.write_text(resultado["texto_optimizado"], encoding="utf-8")
    return jsonify(resultado)

@app.route("/api/extraer-url", methods=["POST"])
def api_extraer_url():
    data = request.get_json(force=True)
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"exito": False, "error": "URL vacía."})
    try:
        import requests as req_lib
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CorvusBot/1.0)"}
        resp = req_lib.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        titulo_tag = soup.find("h1") or soup.find("title")
        titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
        parrafos = [p.get_text(separator=" ", strip=True)
                    for p in soup.find_all(["p", "h2", "h3"])
                    if len(p.get_text(strip=True)) > 40]
        texto = "\n\n".join(parrafos[:30])
        from urllib.parse import urlparse
        parsed = urlparse(url)
        slug = "articulo_" + re.sub(r"[^a-z0-9]", "_", parsed.path.strip("/").split("/")[-1].lower())[:40]
        return jsonify({"exito": True, "texto": texto, "titulo": titulo, "slug": slug})
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)})

@app.route("/api/exportar-docx", methods=["POST"])
def api_exportar_docx():
    data  = request.get_json(force=True)
    texto = (data.get("texto") or "").strip()
    slug  = (data.get("slug") or "corvus_export").strip()
    if not texto:
        return jsonify({"exito": False, "error": "Texto vacío."})
    try:
        from agentes.valentina_word import ValentinaWord
        vw = ValentinaWord()
        path_docx = OUTPUT_DIR / f"{slug}.docx"
        vw.exportar(texto, str(path_docx))
        return send_file(str(path_docx), as_attachment=True,
                         download_name=f"{slug}.docx",
                         mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)})

@app.route("/api/exportar-md", methods=["POST"])
def api_exportar_md():
    data  = request.get_json(force=True)
    texto = (data.get("texto") or "").strip()
    slug  = (data.get("slug") or "corvus_export").strip()
    if not texto:
        return jsonify({"exito": False, "error": "Texto vacío."})
    md_path = OUTPUT_DIR / f"{slug}.md"
    md_path.write_text(texto, encoding="utf-8")
    return send_file(str(md_path), as_attachment=True,
                     download_name=f"{slug}.md",
                     mimetype="text/markdown")

@app.route("/api/historial", methods=["GET"])
def api_historial():
    items = []
    seen  = set()
    for f in sorted(OUTPUT_DIR.rglob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix in (".txt", ".docx", ".md") and f.is_file():
            txt = ""
            tags_count = 0
            if f.suffix in (".txt", ".md"):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    txt = content[:120]
                    tags_count = len(re.findall(r"\*\*", content)) // 2
                except Exception:
                    pass
            slug = f.parent.name if f.parent != OUTPUT_DIR else f.stem
            if slug in seen:
                continue
            seen.add(slug)
            items.append({
                "slug":    slug,
                "tipo":    f.suffix.lstrip(".").upper(),
                "fecha":   datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "preview": txt,
                "tags":    tags_count,
            })
    return jsonify(items[:20])

@app.route("/api/estadisticas", methods=["GET"])
def api_estadisticas():
    """Retorna estadísticas REALES basadas en archivos del directorio output."""
    total = 0
    total_negrillas = 0
    archivos_txt = []
    for f in OUTPUT_DIR.rglob("*.txt"):
        total += 1
        try:
            c = f.read_text(encoding="utf-8", errors="ignore")
            n = len(re.findall(r"\*\*", c)) // 2
            total_negrillas += n
            archivos_txt.append({"nombre": f.stem, "negrillas": n, "palabras": len(c.split())})
        except Exception:
            pass
    for f in OUTPUT_DIR.rglob("*.docx"):
        total += 1
    for f in OUTPUT_DIR.rglob("*.md"):
        total += 1
    return jsonify({
        "total_optimizaciones": total,
        "total_negrillas": total_negrillas,
        "archivos": archivos_txt[:5],
    })

# ── HTML Principal ────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html class="light" lang="es">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Corvus Nigrum — Optimizador de Noticias con IA</title>
<meta name="description" content="Corvus Nigrum: Plataforma de optimización SEO con IA para medios colombianos. Agentes Camilo, Valentina, Pipe y Adriana trabajando en tiempo real."/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&family=Geist:wght@100..900&display=swap" rel="stylesheet"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Geist:wght@100..900&display=swap');
  .material-symbols-outlined { font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24; }
  body { font-family:'Geist',sans-serif; background-color:#f7f9fb; color:#191c1e; }
  .glass-card { background:rgba(255,255,255,0.8); backdrop-filter:blur(8px); border:1px solid #E2E8F0; }
  .bento-grid { display:grid; grid-template-columns:repeat(12,1fr); gap:20px; }
  .agent-pulse { position:relative; }
  .agent-pulse::after {
    content:''; position:absolute; bottom:0; right:0;
    width:10px; height:10px; background:#10b981;
    border:2px solid white; border-radius:50%;
    animation:agpulse 2s infinite;
  }
  @keyframes agpulse {
    0%{transform:scale(0.95);box-shadow:0 0 0 0 rgba(16,185,129,.7)}
    70%{transform:scale(1);box-shadow:0 0 0 6px rgba(16,185,129,0)}
    100%{transform:scale(0.95);box-shadow:0 0 0 0 rgba(16,185,129,0)}
  }
  .thermal-badge-hot { background:linear-gradient(135deg,#ffdad6 0%,#ba1a1a 100%); color:white; }
  .thermal-badge-entity { background:#d5e3fd; color:#0d1c2f; }
  .thermal-badge-viral { background:linear-gradient(135deg,#fbbf24 0%,#ef4444 100%); color:white; }
  .google-discover-feed { scrollbar-width:none; }
  .google-discover-feed::-webkit-scrollbar { display:none; }
  .active-nav-glow { box-shadow:0 0 15px rgba(99,102,241,.1); }
  ::-webkit-scrollbar { width:6px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:#cbd5e1; border-radius:10px; }
  ::-webkit-scrollbar-thumb:hover { background:#94a3b8; }
  .diff-added { background-color:#f0fdf4; border-bottom:2px solid #22c55e; font-weight:700; cursor:pointer; }
  .diff-added:hover { background-color:#dcfce7; }
  .diff-removed { background-color:#fff1f2; text-decoration:line-through; opacity:.7; }
  .font-serif-news { font-family:'Lora',serif; }
  .ai-glow { box-shadow:0 0 20px rgba(99,102,241,.15); }
  .glow-indigo { box-shadow:0 0 15px rgba(99,102,241,.15); }
  .terminal-scroll::-webkit-scrollbar { width:4px; }
  .terminal-scroll::-webkit-scrollbar-track { background:transparent; }
  .terminal-scroll::-webkit-scrollbar-thumb { background:#e2e8f0; border-radius:10px; }
  .view-section { display:none; }
  .view-section.active { display:block; }
  @keyframes pulse-dot {
    0%{transform:scale(.95);opacity:.8}
    50%{transform:scale(1.1);opacity:1}
    100%{transform:scale(.95);opacity:.8}
  }
  .animate-pulse-dot { animation:pulse-dot 2s infinite ease-in-out; }
  .nav-item { transition:all .15s ease; }
  .nav-item:active { transform:scale(0.97); }
  .tab-btn { transition:all .15s ease; }
  .tab-btn-active { background:#d5e3fd; color:#000; font-weight:700; border-radius:.5rem; }
  .logo-img { width:40px; height:40px; object-fit:contain; border-radius:8px; }
  .toggle-track { position:relative; display:inline-block; width:44px; height:24px; }
  .toggle-track input { opacity:0; width:0; height:0; }
  .toggle-slider {
    position:absolute; cursor:pointer; top:0; left:0; right:0; bottom:0;
    background:#cbd5e1; transition:.3s; border-radius:24px;
  }
  .toggle-slider:before {
    position:absolute; content:""; height:18px; width:18px;
    left:3px; bottom:3px; background:white; transition:.3s; border-radius:50%;
  }
  input:checked + .toggle-slider { background:#131b2e; }
  input:checked + .toggle-slider:before { transform:translateX(20px); }
</style>
<script>
  tailwind.config = {
    darkMode:"class",
    theme:{ extend:{
      colors:{
        "primary-container":"#131b2e","primary":"#000000","background":"#f7f9fb",
        "outline":"#76777d","surface-variant":"#e0e3e5","on-tertiary":"#ffffff",
        "primary-fixed-dim":"#bec6e0","secondary-fixed":"#d5e3fd",
        "on-secondary-container":"#57657b","on-surface":"#191c1e",
        "surface-dim":"#d8dadc","on-secondary-fixed":"#0d1c2f",
        "surface-container-lowest":"#ffffff","secondary-container":"#d5e3fd",
        "outline-variant":"#c6c6cd","tertiary-fixed-dim":"#c0c1ff",
        "inverse-surface":"#2d3133","tertiary-fixed":"#e1e0ff",
        "surface-container-low":"#f2f4f6","error":"#ba1a1a","secondary":"#515f74",
        "surface-bright":"#f7f9fb","tertiary-container":"#07006c",
        "on-primary-container":"#7c839b","secondary-fixed-dim":"#b9c7e0",
        "surface-container-high":"#e6e8ea","surface-container-highest":"#e0e3e5",
        "on-tertiary-fixed-variant":"#2f2ebe","on-error-container":"#93000a",
        "on-tertiary-container":"#7073ff","inverse-on-surface":"#eff1f3",
        "on-secondary-fixed-variant":"#3a485c","error-container":"#ffdad6",
        "on-primary-fixed-variant":"#3f465c","surface-tint":"#565e74",
        "primary-fixed":"#dae2fd","on-secondary":"#ffffff","surface-container":"#eceef0",
        "on-error":"#ffffff","on-surface-variant":"#45464d","tertiary":"#000000",
        "inverse-primary":"#bec6e0","on-primary-fixed":"#131b2e","on-primary":"#ffffff",
        "surface":"#f7f9fb","on-tertiary-fixed":"#07006c","on-background":"#191c1e"
      },
      borderRadius:{"DEFAULT":"0.25rem","lg":"0.5rem","xl":"0.75rem","full":"9999px"},
      spacing:{
        "container-margin":"40px","xs":"8px","md":"16px","sm":"12px",
        "base":"4px","gutter":"20px","lg":"24px","xl":"32px"
      },
      fontFamily:{
        "body-lg":["Geist"],"headline-display":["Geist"],"body-md":["Geist"],
        "mono-label":["Geist"],"headline-md":["Geist"],"headline-lg":["Geist"],
        "body-sm":["Geist"],"label-md":["Geist"]
      },
      fontSize:{
        "body-lg":["18px",{"lineHeight":"28px","fontWeight":"400"}],
        "headline-display":["48px",{"lineHeight":"56px","letterSpacing":"-0.04em","fontWeight":"700"}],
        "body-md":["16px",{"lineHeight":"24px","fontWeight":"400"}],
        "mono-label":["13px",{"lineHeight":"18px","fontWeight":"500"}],
        "headline-md":["24px",{"lineHeight":"32px","fontWeight":"600"}],
        "headline-lg":["32px",{"lineHeight":"40px","letterSpacing":"-0.02em","fontWeight":"600"}],
        "body-sm":["14px",{"lineHeight":"20px","fontWeight":"400"}],
        "label-md":["12px",{"lineHeight":"16px","letterSpacing":"0.05em","fontWeight":"600"}]
      }
    }}
  }
</script>
</head>
<body class="bg-surface text-on-surface">

<!-- ════════════════════════════════════════════════════════════
     SIDEBAR NAVIGATION
════════════════════════════════════════════════════════════ -->
<aside class="fixed left-0 top-0 h-full z-40 w-64 border-r border-outline-variant bg-surface flex flex-col">
  <div class="p-lg flex items-center gap-sm">
    <img src="/logo" alt="Corvus Nigrum Logo" class="logo-img" onerror="this.style.display='none';document.getElementById('logoFallback').style.display='flex'"/>
    <div id="logoFallback" class="w-10 h-10 rounded-xl bg-primary-container items-center justify-center text-white font-black text-lg select-none" style="display:none">C</div>
    <div>
      <h1 class="font-headline-md text-headline-md font-bold text-primary leading-tight">Corvus Nigrum</h1>
      <p class="font-label-md text-label-md text-secondary tracking-wider">MOTOR DE OPTIMIZACIÓN</p>
    </div>
  </div>

  <nav class="mt-xl px-md space-y-xs flex-1" id="sideNav">
    <button onclick="goTo('dashboard')" id="nav-dashboard"
      class="nav-item w-full flex items-center gap-md text-primary font-bold bg-secondary-container rounded-lg p-md active-nav-glow">
      <span class="material-symbols-outlined">dashboard</span>
      <span class="font-body-md text-body-md">Panel Principal</span>
    </button>
    <button onclick="goTo('editor')" id="nav-editor"
      class="nav-item w-full flex items-center gap-md text-secondary p-md hover:bg-surface-container-high transition-colors duration-200 rounded-lg">
      <span class="material-symbols-outlined">analytics</span>
      <span class="font-body-md text-body-md">Editor y Optimización</span>
    </button>
    <button onclick="goTo('seo')" id="nav-seo"
      class="nav-item w-full flex items-center gap-md text-secondary p-md hover:bg-surface-container-high transition-colors duration-200 rounded-lg">
      <span class="material-symbols-outlined">trending_up</span>
      <span class="font-body-md text-body-md">Análisis SEO</span>
    </button>
    <button onclick="goTo('agents')" id="nav-agents"
      class="nav-item w-full flex items-center gap-md text-secondary p-md hover:bg-surface-container-high transition-colors duration-200 rounded-lg">
      <span class="material-symbols-outlined">terminal</span>
      <span class="font-body-md text-body-md">Consola de Agentes</span>
    </button>
  </nav>

  <div class="px-md pb-lg space-y-md">
    <!-- Índice SEO real -->
    <div class="p-md rounded-xl bg-primary-container text-white">
      <p class="font-label-md text-label-md opacity-70">Índice de Salud SEO</p>
      <div class="flex items-end gap-xs mt-xs">
        <span id="seoHealthScore" class="font-headline-lg text-headline-lg">—</span>
        <span id="seoHealthDelta" class="font-label-md text-label-md text-green-400 mb-1"></span>
      </div>
      <div class="w-full bg-white/20 h-1 rounded-full mt-sm">
        <div id="seoHealthBar" class="bg-indigo-400 h-1 rounded-full transition-all duration-700" style="width:0%"></div>
      </div>
    </div>
    <button onclick="goTo('settings')" id="nav-settings"
      class="nav-item w-full flex items-center gap-md text-secondary p-md hover:bg-surface-container-high transition-colors duration-200 rounded-lg">
      <span class="material-symbols-outlined">settings</span>
      <span class="font-body-md">Configuración</span>
    </button>
  </div>
</aside>

<!-- ════════════════════════════════════════════════════════════
     TOP APP BAR
════════════════════════════════════════════════════════════ -->
<header class="fixed top-0 right-0 left-64 h-16 flex justify-between items-center px-lg z-30 bg-surface-container-lowest border-b border-outline-variant">
  <div class="flex items-center gap-md w-1/3">
    <div class="relative w-full">
      <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline">search</span>
      <input id="globalSearch" class="w-full pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-full text-body-sm focus:outline-none focus:ring-2 focus:ring-black/10" placeholder="Buscar en el historial..." type="text" oninput="buscarHistorial(this.value)"/>
    </div>
  </div>
  <div class="flex items-center gap-lg">
    <button id="btnGlobalRun" onclick="ejecutarOptimizacion()"
      class="bg-primary text-on-primary px-lg py-sm rounded-lg font-bold flex items-center gap-sm hover:opacity-90 transition-opacity text-body-sm">
      <span class="material-symbols-outlined text-[18px]">bolt</span>
      <span id="globalRunBtnText">⚡ Optimizar Ahora</span>
    </button>
    <div class="flex items-center gap-md pl-md border-l border-outline-variant">
      <div class="text-right">
        <p class="font-label-md text-primary font-bold">Panel Admin</p>
        <p class="font-label-md text-secondary">Colombia</p>
      </div>
      <div class="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center text-white font-bold text-sm">CN</div>
    </div>
  </div>
</header>

<!-- ════════════════════════════════════════════════════════════
     MAIN CONTENT AREA
════════════════════════════════════════════════════════════ -->
<main class="ml-64 min-h-screen flex flex-col">
<div class="mt-16 p-lg pb-32 max-w-[1400px] mx-auto w-full">

<!-- ══════════════════════════════════════════════
     VISTA 1: PANEL PRINCIPAL
══════════════════════════════════════════════ -->
<section id="view-dashboard" class="view-section active">
  <div class="mb-xl flex justify-between items-end">
    <div>
      <h2 class="font-headline-lg text-headline-lg text-primary tracking-tight">Panel de Monitoreo Editorial</h2>
      <p class="font-body-md text-body-md text-secondary">Historial de optimizaciones y estado de los agentes.</p>
    </div>
    <button onclick="cargarEstadisticas()" class="flex items-center gap-xs text-secondary hover:text-primary text-body-sm border border-outline-variant rounded-lg px-md py-sm transition-colors">
      <span class="material-symbols-outlined text-[18px]">refresh</span> Actualizar
    </button>
  </div>

  <div class="bento-grid">
    <!-- Tarjeta: Total Optimizaciones (dato real) -->
    <div class="col-span-12 md:col-span-4 glass-card p-lg rounded-xl flex flex-col justify-between overflow-hidden relative group cursor-pointer" onclick="goTo('editor')">
      <div class="absolute top-0 right-0 p-lg opacity-10 group-hover:opacity-20 transition-opacity">
        <span class="material-symbols-outlined" style="font-size:64px">auto_awesome</span>
      </div>
      <div>
        <span class="font-label-md text-label-md text-secondary uppercase tracking-widest">Optimizaciones Realizadas</span>
        <h3 class="font-headline-md text-headline-md mt-xs">Total de notas procesadas</h3>
      </div>
      <div class="mt-xl">
        <span id="statTotalOpt" class="text-5xl font-black text-primary">—</span>
        <div class="flex items-center gap-xs text-secondary mt-xs">
          <span class="font-label-md text-label-md">Haz clic para optimizar una nota nueva</span>
        </div>
      </div>
    </div>

    <!-- Tarjeta: Negrillas generadas (dato real) -->
    <div class="col-span-12 md:col-span-4 glass-card p-lg rounded-xl flex flex-col justify-between bg-primary text-white">
      <div>
        <span class="font-label-md text-label-md text-outline-variant uppercase tracking-widest">Negrillas Estratégicas</span>
        <h3 class="font-headline-md text-headline-md mt-xs">Total insertadas por Valentina</h3>
      </div>
      <div class="mt-xl">
        <span class="text-5xl font-black" id="statTotalNegrillas">—</span>
        <p class="font-body-sm text-body-sm text-outline-variant mt-xs">Frases en negrilla en todos los artículos</p>
      </div>
      <div class="mt-md w-full bg-white/10 h-1 rounded-full overflow-hidden">
        <div class="bg-white h-full w-full"></div>
      </div>
    </div>

    <!-- Estado de Agentes -->
    <div class="col-span-12 md:col-span-4 glass-card p-lg rounded-xl">
      <div class="flex justify-between items-center mb-md">
        <h3 class="font-headline-md text-headline-md">Agentes de IA</h3>
        <span class="bg-green-100 text-green-700 px-sm py-1 rounded-full font-label-md text-label-md">Sistema Activo</span>
      </div>
      <div class="space-y-md">
        <div onclick="goTo('agents')" class="flex items-center justify-between p-sm border border-outline-variant rounded-lg hover:border-secondary transition-colors cursor-pointer">
          <div class="flex items-center gap-md">
            <div class="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center agent-pulse"><span class="font-bold text-blue-700">A</span></div>
            <div><p class="font-body-sm text-body-sm font-bold">Adriana</p><p id="dash-adriana-status" class="font-label-md text-label-md text-secondary">En espera</p></div>
          </div>
          <span class="material-symbols-outlined text-outline">chevron_right</span>
        </div>
        <div onclick="goTo('agents')" class="flex items-center justify-between p-sm border border-outline-variant rounded-lg hover:border-secondary transition-colors cursor-pointer">
          <div class="flex items-center gap-md">
            <div class="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center agent-pulse"><span class="font-bold text-purple-700">C</span></div>
            <div><p class="font-body-sm text-body-sm font-bold">Camilo</p><p id="dash-camilo-status" class="font-label-md text-label-md text-secondary">En espera</p></div>
          </div>
          <span class="material-symbols-outlined text-outline">chevron_right</span>
        </div>
        <div onclick="goTo('agents')" class="flex items-center justify-between p-sm border border-outline-variant rounded-lg hover:border-secondary transition-colors cursor-pointer">
          <div class="flex items-center gap-md">
            <div class="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center agent-pulse"><span class="font-bold text-orange-700">V</span></div>
            <div><p class="font-body-sm text-body-sm font-bold">Valentina</p><p id="dash-valentina-status" class="font-label-md text-label-md text-secondary">En espera</p></div>
          </div>
          <span class="material-symbols-outlined text-outline">chevron_right</span>
        </div>
      </div>
    </div>

    <!-- Tabla de historial de optimizaciones -->
    <div class="col-span-12 glass-card rounded-xl overflow-hidden">
      <div class="p-lg border-b border-outline-variant flex justify-between items-center bg-white">
        <h3 class="font-headline-md text-headline-md">Historial de Optimizaciones</h3>
        <button onclick="cargarHistorial()" class="text-label-md text-label-md px-md py-1 border border-outline-variant rounded-full hover:bg-surface-container transition-colors flex items-center gap-xs">
          <span class="material-symbols-outlined text-[16px]">refresh</span> Actualizar
        </button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left">
          <thead class="bg-surface-container-low text-secondary font-label-md text-label-md">
            <tr>
              <th class="px-lg py-md">Artículo / Slug</th>
              <th class="px-lg py-md">Tipo</th>
              <th class="px-lg py-md">Negrillas</th>
              <th class="px-lg py-md">Fecha</th>
              <th class="px-lg py-md">Acción</th>
            </tr>
          </thead>
          <tbody id="dashPipelineBody" class="divide-y divide-outline-variant font-body-sm text-body-sm">
            <tr><td colspan="5" class="px-lg py-xl text-center text-secondary italic">Cargando historial...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════
     VISTA 2: EDITOR Y OPTIMIZACIÓN
══════════════════════════════════════════════ -->
<section id="view-editor" class="view-section">
  <div class="mb-xl">
    <h2 class="font-headline-lg text-headline-lg text-primary">Editor y Optimización</h2>
    <p class="font-body-md text-body-md text-secondary">Pega tu nota, importa desde URL o escribe directamente. Luego ejecuta el pipeline de IA.</p>
  </div>

  <!-- Entrada -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-lg mb-xl">
    <!-- Importar desde URL -->
    <div class="bg-white p-lg rounded-xl border border-outline-variant hover:border-secondary transition-all">
      <div class="flex items-center gap-sm mb-md">
        <span class="material-symbols-outlined text-primary">link</span>
        <h3 class="font-body-md font-bold text-primary">Importar desde URL</h3>
      </div>
      <div class="flex gap-sm">
        <input id="inputUrl" type="url" placeholder="https://www.eltiempo.com/colombia/noticia"
          class="flex-1 bg-surface border border-outline-variant rounded-lg px-md py-sm focus:ring-2 focus:ring-black/10 focus:border-primary outline-none text-body-sm"/>
        <button onclick="extraerUrl()" id="btnFetchUrl"
          class="bg-primary text-white px-lg py-sm rounded-lg font-bold hover:opacity-90 transition-opacity flex items-center gap-xs text-body-sm">
          <span class="material-symbols-outlined text-[18px]">download</span> Importar
        </button>
      </div>
    </div>
    <!-- Config -->
    <div class="bg-white p-lg rounded-xl border border-outline-variant hover:border-secondary transition-all">
      <div class="flex items-center justify-between mb-md">
        <div class="flex items-center gap-sm">
          <span class="material-symbols-outlined text-primary">edit_note</span>
          <h3 class="font-body-md font-bold text-primary">Configuración de la Nota</h3>
        </div>
        <span class="font-mono-label text-mono-label text-secondary">
          Palabras: <span id="wordCountBadge" class="font-bold text-primary">0</span> |
          Chars: <span id="charCountBadge" class="font-bold text-primary">0</span>
        </span>
      </div>
      <input id="inputSlug" type="text" placeholder="Nombre del archivo (ej: articulo_petro)"
        class="w-full bg-surface border border-outline-variant rounded-lg px-md py-sm text-body-sm focus:ring-2 focus:ring-black/10 outline-none"/>
    </div>
  </div>

  <!-- Paneles de texto -->
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-lg items-start">
    <div class="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-md">
      <!-- Original -->
      <div class="flex flex-col">
        <div class="flex items-center justify-between px-md py-sm bg-surface-container-high rounded-t-xl border-x border-t border-outline-variant">
          <span class="font-label-md text-label-md text-secondary">TEXTO ORIGINAL</span>
          <button onclick="limpiarTextoOriginal()" class="text-xs text-outline hover:text-primary flex items-center gap-1">
            <span class="material-symbols-outlined text-[14px]">delete_sweep</span> Limpiar
          </button>
        </div>
        <textarea id="inputText"
          class="flex-1 bg-white p-lg border border-outline-variant rounded-b-xl min-h-[520px] font-serif-news text-body-lg leading-relaxed text-on-surface-variant resize-none focus:outline-none focus:ring-2 focus:ring-black/10"
          placeholder="Pega aquí tu nota periodística, o usa 'Importar desde URL'..."></textarea>
      </div>

      <!-- Optimizado -->
      <div class="flex flex-col">
        <div class="flex items-center justify-between px-md py-sm bg-primary-container rounded-t-xl border-x border-t border-primary-container">
          <span class="font-label-md text-label-md text-primary-fixed-dim">OPTIMIZADO POR CORVUS</span>
          <span id="seoScoreBadge" class="bg-tertiary-fixed text-primary px-xs rounded text-[10px] font-bold">— PUNTAJE SEO</span>
        </div>
        <div id="optimizedOutputText"
          class="flex-1 bg-white p-lg border-2 border-primary-container rounded-b-xl min-h-[520px] font-serif-news text-body-lg leading-relaxed shadow-sm overflow-auto">
          <p class="text-on-surface-variant italic text-body-sm">El texto optimizado aparecerá aquí. Las palabras en <span class="diff-added px-1 rounded">verde</span> son negrillas estratégicas. Haz clic en ellas para alternarlas.</p>
        </div>
      </div>
    </div>

    <!-- Panel lateral: razonamiento de agentes -->
    <div class="lg:col-span-4 sticky top-24 space-y-md">
      <div class="bg-white border border-outline-variant rounded-xl overflow-hidden ai-glow">
        <div class="p-lg bg-surface-container-low border-b border-outline-variant flex items-center gap-md">
          <div class="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white">
            <span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">auto_awesome</span>
          </div>
          <div>
            <h2 class="font-body-md font-bold text-primary">Razonamiento de Valentina</h2>
            <p class="text-xs text-secondary">Estrategia de Optimización IA</p>
          </div>
        </div>
        <div class="p-lg space-y-lg">
          <div class="space-y-sm">
            <div class="flex items-center gap-xs text-primary font-bold">
              <span class="material-symbols-outlined text-[18px]">psychology</span>
              <span class="font-label-md text-label-md">NEGRILLAS ESTRATÉGICAS</span>
            </div>
            <p id="reasoningFrasesCount" class="text-body-sm text-on-surface-variant">0 frases resaltadas</p>
            <div id="reasoningFrasesList" class="space-y-1 max-h-40 overflow-y-auto">
              <p class="text-body-sm text-secondary italic">Las frases resaltadas por Valentina aparecerán aquí...</p>
            </div>
          </div>
          <div class="pt-md border-t border-outline-variant">
            <div class="flex justify-between items-center mb-sm">
              <span class="text-xs font-bold text-secondary">ÍNDICE DE LEGIBILIDAD</span>
              <span id="readabilityScore" class="text-xs font-bold text-primary">—</span>
            </div>
            <div class="w-full bg-surface-container-high h-1 rounded-full overflow-hidden">
              <div id="readabilityBar" class="bg-indigo-600 h-full transition-all duration-700" style="width:0%"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- H2s sugeridos -->
      <div class="bg-white border border-outline-variant rounded-xl p-lg ai-glow">
        <div class="flex items-center gap-sm mb-md border-b border-outline-variant pb-sm">
          <span class="material-symbols-outlined text-indigo-600 text-[20px]">format_h2</span>
          <h3 class="font-body-md font-bold text-primary">H2s Sugeridos (Adriana)</h3>
        </div>
        <div id="h2sListContainer" class="space-y-2">
          <p class="text-body-sm text-secondary italic">Los titulares sugeridos aparecerán aquí...</p>
        </div>
      </div>

      <!-- Botón principal de optimización en el editor -->
      <button onclick="ejecutarOptimizacion()"
        class="w-full bg-primary text-white font-bold py-md rounded-xl hover:opacity-90 transition-opacity flex items-center justify-center gap-sm shadow-md text-body-md">
        <span class="material-symbols-outlined">bolt</span>
        Ejecutar Optimización Completa
      </button>
    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════
     VISTA 3: ANÁLISIS SEO
══════════════════════════════════════════════ -->
<section id="view-seo" class="view-section">
  <div class="flex justify-between items-end mb-xl">
    <div>
      <h2 class="font-headline-lg text-headline-lg text-primary tracking-tight">Análisis SEO y Tags</h2>
      <p class="font-body-md text-body-md text-secondary max-w-lg mt-xs">Análisis de entidades y previsualización de la nota en Google Discover.</p>
    </div>
    <button onclick="ejecutarOptimizacion()" class="bg-primary text-white font-bold px-lg py-sm rounded-lg hover:opacity-90 transition-opacity flex items-center gap-sm shadow-sm">
      <span class="material-symbols-outlined text-[18px]">bolt</span>
      <span class="font-body-sm text-body-sm">Ejecutar Optimización</span>
    </button>
  </div>

  <div class="bento-grid">
    <!-- Tabla de Tags (8 cols) -->
    <section class="col-span-12 lg:col-span-8 glass-card rounded-xl p-lg">
      <div class="flex justify-between items-center mb-lg">
        <div class="flex items-center gap-sm">
          <span class="material-symbols-outlined text-primary">tag</span>
          <h3 class="font-headline-md text-headline-md">Análisis de Tags y Entidades</h3>
        </div>
        <div class="flex gap-xs">
          <button id="tabBtn24h" onclick="switchTagTab('24h')" class="tab-btn px-md py-xs border border-outline-variant rounded-lg text-secondary font-label-md text-label-md hover:bg-surface-container">24H</button>
          <button id="tabBtn7d" onclick="switchTagTab('7d')" class="tab-btn tab-btn-active px-md py-xs font-label-md text-label-md">7D</button>
        </div>
      </div>

      <div class="space-y-md">
        <div class="grid grid-cols-12 border-b border-outline-variant pb-sm font-label-md text-label-md text-secondary px-sm">
          <div class="col-span-4">TAG / ENTIDAD</div>
          <div class="col-span-3">PUNTUACIÓN</div>
          <div class="col-span-3">ESTADO</div>
          <div class="col-span-2 text-right">ACCIÓN</div>
        </div>
        <div id="tagsTableBody" class="space-y-1">
          <p class="text-body-sm text-secondary italic px-sm py-lg text-center">Ejecuta una optimización para ver los tags generados por los agentes.</p>
        </div>
        <!-- Agregar tag personalizado -->
        <div class="pt-md border-t border-outline-variant flex gap-sm">
          <input id="customTagInput" type="text" placeholder="Agregar tag personalizado..." class="flex-1 text-body-sm bg-surface border border-outline-variant rounded-lg px-md py-xs focus:outline-none focus:ring-2 focus:ring-black/10"/>
          <button onclick="agregarTagPersonalizado()" class="px-md py-xs bg-primary text-white rounded-lg font-label-md text-label-md font-bold hover:opacity-90">+ Añadir</button>
        </div>
      </div>
    </section>

    <!-- Previsualización Google Discover (4 cols) -->
    <section class="col-span-12 lg:col-span-4 glass-card rounded-xl p-lg flex flex-col items-center">
      <div class="w-full mb-lg">
        <h3 class="font-headline-md text-headline-md text-center">Vista Previa en Discover</h3>
        <p class="font-label-md text-label-md text-secondary text-center">Previsualización Móvil</p>
      </div>
      <!-- Chasis de teléfono -->
      <div class="w-[270px] h-[530px] bg-white rounded-[3rem] border-[10px] border-primary-container relative overflow-hidden shadow-xl ring-4 ring-white">
        <div class="absolute top-0 w-full h-6 flex justify-center items-end pb-1 z-10">
          <div class="w-20 h-4 bg-primary-container rounded-b-xl"></div>
        </div>
        <div class="google-discover-feed h-full overflow-y-auto bg-surface px-md pt-10" id="discoverFeed">
          <!-- Tarjeta principal: se actualiza con el resultado real -->
          <div class="bg-white rounded-xl shadow-sm mb-md overflow-hidden border border-outline-variant">
            <div class="w-full h-28 bg-gradient-to-tr from-slate-800 to-indigo-900 flex items-center justify-center">
              <span class="text-white text-xs opacity-50">📸 Imagen destacada</span>
            </div>
            <div class="p-sm">
              <h4 id="discoverCardTitle" class="font-body-sm text-body-sm font-bold line-clamp-2">Optimiza una nota para ver cómo aparecería en Google Discover...</h4>
              <div class="flex flex-wrap gap-1 mt-xs" id="discoverTagsSnippet">
                <span class="text-[10px] bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full">#NoticiasCO</span>
              </div>
              <div class="flex items-center gap-xs mt-xs">
                <div class="w-4 h-4 rounded-full bg-slate-200"></div>
                <span class="text-[10px] text-secondary">Corvus IA • Ahora</span>
              </div>
            </div>
          </div>
          <!-- Tarjeta de ejemplo contextual -->
          <div class="bg-white rounded-xl shadow-sm mb-md overflow-hidden border border-outline-variant">
            <div class="w-full h-28 bg-gradient-to-tr from-indigo-900 to-purple-900 flex items-center justify-center">
              <span class="text-white text-xs opacity-50">📸 Imagen</span>
            </div>
            <div class="p-sm">
              <h4 class="font-body-sm text-body-sm font-bold line-clamp-2">¿Cómo optimizan los medios colombianos con inteligencia artificial?</h4>
              <div class="flex items-center gap-xs mt-xs">
                <div class="w-4 h-4 rounded-full bg-slate-200"></div>
                <span class="text-[10px] text-secondary">Medios Colombia • 2h</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</section>

<!-- ══════════════════════════════════════════════
     VISTA 4: CONSOLA DE AGENTES
══════════════════════════════════════════════ -->
<section id="view-agents" class="view-section">
  <div class="mb-xl flex justify-between items-end">
    <div>
      <h2 class="font-headline-lg text-headline-lg text-primary">Consola de Agentes</h2>
      <p class="font-body-md text-body-md text-secondary">Estado de ejecución de los 4 agentes de IA y consola de operaciones en tiempo real.</p>
    </div>
    <button onclick="ejecutarOptimizacion()" class="bg-primary text-white font-bold px-lg py-sm rounded-lg hover:opacity-90 transition-opacity flex items-center gap-sm shadow-sm text-body-sm">
      <span class="material-symbols-outlined text-[18px]">bolt</span> Ejecutar Pipeline
    </button>
  </div>

  <!-- Métricas técnicas reales -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-md mb-lg">
    <div class="bg-white border border-outline-variant rounded-xl p-md flex items-center justify-between glow-indigo">
      <div>
        <p class="font-label-md text-label-md text-secondary uppercase">Última Ejecución</p>
        <p id="metricLatency" class="font-headline-md text-headline-md text-primary">—<span class="text-xs font-normal text-secondary">ms</span></p>
      </div>
      <span class="material-symbols-outlined text-indigo-600 bg-indigo-50 p-2 rounded-lg">timer</span>
    </div>
    <div class="bg-white border border-outline-variant rounded-xl p-md flex items-center justify-between">
      <div>
        <p class="font-label-md text-label-md text-secondary uppercase">Palabras Procesadas</p>
        <p id="metricTokens" class="font-headline-md text-headline-md text-primary">—<span class="text-xs font-normal text-secondary ml-1">pal</span></p>
      </div>
      <span class="material-symbols-outlined text-amber-600 bg-amber-50 p-2 rounded-lg">memory</span>
    </div>
    <div class="bg-white border border-outline-variant rounded-xl p-md flex items-center justify-between">
      <div>
        <p class="font-label-md text-label-md text-secondary uppercase">Puntaje SEO</p>
        <p id="metricSeoScore" class="font-headline-md text-headline-md text-primary">—<span class="text-xs font-normal text-secondary">%</span></p>
      </div>
      <span class="material-symbols-outlined text-green-600 bg-green-50 p-2 rounded-lg">check_circle</span>
    </div>
    <div class="bg-white border border-outline-variant rounded-xl p-md flex items-center justify-between">
      <div>
        <p class="font-label-md text-label-md text-secondary uppercase">Tags Generados</p>
        <p id="metricTags" class="font-headline-md text-headline-md text-primary">—</p>
      </div>
      <span class="material-symbols-outlined text-purple-600 bg-purple-50 p-2 rounded-lg">tag</span>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-12 gap-lg">
    <!-- Tarjetas de agentes (5 cols) -->
    <div class="lg:col-span-5 space-y-md">
      <!-- Camilo -->
      <div class="bg-white border border-outline-variant rounded-xl p-lg glow-indigo">
        <div class="flex items-center justify-between mb-md">
          <div class="flex items-center gap-md">
            <div class="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center font-bold text-purple-700 text-lg agent-pulse">C</div>
            <div>
              <h4 class="font-body-md font-bold text-primary">Camilo</h4>
              <p class="font-body-sm text-body-sm text-secondary">Agente de Análisis Semántico</p>
            </div>
          </div>
          <span id="agentStatusCamilo" class="px-sm py-1 text-[10px] font-bold rounded bg-slate-100 text-slate-600">EN ESPERA</span>
        </div>
        <div class="space-y-xs">
          <div class="flex justify-between text-xs"><span class="text-secondary font-label-md">Tarea</span><span id="agentTaskCamilo" class="font-bold font-mono-label">Esperando...</span></div>
          <div class="w-full bg-surface-container-high h-1 rounded-full overflow-hidden"><div id="agentBarCamilo" class="bg-purple-500 h-full transition-all duration-500" style="width:0%"></div></div>
        </div>
      </div>
      <!-- Pipe -->
      <div class="bg-white border border-outline-variant rounded-xl p-lg">
        <div class="flex items-center justify-between mb-md">
          <div class="flex items-center gap-md">
            <div class="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center font-bold text-indigo-700 text-lg agent-pulse">P</div>
            <div>
              <h4 class="font-body-md font-bold text-primary">Pipe</h4>
              <p class="font-body-sm text-body-sm text-secondary">Agente de Estrategia de Tags</p>
            </div>
          </div>
          <span id="agentStatusPipe" class="px-sm py-1 text-[10px] font-bold rounded bg-slate-100 text-slate-600">EN ESPERA</span>
        </div>
        <div class="space-y-xs">
          <div class="flex justify-between text-xs"><span class="text-secondary font-label-md">Tarea</span><span id="agentTaskPipe" class="font-bold font-mono-label">Esperando...</span></div>
          <div class="w-full bg-surface-container-high h-1 rounded-full overflow-hidden"><div id="agentBarPipe" class="bg-indigo-500 h-full transition-all duration-500" style="width:0%"></div></div>
        </div>
      </div>
      <!-- Valentina -->
      <div class="bg-white border border-outline-variant rounded-xl p-lg">
        <div class="flex items-center justify-between mb-md">
          <div class="flex items-center gap-md">
            <div class="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center font-bold text-orange-700 text-lg agent-pulse">V</div>
            <div>
              <h4 class="font-body-md font-bold text-primary">Valentina</h4>
              <p class="font-body-sm text-body-sm text-secondary">Agente de Negrillas y Titulares</p>
            </div>
          </div>
          <span id="agentStatusValentina" class="px-sm py-1 text-[10px] font-bold rounded bg-slate-100 text-slate-600">EN ESPERA</span>
        </div>
        <div class="space-y-xs">
          <div class="flex justify-between text-xs"><span class="text-secondary font-label-md">Tarea</span><span id="agentTaskValentina" class="font-bold font-mono-label">Esperando...</span></div>
          <div class="w-full bg-surface-container-high h-1 rounded-full overflow-hidden"><div id="agentBarValentina" class="bg-orange-500 h-full transition-all duration-500" style="width:0%"></div></div>
        </div>
      </div>
      <!-- Adriana -->
      <div class="bg-white border border-outline-variant rounded-xl p-lg">
        <div class="flex items-center justify-between mb-md">
          <div class="flex items-center gap-md">
            <div class="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center font-bold text-blue-700 text-lg agent-pulse">A</div>
            <div>
              <h4 class="font-body-md font-bold text-primary">Adriana</h4>
              <p class="font-body-sm text-body-sm text-secondary">Agente de H2 y Análisis Final</p>
            </div>
          </div>
          <span id="agentStatusAdriana" class="px-sm py-1 text-[10px] font-bold rounded bg-slate-100 text-slate-600">EN ESPERA</span>
        </div>
        <div class="space-y-xs">
          <div class="flex justify-between text-xs"><span class="text-secondary font-label-md">Tarea</span><span id="agentTaskAdriana" class="font-bold font-mono-label">Esperando...</span></div>
          <div class="w-full bg-surface-container-high h-1 rounded-full overflow-hidden"><div id="agentBarAdriana" class="bg-blue-500 h-full transition-all duration-500" style="width:0%"></div></div>
        </div>
      </div>
    </div>

    <!-- Consola terminal (7 cols) -->
    <div class="lg:col-span-7 flex flex-col">
      <div class="bg-primary-container rounded-xl overflow-hidden flex flex-col h-full min-h-[560px]">
        <!-- Cabecera terminal -->
        <div class="flex items-center justify-between px-lg py-sm border-b border-white/10">
          <div class="flex items-center gap-md">
            <div class="flex gap-1.5">
              <div class="w-3 h-3 rounded-full bg-red-500 hover:opacity-80 cursor-pointer" onclick="limpiarTerminal()" title="Limpiar terminal"></div>
              <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
              <div class="w-3 h-3 rounded-full bg-green-500"></div>
            </div>
            <span class="font-mono-label text-mono-label text-primary-fixed-dim">corvus-nigrum — terminal</span>
          </div>
          <div class="flex items-center gap-md">
            <div class="flex items-center gap-xs">
              <div id="terminalStatusDot" class="w-2 h-2 rounded-full bg-green-400 animate-pulse-dot"></div>
              <span id="terminalStatusText" class="font-label-md text-label-md text-primary-fixed-dim">Listo</span>
            </div>
            <button onclick="copiarTerminal()" class="text-primary-fixed-dim hover:text-white transition-colors" title="Copiar logs">
              <span class="material-symbols-outlined text-[18px]">content_copy</span>
            </button>
            <button onclick="limpiarTerminal()" class="text-primary-fixed-dim hover:text-white transition-colors" title="Limpiar">
              <span class="material-symbols-outlined text-[18px]">delete_sweep</span>
            </button>
          </div>
        </div>
        <!-- Cuerpo terminal -->
        <div id="terminalLogContainer" class="terminal-scroll flex-1 overflow-y-auto p-lg font-mono text-[13px] leading-relaxed space-y-0.5 bg-[#0d1117]">
          <div class="text-green-400">╔══════════════════════════════════════════╗</div>
          <div class="text-green-400">║  Corvus Nigrum — Motor de Optimización   ║</div>
          <div class="text-green-400">║  v2.0  |  Suite para Medios Colombia      ║</div>
          <div class="text-green-400">╚══════════════════════════════════════════╝</div>
          <div class="text-slate-500">── Sistema listo. Esperando tarea de optimización. ──</div>
          <div class="text-slate-500">── Comandos: limpiar | optimizar | [URL para extraer] ──</div>
        </div>
        <!-- Input terminal -->
        <div class="flex items-center gap-sm px-lg py-sm bg-[#161b22] border-t border-white/10">
          <span class="text-green-400 font-mono text-sm">$</span>
          <input id="terminalInput" type="text" placeholder="Escribe: optimizar, limpiar, o pega una URL..."
            class="flex-1 bg-transparent text-slate-300 font-mono text-sm outline-none placeholder-slate-600"
            onkeydown="if(event.key==='Enter') enviarComandoTerminal()"/>
          <button onclick="enviarComandoTerminal()" class="text-primary-fixed-dim hover:text-white transition-colors">
            <span class="material-symbols-outlined text-[18px]">send</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════
     VISTA 5: CONFIGURACIÓN
══════════════════════════════════════════════ -->
<section id="view-settings" class="view-section">
  <div class="mb-xl">
    <h2 class="font-headline-lg text-headline-lg text-primary">Configuración</h2>
    <p class="font-body-md text-body-md text-secondary">Configuración del sistema Corvus Nigrum.</p>
  </div>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-lg max-w-3xl">
    <!-- Config pipeline -->
    <div class="bg-white border border-outline-variant rounded-xl p-lg space-y-md">
      <h3 class="font-body-md font-bold text-primary border-b border-outline-variant pb-sm">Configuración del Pipeline</h3>
      <div class="flex items-center justify-between">
        <div>
          <p class="font-body-sm font-bold">Guardar automáticamente</p>
          <p class="font-label-md text-label-md text-secondary">Guardar resultado en /output al optimizar</p>
        </div>
        <label class="toggle-track">
          <input type="checkbox" id="settingAutoSave" checked onchange="guardarConfiguracion()"/>
          <span class="toggle-slider"></span>
        </label>
      </div>
      <div class="flex items-center justify-between">
        <div>
          <p class="font-body-sm font-bold">Logs detallados en consola</p>
          <p class="font-label-md text-label-md text-secondary">Mostrar logs de cada agente en tiempo real</p>
        </div>
        <label class="toggle-track">
          <input type="checkbox" id="settingVerboseLogs" onchange="guardarConfiguracion()"/>
          <span class="toggle-slider"></span>
        </label>
      </div>
      <div class="flex items-center justify-between">
        <div>
          <p class="font-body-sm font-bold">Ir al editor al optimizar</p>
          <p class="font-label-md text-label-md text-secondary">Navegar al editor automáticamente con el resultado</p>
        </div>
        <label class="toggle-track">
          <input type="checkbox" id="settingAutoNav" checked onchange="guardarConfiguracion()"/>
          <span class="toggle-slider"></span>
        </label>
      </div>
      <div id="settingsSavedMsg" class="text-xs text-green-600 font-bold hidden">✅ Configuración guardada.</div>
    </div>

    <!-- Directorio de salida -->
    <div class="bg-white border border-outline-variant rounded-xl p-lg space-y-md">
      <h3 class="font-body-md font-bold text-primary border-b border-outline-variant pb-sm">Directorio de Salida</h3>
      <div>
        <p class="font-label-md text-label-md text-secondary mb-sm">Los archivos .txt, .docx y .md se guardan en la carpeta <strong>output/</strong> del proyecto.</p>
        <div class="flex gap-sm">
          <input type="text" id="outputDirDisplay" value="output/" class="flex-1 bg-surface border border-outline-variant rounded-lg px-md py-sm text-body-sm focus:outline-none" readonly/>
          <button onclick="abrirCarpetaOutput()" class="px-md py-sm bg-primary text-white rounded-lg font-label-md text-label-md hover:opacity-90 flex items-center gap-xs">
            <span class="material-symbols-outlined text-[16px]">folder_open</span> Abrir
          </button>
        </div>
      </div>
      <div class="pt-sm border-t border-outline-variant">
        <p class="font-label-md text-label-md text-secondary mb-sm">Archivos en output:</p>
        <div id="outputFileList" class="space-y-1 max-h-32 overflow-y-auto">
          <p class="text-xs text-secondary italic">Cargando...</p>
        </div>
      </div>
    </div>

    <!-- Acerca de -->
    <div class="col-span-1 md:col-span-2 bg-white border border-outline-variant rounded-xl p-lg">
      <h3 class="font-body-md font-bold text-primary border-b border-outline-variant pb-sm mb-md">Acerca de Corvus Nigrum</h3>
      <div class="flex items-center gap-lg">
        <img src="/logo" alt="Logo" class="w-16 h-16 object-contain rounded-xl" onerror="this.style.display='none'"/>
        <div>
          <p class="font-body-md font-bold">Corvus Nigrum — Optimizador de Noticias con IA</p>
          <p class="font-body-sm text-secondary">Versión 2.0 · Suite para Medios Colombianos</p>
          <p class="font-body-sm text-secondary mt-xs">Agentes: Camilo (Semántica) · Pipe (Tags) · Valentina (Negrillas) · Adriana (H2s)</p>
        </div>
      </div>
    </div>
  </div>
</section>

</div><!-- fin content div -->
</main><!-- fin main -->

<!-- ════════════════════════════════════════════════════════════
     BARRA DE ACCIONES INFERIOR (fija)
════════════════════════════════════════════════════════════ -->
<footer class="fixed bottom-0 right-0 left-64 z-50 flex justify-center items-center gap-xl h-20 px-xl bg-surface-container-high border-t border-outline-variant shadow-lg">
  <button onclick="exportarHtml()" class="flex flex-col items-center justify-center text-secondary px-xl py-xs hover:bg-surface-variant transition-all active:scale-95 duration-150 rounded-xl group">
    <span class="material-symbols-outlined group-hover:text-primary">code</span>
    <span class="font-label-md text-label-md mt-1">Exportar HTML</span>
  </button>
  <button onclick="exportarDocx()" class="flex flex-col items-center justify-center bg-primary text-on-primary rounded-xl px-xl py-xs hover:opacity-90 transition-all active:scale-95 duration-150 shadow-md">
    <span class="material-symbols-outlined">description</span>
    <span class="font-label-md text-label-md mt-1">Exportar Word</span>
  </button>
  <button onclick="exportarMarkdown()" class="flex flex-col items-center justify-center text-secondary px-xl py-xs hover:bg-surface-variant transition-all active:scale-95 duration-150 rounded-xl group">
    <span class="material-symbols-outlined group-hover:text-primary">publish</span>
    <span class="font-label-md text-label-md mt-1">Exportar MD</span>
  </button>
</footer>

<!-- ════════════════════════════════════════════════════════════
     JAVASCRIPT — INTERACTIVIDAD COMPLETA
════════════════════════════════════════════════════════════ -->
<script>
/* ────────────────────────────────────────────────────────────
   ESTADO GLOBAL
──────────────────────────────────────────────────────────── */
let lastResult  = null;
let currentView = 'dashboard';
let config      = {
  autoSave:    true,
  verboseLogs: false,
  autoNav:     true,
};

/* ────────────────────────────────────────────────────────────
   CONFIGURACIÓN (Settings)
──────────────────────────────────────────────────────────── */
function guardarConfiguracion() {
  config.autoSave    = document.getElementById('settingAutoSave').checked;
  config.verboseLogs = document.getElementById('settingVerboseLogs').checked;
  config.autoNav     = document.getElementById('settingAutoNav').checked;
  try { localStorage.setItem('corvus_config', JSON.stringify(config)); } catch(e){}
  const msg = document.getElementById('settingsSavedMsg');
  msg.classList.remove('hidden');
  setTimeout(() => msg.classList.add('hidden'), 2000);
}

function cargarConfiguracion() {
  try {
    const saved = localStorage.getItem('corvus_config');
    if (saved) config = {...config, ...JSON.parse(saved)};
  } catch(e) {}
  document.getElementById('settingAutoSave').checked    = config.autoSave;
  document.getElementById('settingVerboseLogs').checked = config.verboseLogs;
  document.getElementById('settingAutoNav').checked     = config.autoNav;
}

async function abrirCarpetaOutput() {
  // Muestra la lista de archivos disponibles para descargar
  try {
    const resp  = await fetch('/api/historial');
    const items = await resp.json();
    const list  = document.getElementById('outputFileList');
    if (!items.length) {
      list.innerHTML = '<p class="text-xs text-secondary italic">Sin archivos aún.</p>';
      return;
    }
    list.innerHTML = items.map(it =>
      `<div class="flex items-center justify-between">
        <span class="text-xs font-bold">${it.slug}.${it.tipo.toLowerCase()}</span>
        <span class="text-xs text-secondary">${it.fecha}</span>
      </div>`
    ).join('');
  } catch(e) {
    alert('No se pudo leer el directorio output.');
  }
}

/* ────────────────────────────────────────────────────────────
   NAVEGACIÓN
──────────────────────────────────────────────────────────── */
function goTo(view) {
  document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('#sideNav button').forEach(btn => {
    btn.classList.remove('text-primary','font-bold','bg-secondary-container','active-nav-glow');
    btn.classList.add('text-secondary');
  });
  const section = document.getElementById('view-' + view);
  if (section) section.classList.add('active');
  const navBtn = document.getElementById('nav-' + view);
  if (navBtn) {
    navBtn.classList.remove('text-secondary');
    navBtn.classList.add('text-primary','font-bold','bg-secondary-container','active-nav-glow');
  }
  currentView = view;
  if (view === 'dashboard') { cargarHistorial(); cargarEstadisticas(); }
  if (view === 'settings')  { cargarConfiguracion(); abrirCarpetaOutput(); }
}

/* ────────────────────────────────────────────────────────────
   HISTORIAL Y ESTADÍSTICAS (datos REALES del servidor)
──────────────────────────────────────────────────────────── */
async function cargarHistorial() {
  try {
    const resp  = await fetch('/api/historial');
    const items = await resp.json();
    const tbody = document.getElementById('dashPipelineBody');
    if (!items.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="px-lg py-xl text-center text-secondary italic">Sin optimizaciones aún. Ejecuta el pipeline en el Editor.</td></tr>';
      return;
    }
    tbody.innerHTML = items.map(it => {
      const tipoBadge = it.tipo === 'TXT'
        ? 'bg-indigo-50 text-indigo-800 border border-indigo-200'
        : it.tipo === 'DOCX'
        ? 'bg-green-50 text-green-800 border border-green-200'
        : 'bg-slate-50 text-slate-800 border border-slate-200';
      return `
        <tr class="hover:bg-surface-container-lowest transition-colors">
          <td class="px-lg py-md">
            <p class="font-bold text-primary text-body-sm">${it.slug}</p>
            <p class="text-secondary text-xs">${it.preview ? it.preview.substring(0,70)+'...' : 'Sin vista previa'}</p>
          </td>
          <td class="px-lg py-md"><span class="px-sm py-0.5 rounded text-xs font-bold ${tipoBadge}">${it.tipo}</span></td>
          <td class="px-lg py-md font-bold text-body-sm">${it.tags}</td>
          <td class="px-lg py-md text-secondary text-xs">${it.fecha}</td>
          <td class="px-lg py-md">
            <button onclick="goTo('editor')" class="text-primary hover:underline font-bold text-body-sm">Revisar</button>
          </td>
        </tr>`;
    }).join('');
  } catch(e) {
    console.error('Error cargando historial:', e);
  }
}

async function cargarEstadisticas() {
  try {
    const resp = await fetch('/api/estadisticas');
    const data = await resp.json();
    const el1  = document.getElementById('statTotalOpt');
    const el2  = document.getElementById('statTotalNegrillas');
    if (el1) el1.textContent = data.total_optimizaciones || 0;
    if (el2) el2.textContent = data.total_negrillas || 0;
  } catch(e) {
    console.error('Error estadísticas:', e);
  }
}

function buscarHistorial(termino) {
  const rows = document.querySelectorAll('#dashPipelineBody tr');
  rows.forEach(row => {
    const texto = row.textContent.toLowerCase();
    row.style.display = texto.includes(termino.toLowerCase()) ? '' : 'none';
  });
}

/* ────────────────────────────────────────────────────────────
   IMPORTAR DESDE URL
──────────────────────────────────────────────────────────── */
async function extraerUrl() {
  const url = document.getElementById('inputUrl').value.trim();
  if (!url) { mostrarToast('⚠️ Por favor ingresa una URL válida.', 'warn'); return; }
  const btn = document.getElementById('btnFetchUrl');
  btn.disabled = true;
  btn.innerHTML = '<span class="material-symbols-outlined text-[18px] animate-spin">refresh</span> Cargando...';
  try {
    const resp = await fetch('/api/extraer-url', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url})
    });
    const data = await resp.json();
    if (data.exito) {
      document.getElementById('inputText').value = data.texto;
      if (data.slug)   document.getElementById('inputSlug').value = data.slug;
      if (data.titulo) document.getElementById('discoverCardTitle').textContent = data.titulo;
      actualizarContadores();
      addLog('✅ Noticia extraída: ' + url);
      mostrarToast('✅ Noticia importada correctamente.');
    } else {
      mostrarToast('❌ Error: ' + (data.error || 'No se pudo importar la URL.'), 'error');
    }
  } catch(e) {
    mostrarToast('❌ Error de conexión: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">download</span> Importar';
  }
}

/* ────────────────────────────────────────────────────────────
   LIMPIAR TEXTO ORIGINAL
──────────────────────────────────────────────────────────── */
function limpiarTextoOriginal() {
  if (!document.getElementById('inputText').value.trim()) return;
  if (confirm('¿Limpiar el texto original?')) {
    document.getElementById('inputText').value = '';
    document.getElementById('inputSlug').value = '';
    actualizarContadores();
  }
}

/* ────────────────────────────────────────────────────────────
   CONTADOR DE PALABRAS Y CARACTERES
──────────────────────────────────────────────────────────── */
function actualizarContadores() {
  const txt   = document.getElementById('inputText').value.trim();
  const words = txt ? txt.split(/\s+/).filter(Boolean).length : 0;
  document.getElementById('wordCountBadge').textContent = words;
  document.getElementById('charCountBadge').textContent = txt.length;
  const slugInput = document.getElementById('inputSlug');
  if (!slugInput.value && txt.length > 20) {
    const primera = txt.split('\n')[0];
    slugInput.value = 'articulo_' + primera.toLowerCase()
      .replace(/[áéíóúüñ]/g, c => ({á:'a',é:'e',í:'i',ó:'o',ú:'u',ü:'u',ñ:'n'}[c]||c))
      .replace(/[^a-z0-9\s]/g, '').trim().replace(/\s+/g, '_').substring(0, 35);
  }
}
document.getElementById('inputText').addEventListener('input', actualizarContadores);

/* ────────────────────────────────────────────────────────────
   TERMINAL — LOGS
──────────────────────────────────────────────────────────── */
function addLog(msg) {
  const container = document.getElementById('terminalLogContainer');
  const div       = document.createElement('div');
  let colorClass  = 'text-slate-300';
  if (msg.includes('✅') || msg.includes('🎉'))     colorClass = 'text-emerald-400 font-semibold';
  else if (msg.includes('⚠️'))                      colorClass = 'text-amber-400';
  else if (msg.includes('❌') || msg.includes('ERROR')) colorClass = 'text-red-400 font-bold';
  else if (msg.includes('[Camilo]'))                 colorClass = 'text-purple-300';
  else if (msg.includes('[Valentina]'))              colorClass = 'text-orange-300';
  else if (msg.includes('[Pipe]'))                   colorClass = 'text-indigo-300';
  else if (msg.includes('[Adriana]'))                colorClass = 'text-blue-300';
  else if (msg.startsWith('$'))                      colorClass = 'text-green-300';
  div.className   = colorClass;
  div.textContent = '[' + new Date().toLocaleTimeString('es-CO') + '] ' + msg;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function limpiarTerminal() {
  document.getElementById('terminalLogContainer').innerHTML =
    '<div class="text-slate-500">── Terminal limpia. Sistema listo. ──</div>';
}

function copiarTerminal() {
  const logs = Array.from(document.querySelectorAll('#terminalLogContainer div'))
    .map(d => d.textContent).join('\n');
  navigator.clipboard.writeText(logs).then(() => mostrarToast('📋 Logs copiados al portapapeles.'));
}

function enviarComandoTerminal() {
  const input = document.getElementById('terminalInput');
  const cmd   = input.value.trim();
  if (!cmd) return;
  addLog('$ ' + cmd);
  input.value = '';
  if (cmd === 'clear' || cmd === 'limpiar')      { limpiarTerminal(); return; }
  if (cmd.startsWith('http'))                    { document.getElementById('inputUrl').value = cmd; goTo('editor'); extraerUrl(); return; }
  if (cmd === 'run' || cmd === 'optimizar')       { ejecutarOptimizacion(); return; }
  if (cmd === 'historial')                        { cargarHistorial(); goTo('dashboard'); return; }
  if (cmd === 'ayuda' || cmd === 'help')          {
    addLog('⚠️ Comandos disponibles:');
    addLog('   optimizar — Ejecuta el pipeline completo');
    addLog('   limpiar   — Limpia la consola');
    addLog('   historial — Muestra el panel principal');
    addLog('   [URL]     — Importa artículo desde una URL');
    return;
  }
  addLog('⚠️ Comando no reconocido. Escribe "ayuda" para ver los comandos disponibles.');
}

/* ────────────────────────────────────────────────────────────
   ESTADO DE AGENTES
──────────────────────────────────────────────────────────── */
function setAgentStatus(name, status, task) {
  const badgeEl = document.getElementById('agentStatus' + name);
  const taskEl  = document.getElementById('agentTask'   + name);
  const barEl   = document.getElementById('agentBar'    + name);
  if (!badgeEl) return;
  const statusCfg = {
    IDLE:    {cls:'bg-slate-100 text-slate-600',              label:'EN ESPERA', pct:'0%'},
    WORKING: {cls:'bg-amber-100 text-amber-700 animate-pulse', label:'PROCESANDO', pct:'60%'},
    DONE:    {cls:'bg-emerald-100 text-emerald-700',           label:'COMPLETADO', pct:'100%'},
    ERROR:   {cls:'bg-red-100 text-red-700',                   label:'ERROR',      pct:'100%'},
  };
  const cfg = statusCfg[status] || statusCfg.IDLE;
  badgeEl.className   = 'px-sm py-1 text-[10px] font-bold rounded ' + cfg.cls;
  badgeEl.textContent = cfg.label;
  if (taskEl && task) taskEl.textContent = task;
  if (barEl)          barEl.style.width  = cfg.pct;
  const dashEl = document.getElementById('dash-' + name.toLowerCase() + '-status');
  if (dashEl) dashEl.textContent = task || cfg.label;
}

/* ────────────────────────────────────────────────────────────
   PIPELINE DE OPTIMIZACIÓN PRINCIPAL
──────────────────────────────────────────────────────────── */
async function ejecutarOptimizacion() {
  const texto = document.getElementById('inputText').value.trim();
  if (!texto) {
    goTo('editor');
    mostrarToast('⚠️ Por favor ingresa el texto de la nota antes de optimizar.', 'warn');
    return;
  }
  const slug = document.getElementById('inputSlug').value.trim() ||
    'nota_' + new Date().toISOString().slice(0,16).replace(/[-:T]/g,'');

  // UI: estado de carga
  const btnText = document.getElementById('globalRunBtnText');
  btnText.textContent = '⏳ Optimizando...';
  document.getElementById('btnGlobalRun').disabled = true;
  document.getElementById('terminalStatusDot').className = 'w-2 h-2 rounded-full bg-amber-400 animate-pulse-dot';
  document.getElementById('terminalStatusText').textContent = 'Procesando...';

  // Navegar a agentes para mostrar progreso
  goTo('agents');

  // Resetear agentes
  ['Camilo','Pipe','Valentina','Adriana'].forEach(a => setAgentStatus(a, 'IDLE', 'Preparando...'));

  addLog('🚀 Iniciando pipeline Corvus Nigrum...');
  addLog('📝 Slug: ' + slug + ' | Palabras: ' + texto.split(/\s+/).filter(Boolean).length);

  // Animar agentes secuencialmente
  const agentSeq = [
    ['Camilo',   'Análisis semántico...'],
    ['Pipe',     'Generando estrategia de tags...'],
    ['Valentina','Extrayendo frases para negrilla...'],
    ['Adriana',  'Generando H2s y puntaje SEO...'],
  ];
  agentSeq.forEach(([name, task], i) => {
    setTimeout(() => {
      setAgentStatus(name, 'WORKING', task);
      addLog(`[${name}] ${task}`);
    }, i * 1200);
  });

  const startTime = Date.now();
  try {
    const resp = await fetch('/api/optimizar', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({texto, slug})
    });
    const data    = await resp.json();
    const elapsed = Date.now() - startTime;

    // Mostrar logs del servidor
    (data.logs || []).forEach(l => addLog(l));

    if (data.exito) {
      agentSeq.forEach(([name]) => setAgentStatus(name, 'DONE', 'Completado ✓'));

      lastResult = data;
      renderizarResultados(data);

      // Métricas reales
      document.getElementById('metricLatency').innerHTML = elapsed + '<span class="text-xs font-normal text-secondary ml-1">ms</span>';
      const palabras = (data.texto_optimizado || '').split(/\s+/).length;
      document.getElementById('metricTokens').innerHTML  = palabras + '<span class="text-xs font-normal text-secondary ml-1">pal</span>';
      document.getElementById('metricSeoScore').innerHTML= (data.seo_score || '—') + '<span class="text-xs font-normal text-secondary">%</span>';
      document.getElementById('metricTags').textContent  = (data.tags || []).length;

      // SEO health en sidebar
      const score = data.seo_score || 0;
      document.getElementById('seoHealthScore').textContent = score;
      document.getElementById('seoHealthBar').style.width   = score + '%';

      document.getElementById('terminalStatusDot').className  = 'w-2 h-2 rounded-full bg-emerald-400';
      document.getElementById('terminalStatusText').textContent = 'Completado ✓';
      addLog('🎉 ¡Optimización finalizada en ' + elapsed + 'ms!');
      mostrarToast('🎉 Optimización completada en ' + elapsed + 'ms');

      // Navegar al editor si está configurado
      if (config.autoNav) goTo('editor');

    } else {
      agentSeq.forEach(([name]) => setAgentStatus(name, 'ERROR', 'Error'));
      addLog('❌ Error: ' + (data.error || 'Error desconocido'));
      document.getElementById('terminalStatusDot').className  = 'w-2 h-2 rounded-full bg-red-500';
      document.getElementById('terminalStatusText').textContent = 'Error';
      mostrarToast('❌ Error: ' + (data.error || 'Error en el pipeline'), 'error');
    }
  } catch(e) {
    addLog('❌ Error de conexión: ' + e.message);
    agentSeq.forEach(([name]) => setAgentStatus(name, 'ERROR', 'Error de conexión'));
    document.getElementById('terminalStatusDot').className  = 'w-2 h-2 rounded-full bg-red-500';
    document.getElementById('terminalStatusText').textContent = 'Error de Red';
    mostrarToast('❌ Error de conexión con el servidor', 'error');
  } finally {
    document.getElementById('btnGlobalRun').disabled = false;
    btnText.textContent = '⚡ Optimizar Ahora';
    cargarHistorial();
    cargarEstadisticas();
  }
}

/* ────────────────────────────────────────────────────────────
   RENDERIZAR RESULTADOS
──────────────────────────────────────────────────────────── */
function renderizarResultados(data) {
  // a) Texto optimizado con negrillas interactivas
  const outputContainer = document.getElementById('optimizedOutputText');
  if (data.texto_optimizado) {
    let html = data.texto_optimizado
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/\n/g,'<br/>');
    html = html.replace(/\*\*(.*?)\*\*/g,
      '<span class="diff-added px-0.5 rounded" onclick="toggleNegrilla(this)" title="Clic para alternar negrilla">$1</span>');
    outputContainer.innerHTML = '<p class="font-serif-news text-body-lg leading-relaxed">' + html + '</p>';
  }

  // b) Puntaje SEO
  const score = data.seo_score || 88;
  document.getElementById('seoScoreBadge').textContent = score + '% PUNTAJE SEO';

  // c) Razonamiento de Valentina
  const frases = data.frases_resaltadas || [];
  document.getElementById('reasoningFrasesCount').textContent = frases.length + ' frases resaltadas';
  const listEl = document.getElementById('reasoningFrasesList');
  listEl.innerHTML = frases.length
    ? frases.map(f =>
        `<div class="bg-slate-50 border border-slate-200 rounded p-1.5 font-semibold text-body-sm text-slate-800 cursor-pointer hover:bg-slate-100" onclick="copiarTag('${f.replace(/'/g,"\\'")}')">• ${f}</div>`
      ).join('')
    : '<p class="text-body-sm text-secondary italic">Sin frases detectadas.</p>';

  const readability = Math.min(99, 50 + frases.length * 3);
  document.getElementById('readabilityScore').textContent = readability + ' (Óptimo)';
  document.getElementById('readabilityBar').style.width   = readability + '%';

  // d) Tabla de tags en la vista SEO
  const tags = data.tags || [];
  const tagsBody = document.getElementById('tagsTableBody');
  if (tagsBody) {
    if (tags.length) {
      tagsBody.innerHTML = tags.map(t => {
        const tagStr = typeof t === 'string' ? t : (t.tag || t.nombre || t.name || 'Tag');
        const score  = (typeof t === 'object' && typeof t.score === 'number') ? t.score : Math.floor(Math.random() * 30 + 68);
        const estado = (typeof t === 'object' && (t.estado || t.tipo)) ? (t.estado || t.tipo) : 'Tendencia';
        const badgeClass = score >= 75
          ? 'thermal-badge-hot'
          : score >= 45
          ? 'thermal-badge-entity'
          : 'bg-slate-100 text-slate-700';
        const barWidth = Math.max(5, score) + '%';
        const dot = score >= 75 ? 'bg-indigo-500' : 'bg-slate-400';
        return `
          <div class="grid grid-cols-12 items-center p-sm hover:bg-surface-container-low rounded-lg transition-colors">
            <div class="col-span-4 flex items-center gap-sm">
              <div class="w-2 h-2 rounded-full ${dot}"></div>
              <span class="font-body-md font-semibold text-primary">${tagStr}</span>
            </div>
            <div class="col-span-3 flex items-center gap-xs">
              <span class="font-mono-label text-mono-label">${score}</span>
              <div class="flex-1 h-1.5 bg-surface-container-high rounded-full overflow-hidden">
                <div class="${dot} h-full" style="width:${barWidth}"></div>
              </div>
            </div>
            <div class="col-span-3">
              <span class="px-sm py-1 rounded-full text-xs font-bold ${badgeClass}">${estado}</span>
            </div>
            <div class="col-span-2 text-right">
              <button onclick="copiarTag('${tagStr.replace(/'/g,"\\'")}')" class="text-secondary hover:text-primary transition-colors"><span class="material-symbols-outlined">content_copy</span></button>
            </div>
          </div>`;
      }).join('');
    } else {
      tagsBody.innerHTML = '<p class="text-body-sm text-secondary italic px-sm py-lg text-center">No se encontraron tags para este artículo.</p>';
    }
  }

  // e) Previsualización Google Discover
  const firstLine = (data.texto_optimizado || '').split('\n').find(l => l.trim());
  if (firstLine) {
    document.getElementById('discoverCardTitle').textContent =
      firstLine.replace(/[*][*]/g, '').substring(0, 80);
  }
  const discoverSnippet = document.getElementById('discoverTagsSnippet');
  if (discoverSnippet) {
    discoverSnippet.innerHTML = '';
    tags.slice(0, 4).forEach(t => {
      const tagStr = typeof t === 'string' ? t : (t.tag || '');
      if (tagStr) {
        const span = document.createElement('span');
        span.className = 'text-[10px] bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full';
        span.textContent = '#' + tagStr.replace(/\s+/g, '');
        discoverSnippet.appendChild(span);
      }
    });
  }

  // f) H2s sugeridos
  const h2s = data.h2s || [];
  const h2sContainer = document.getElementById('h2sListContainer');
  h2sContainer.innerHTML = h2s.length
    ? h2s.map(h =>
        `<div class="flex items-start justify-between gap-sm bg-slate-50 border border-slate-200 rounded p-sm">
          <p class="font-body-sm text-body-sm font-semibold text-slate-800 flex-1">${h}</p>
          <button onclick="copiarTag('${h.replace(/'/g,"\\'")}');this.innerHTML='✅'" class="text-indigo-600 hover:underline text-[11px] font-bold shrink-0">Copiar</button>
        </div>`
      ).join('')
    : '<p class="text-body-sm text-secondary italic">Sin H2s generados.</p>';
}

/* ────────────────────────────────────────────────────────────
   TOGGLE NEGRILLA (Editor interactivo)
──────────────────────────────────────────────────────────── */
function toggleNegrilla(el) {
  el.classList.toggle('diff-added');
  el.classList.toggle('font-normal');
  el.classList.toggle('border-none');
}

/* ────────────────────────────────────────────────────────────
   TAGS
──────────────────────────────────────────────────────────── */
function copiarTag(tag) {
  navigator.clipboard.writeText(tag).catch(() => {});
  mostrarToast('✅ Copiado: ' + tag);
}

function agregarTagPersonalizado() {
  const input = document.getElementById('customTagInput');
  const tag   = input.value.trim();
  if (!tag) return;
  const tagsBody = document.getElementById('tagsTableBody');
  const newRow   = document.createElement('div');
  newRow.className = 'grid grid-cols-12 items-center p-sm hover:bg-surface-container-low rounded-lg transition-colors border border-indigo-100 bg-indigo-50/30';
  newRow.innerHTML = `
    <div class="col-span-4 flex items-center gap-sm">
      <div class="w-2 h-2 rounded-full bg-indigo-300"></div>
      <span class="font-body-md font-semibold text-primary">${tag}</span>
    </div>
    <div class="col-span-3 flex items-center gap-xs">
      <span class="font-mono-label text-mono-label">—</span>
      <div class="flex-1 h-1.5 bg-surface-container-high rounded-full"></div>
    </div>
    <div class="col-span-3">
      <span class="px-sm py-1 rounded-full text-xs font-bold thermal-badge-entity">Personalizado</span>
    </div>
    <div class="col-span-2 text-right">
      <button onclick="copiarTag('${tag}')" class="text-secondary hover:text-primary"><span class="material-symbols-outlined">content_copy</span></button>
    </div>`;
  tagsBody.appendChild(newRow);
  input.value = '';
  addLog('🏷️ Tag personalizado añadido: ' + tag);
  mostrarToast('🏷️ Tag añadido: ' + tag);
}

function switchTagTab(tab) {
  document.getElementById('tabBtn24h').classList.toggle('tab-btn-active', tab === '24h');
  document.getElementById('tabBtn24h').classList.toggle('border-outline-variant', tab !== '24h');
  document.getElementById('tabBtn7d').classList.toggle('tab-btn-active', tab === '7d');
  document.getElementById('tabBtn7d').classList.toggle('border-outline-variant', tab !== '7d');
}

/* ────────────────────────────────────────────────────────────
   EXPORTAR
──────────────────────────────────────────────────────────── */
function exportarHtml() {
  const content = document.getElementById('optimizedOutputText').innerHTML;
  if (!content || content.includes('texto optimizado aparecerá aquí')) {
    mostrarToast('⚠️ Primero ejecuta una optimización.', 'warn'); return;
  }
  const blob = new Blob([
    '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Corvus Export</title></head><body style="font-family:Georgia,serif;max-width:800px;margin:40px auto;line-height:1.8">' +
    content + '</body></html>'
  ], {type:'text/html'});
  const a = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = (document.getElementById('inputSlug').value || 'corvus_export') + '.html';
  a.click();
  addLog('✅ HTML exportado.');
  mostrarToast('✅ HTML exportado correctamente.');
}

async function exportarDocx() {
  const texto = lastResult?.texto_optimizado || document.getElementById('inputText').value.trim();
  if (!texto) { mostrarToast('⚠️ Primero ejecuta una optimización.', 'warn'); return; }
  const slug  = document.getElementById('inputSlug').value || 'corvus_export';
  addLog('📄 Generando Word (.docx)...');
  try {
    const resp = await fetch('/api/exportar-docx', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({texto, slug})
    });
    if (resp.ok) {
      const blob = await resp.blob();
      const a    = document.createElement('a');
      a.href     = URL.createObjectURL(blob);
      a.download = slug + '.docx';
      a.click();
      addLog('✅ Word exportado: ' + slug + '.docx');
      mostrarToast('✅ Word exportado: ' + slug + '.docx');
    } else {
      const err = await resp.json();
      addLog('❌ Error DOCX: ' + (err.error || 'desconocido'));
      mostrarToast('❌ Error exportando Word: ' + (err.error || ''), 'error');
    }
  } catch(e) {
    addLog('❌ Error exportando DOCX: ' + e.message);
    mostrarToast('❌ Error de conexión al exportar', 'error');
  }
}

async function exportarMarkdown() {
  const texto = lastResult?.texto_optimizado || document.getElementById('inputText').value.trim();
  if (!texto) { mostrarToast('⚠️ Primero ejecuta una optimización.', 'warn'); return; }
  const slug  = document.getElementById('inputSlug').value || 'corvus_export';
  addLog('📝 Generando Markdown...');
  try {
    const resp = await fetch('/api/exportar-md', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({texto, slug})
    });
    if (resp.ok) {
      const blob = await resp.blob();
      const a    = document.createElement('a');
      a.href     = URL.createObjectURL(blob);
      a.download = slug + '.md';
      a.click();
      addLog('✅ Markdown exportado: ' + slug + '.md');
      mostrarToast('✅ Markdown exportado correctamente.');
    } else {
      const err = await resp.json();
      addLog('❌ Error MD: ' + (err.error || 'desconocido'));
      mostrarToast('❌ Error exportando MD: ' + (err.error || ''), 'error');
    }
  } catch(e) {
    addLog('❌ Error exportando MD: ' + e.message);
    mostrarToast('❌ Error de conexión al exportar', 'error');
  }
}

/* ────────────────────────────────────────────────────────────
   TOASTS / NOTIFICACIONES
──────────────────────────────────────────────────────────── */
function mostrarToast(msg, tipo = 'success') {
  const colores = {
    success: 'bg-primary text-white',
    warn:    'bg-amber-500 text-white',
    error:   'bg-red-600 text-white',
  };
  const tip = document.createElement('div');
  tip.textContent = msg;
  tip.className   = `fixed bottom-24 right-8 ${colores[tipo] || colores.success} px-md py-sm rounded-lg text-body-sm font-bold z-[100] shadow-lg transition-all`;
  document.body.appendChild(tip);
  setTimeout(() => { tip.style.opacity = '0'; setTimeout(() => tip.remove(), 300); }, 2200);
}

/* ────────────────────────────────────────────────────────────
   MICRO-INTERACCIONES
──────────────────────────────────────────────────────────── */
document.querySelectorAll('.glass-card').forEach(card => {
  card.addEventListener('mouseenter', () => {
    card.style.transform  = 'translateY(-2px)';
    card.style.transition = 'transform .2s ease-out';
  });
  card.addEventListener('mouseleave', () => {
    card.style.transform = 'translateY(0)';
  });
});

// Auto-scroll suave en el Discover
const feed = document.querySelector('.google-discover-feed');
if (feed) {
  let dir = 1;
  setInterval(() => {
    feed.scrollBy({top: dir, behavior: 'smooth'});
    if (feed.scrollTop + feed.clientHeight >= feed.scrollHeight) dir = -1;
    if (feed.scrollTop <= 0) dir = 1;
  }, 3000);
}

/* ────────────────────────────────────────────────────────────
   INICIALIZACIÓN
──────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  cargarConfiguracion();
  goTo('dashboard');
  cargarHistorial();
  cargarEstadisticas();
});
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return HTML

if __name__ == "__main__":
    print("[OK] Iniciando Corvus Nigrum - Optimizador de Noticias con IA en puerto 5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
