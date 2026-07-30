import os
import threading
import json
import queue
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Cola para streaming de logs
log_queues = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>La Redacción — Optimizador SEO</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
  <style>
    :root {
      --bg: #0a0a0f;
      --surface: #12121a;
      --surface2: #1a1a26;
      --border: #2a2a3d;
      --accent: #6c63ff;
      --accent2: #a78bfa;
      --green: #10b981;
      --yellow: #f59e0b;
      --red: #ef4444;
      --text: #e2e8f0;
      --muted: #64748b;
      --radius: 14px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }

    /* HEADER */
    header {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 16px 32px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .logo-icon {
      width: 38px; height: 38px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      font-size: 18px;
    }
    .logo-text { font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }
    .logo-text span { color: var(--accent2); }
    .badge {
      margin-left: auto;
      font-size: 11px;
      background: rgba(108,99,255,0.15);
      border: 1px solid rgba(108,99,255,0.3);
      color: var(--accent2);
      padding: 4px 10px;
      border-radius: 99px;
      font-weight: 500;
    }

    /* MAIN LAYOUT */
    .container {
      max-width: 1300px;
      margin: 0 auto;
      padding: 32px 24px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    @media (max-width: 900px) {
      .container { grid-template-columns: 1fr; }
    }

    /* CARDS */
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .card-header {
      padding: 18px 22px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .card-header h2 {
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
    }
    .card-header .icon {
      width: 28px; height: 28px;
      border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-size: 14px;
    }
    .icon-purple { background: rgba(108,99,255,0.15); }
    .icon-green  { background: rgba(16,185,129,0.15); }
    .card-body { padding: 20px 22px; }

    /* TEXTAREA */
    .input-label {
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 8px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    textarea {
      width: 100%;
      height: 340px;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      font-family: 'Inter', sans-serif;
      font-size: 13.5px;
      line-height: 1.7;
      padding: 16px;
      resize: vertical;
      outline: none;
      transition: border-color 0.2s;
    }
    textarea:focus { border-color: var(--accent); }
    textarea::placeholder { color: var(--muted); }

    /* SLUG INPUT */
    .slug-row {
      display: flex;
      gap: 10px;
      margin-top: 14px;
      align-items: flex-end;
    }
    .slug-field { flex: 1; }
    input[type="text"] {
      width: 100%;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      font-family: 'Inter', sans-serif;
      font-size: 13px;
      padding: 10px 14px;
      outline: none;
      transition: border-color 0.2s;
    }
    input[type="text"]:focus { border-color: var(--accent); }
    input[type="text"]::placeholder { color: var(--muted); }

    /* BTN */
    .btn {
      padding: 11px 28px;
      border-radius: 10px;
      border: none;
      font-family: 'Inter', sans-serif;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      display: flex; align-items: center; gap: 8px;
      white-space: nowrap;
    }
    .btn-primary {
      background: linear-gradient(135deg, var(--accent), #8b5cf6);
      color: #fff;
    }
    .btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
    .btn-sm {
      padding: 7px 16px;
      font-size: 12px;
    }
    .btn-ghost {
      background: var(--surface2);
      color: var(--muted);
      border: 1px solid var(--border);
    }
    .btn-ghost:hover { color: var(--text); border-color: var(--accent); }

    /* STATS ROW */
    .stats-row {
      display: flex; gap: 10px;
      margin-top: 14px;
    }
    .stat-pill {
      font-size: 11.5px;
      color: var(--muted);
      background: var(--surface2);
      padding: 5px 12px;
      border-radius: 99px;
      border: 1px solid var(--border);
    }
    .stat-pill span { color: var(--text); font-weight: 600; }

    /* LOG PANEL */
    .log-panel {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      height: 200px;
      overflow-y: auto;
      padding: 14px 16px;
      font-family: 'Courier New', monospace;
      font-size: 12px;
      line-height: 1.6;
      color: var(--muted);
    }
    .log-panel .log-line { padding: 1px 0; }
    .log-panel .log-ok   { color: var(--green); }
    .log-panel .log-warn { color: var(--yellow); }
    .log-panel .log-err  { color: var(--red); }
    .log-panel .log-info { color: var(--accent2); }

    /* SPINNER */
    .spinner {
      width: 14px; height: 14px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      display: none;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* RESULT PANEL */
    .result-panel {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      font-size: 13px;
      line-height: 1.8;
      min-height: 200px;
      white-space: pre-wrap;
      overflow-y: auto;
      max-height: 520px;
      color: var(--text);
    }
    .result-placeholder {
      color: var(--muted);
      font-style: italic;
      text-align: center;
      margin-top: 60px;
    }

    /* TAGS */
    .tags-grid {
      display: flex; flex-wrap: wrap; gap: 8px;
      margin-top: 6px;
    }
    .tag-chip {
      font-size: 12px;
      padding: 5px 12px;
      border-radius: 99px;
      font-weight: 500;
    }
    .tag-hot {
      background: rgba(245,158,11,0.15);
      border: 1px solid rgba(245,158,11,0.3);
      color: #f59e0b;
    }
    .tag-rel {
      background: rgba(108,99,255,0.1);
      border: 1px solid rgba(108,99,255,0.25);
      color: var(--accent2);
    }

    /* STATUS BAR */
    .status-bar {
      padding: 12px 22px;
      display: flex;
      align-items: center;
      gap: 10px;
      border-top: 1px solid var(--border);
      font-size: 12.5px;
      color: var(--muted);
    }
    .dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--muted);
    }
    .dot.active { background: var(--green); box-shadow: 0 0 6px var(--green); }
    .dot.running { background: var(--yellow); animation: pulse 1s infinite; }
    @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

    /* COPY BTN */
    .copy-btn {
      margin-left: auto;
      font-size: 11.5px;
      cursor: pointer;
      color: var(--accent2);
      background: none;
      border: none;
      font-family: inherit;
      padding: 4px 8px;
      border-radius: 6px;
      transition: background 0.2s;
    }
    .copy-btn:hover { background: rgba(108,99,255,0.15); }

    /* SECTION DIVIDER */
    .section-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--muted);
      margin: 16px 0 8px;
    }

    /* PROGRESS BAR */
    .progress-wrap {
      width: 100%;
      height: 4px;
      background: var(--border);
      border-radius: 99px;
      overflow: hidden;
      margin-top: 12px;
      display: none;
    }
    .progress-bar {
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent2));
      border-radius: 99px;
      width: 0%;
      transition: width 0.4s ease;
    }

    /* AGENT PILLS */
    .agents-row {
      display: flex; gap: 8px; flex-wrap: wrap;
      margin-top: 6px;
    }
    .agent-pill {
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 99px;
      border: 1px solid var(--border);
      color: var(--muted);
      display: flex; align-items: center; gap: 5px;
    }
    .agent-pill.done { border-color: rgba(16,185,129,0.4); color: var(--green); }
    .agent-pill.active { border-color: rgba(245,158,11,0.4); color: var(--yellow); }

    /* SCROLLBAR */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
  </style>
</head>
<body>

<header>
  <div class="logo-icon">✍️</div>
  <div class="logo-text">La <span>Redacción</span></div>
  <span class="badge">Optimizador SEO v2</span>
</header>

<div class="container">

  <!-- LEFT: INPUT -->
  <div>
    <div class="card">
      <div class="card-header">
        <div class="icon icon-purple">📝</div>
        <h2>Texto del artículo</h2>
      </div>
      <div class="card-body">
        <div class="input-label">Pega aquí el texto completo de la nota</div>
        <textarea id="texto" placeholder="Pega aquí el texto completo de la nota periodística...&#10;&#10;El título, el cuerpo, todo. Entre más texto, mejores tags."></textarea>

        <div class="slug-row">
          <div class="slug-field">
            <div class="input-label" style="margin-top:0">Nombre del archivo (sin espacios)</div>
            <input type="text" id="slug" placeholder="ej: articulo_petro_denuncia"/>
          </div>
          <button class="btn btn-primary" id="btnOptimizar" onclick="optimizar()">
            <span class="spinner" id="spinner"></span>
            <span id="btnText">⚡ Optimizar</span>
          </button>
        </div>

        <div class="progress-wrap" id="progressWrap">
          <div class="progress-bar" id="progressBar"></div>
        </div>

        <div class="stats-row" id="statsRow" style="display:none">
          <div class="stat-pill">Palabras: <span id="wordCount">—</span></div>
          <div class="stat-pill">Caracteres: <span id="charCount">—</span></div>
        </div>
      </div>

      <!-- AGENTS STATUS -->
      <div class="card-body" style="border-top: 1px solid var(--border); padding-top: 14px;">
        <div class="section-label">Agentes en ejecución</div>
        <div class="agents-row">
          <div class="agent-pill" id="agentCamilo">🕵️ Camilo</div>
          <div class="agent-pill" id="agentValentina">✍️ Valentina</div>
          <div class="agent-pill" id="agentPipe">🏷️ Pipe</div>
          <div class="agent-pill" id="agentAdriana">📄 Adriana</div>
        </div>
      </div>

      <!-- LOG -->
      <div class="card-body" style="border-top: 1px solid var(--border); padding-top: 14px;">
        <div class="section-label">Consola en tiempo real</div>
        <div class="log-panel" id="logPanel">
          <div class="log-line" style="color:#444">Esperando texto para optimizar...</div>
        </div>
      </div>

      <div class="status-bar">
        <div class="dot" id="statusDot"></div>
        <span id="statusText">Listo</span>
      </div>
    </div>
  </div>

  <!-- RIGHT: OUTPUT -->
  <div>
    <div class="card" style="height: 100%;">
      <div class="card-header">
        <div class="icon icon-green">✅</div>
        <h2>Resultado optimizado</h2>
        <button class="copy-btn" onclick="copiarResultado()">📋 Copiar todo</button>
      </div>
      <div class="card-body">
        <div id="resultPlaceholder" class="result-placeholder">
          El resultado aparecerá aquí después de optimizar.
        </div>

        <!-- SECCIÓN TEXTO CON NEGRILLAS -->
        <div id="seccionTexto" style="display:none">
          <div class="section-label">Texto con negrillas</div>
          <div class="result-panel" id="textoOptimizado"></div>
        </div>

        <!-- SECCIÓN TAGS -->
        <div id="seccionTags" style="display:none">
          <div class="section-label" style="margin-top:20px">Tags SEO (Google Trends CO)</div>
          <div class="tags-grid" id="tagsGrid"></div>
        </div>

        <!-- SECCIÓN H2s -->
        <div id="seccionH2s" style="display:none">
          <div class="section-label" style="margin-top:20px">H2s sugeridos</div>
          <div id="h2sList" style="display:flex;flex-direction:column;gap:8px;"></div>
        </div>

        <!-- MARKDOWN RAW -->
        <div id="seccionMarkdown" style="display:none">
          <div class="section-label" style="margin-top:20px; display:flex; justify-content:space-between; align-items:center;">
            <span>Markdown completo</span>
            <button class="btn btn-ghost btn-sm" onclick="descargarMarkdown()">⬇️ Descargar .md</button>
          </div>
          <div class="result-panel" id="markdownRaw" style="max-height:300px; font-family: monospace; font-size:12px;"></div>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
  let markdownCompleto = "";
  let slugActual = "";

  // Contar palabras al escribir
  document.getElementById('texto').addEventListener('input', function() {
    const val = this.value.trim();
    if (val.length > 0) {
      document.getElementById('statsRow').style.display = 'flex';
      document.getElementById('wordCount').textContent = val.split(/[\\s]+/).length;
      document.getElementById('charCount').textContent = val.length;
    }
  });

  // Auto-generar slug
  document.getElementById('texto').addEventListener('blur', function() {
    const slugEl = document.getElementById('slug');
    if (!slugEl.value && this.value.trim().length > 10) {
      const primera = this.value.trim().split('\\n')[0];
      const auto = 'articulo_' + primera.toLowerCase()
        .replace(/[^a-z0-9\\s]/g, '')
        .trim()
        .replace(/\\s+/g, '_')
        .substring(0, 40);
      slugEl.value = auto;
    }
  });

  function setStatus(estado, texto) {
    const dot = document.getElementById('statusDot');
    dot.className = 'dot ' + estado;
    document.getElementById('statusText').textContent = texto;
  }

  function addLog(msg, tipo = '') {
    const panel = document.getElementById('logPanel');
    const div = document.createElement('div');
    div.className = 'log-line ' + (
      msg.includes('✅') || msg.includes('🎉') ? 'log-ok' :
      msg.includes('⚠️') ? 'log-warn' :
      msg.includes('❌') ? 'log-err' :
      msg.includes('[') ? 'log-info' : ''
    );
    div.textContent = msg;
    panel.appendChild(div);
    panel.scrollTop = panel.scrollHeight;
  }

  function setProgress(pct) {
    document.getElementById('progressBar').style.width = pct + '%';
  }

  function setAgent(nombre, estado) {
    const el = document.getElementById('agent' + nombre);
    if (el) {
      el.className = 'agent-pill ' + estado;
    }
  }

  function resetAgents() {
    ['Camilo','Valentina','Pipe','Adriana'].forEach(a => setAgent(a, ''));
  }

  async function optimizar() {
    const texto = document.getElementById('texto').value.trim();
    const slug = document.getElementById('slug').value.trim() || 'articulo_' + Date.now();

    if (!texto || texto.length < 100) {
      alert('Por favor pega el texto completo del artículo (mínimo 100 caracteres).');
      return;
    }

    slugActual = slug;
    markdownCompleto = "";

    // Reset UI
    const btn = document.getElementById('btnOptimizar');
    btn.disabled = true;
    document.getElementById('spinner').style.display = 'block';
    document.getElementById('btnText').textContent = 'Optimizando...';
    document.getElementById('logPanel').innerHTML = '';
    document.getElementById('progressWrap').style.display = 'block';
    document.getElementById('resultPlaceholder').style.display = 'block';
    document.getElementById('seccionTexto').style.display = 'none';
    document.getElementById('seccionTags').style.display = 'none';
    document.getElementById('seccionH2s').style.display = 'none';
    document.getElementById('seccionMarkdown').style.display = 'none';
    resetAgents();
    setProgress(5);
    setStatus('running', 'Iniciando optimización...');
    addLog('🚀 Iniciando cadena de optimización SEO...');

    try {
      const resp = await fetch('/optimizar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto, slug })
      });

      const data = await resp.json();

      if (data.error) {
        addLog('❌ Error: ' + data.error, 'err');
        setStatus('', 'Error');
      } else {
        // Mostrar logs
        (data.logs || []).forEach(line => {
          addLog(line);
          if (line.includes('[Camilo]')) setAgent('Camilo', 'active');
          if (line.includes('[Valentina]')) setAgent('Valentina', 'active');
          if (line.includes('[Pipe]')) setAgent('Pipe', 'active');
          if (line.includes('[Adriana]')) setAgent('Adriana', 'active');
          if (line.includes('✅')) {
            if (line.includes('Suggest') || line.includes('Ranking')) setAgent('Camilo', 'done');
            if (line.includes('negrillas')) setAgent('Valentina', 'done');
            if (line.includes('Tags finales')) setAgent('Pipe', 'done');
            if (line.includes('Markdown')) setAgent('Adriana', 'done');
          }
        });

        setProgress(100);
        markdownCompleto = data.markdown || '';
        mostrarResultado(data);
        setStatus('active', 'Optimización completada ✓');
        addLog('🎉 ¡Proceso finalizado! Guardado en: ' + data.output_path);
      }
    } catch(e) {
      addLog('❌ Error de conexión: ' + e.message);
      setStatus('', 'Error de conexión');
    }

    btn.disabled = false;
    document.getElementById('spinner').style.display = 'none';
    document.getElementById('btnText').textContent = '⚡ Optimizar';
  }

  function mostrarResultado(data) {
    document.getElementById('resultPlaceholder').style.display = 'none';

    // Texto optimizado
    if (data.texto_optimizado) {
      document.getElementById('seccionTexto').style.display = 'block';
      document.getElementById('textoOptimizado').textContent = data.texto_optimizado;
    }

    // Tags
    if (data.tags && data.tags.length > 0) {
      document.getElementById('seccionTags').style.display = 'block';
      const grid = document.getElementById('tagsGrid');
      grid.innerHTML = '';
      data.tags.forEach(tag => {
        const chip = document.createElement('div');
        chip.className = 'tag-chip ' + (tag.score > 0 ? 'tag-hot' : 'tag-rel');
        chip.textContent = tag.score > 0 ? `🔥 ${tag.tag} (${tag.score})` : tag.tag;
        grid.appendChild(chip);
      });
    }

    // H2s
    if (data.h2s && data.h2s.length > 0) {
      document.getElementById('seccionH2s').style.display = 'block';
      const lista = document.getElementById('h2sList');
      lista.innerHTML = '';
      data.h2s.forEach(h2 => {
        const div = document.createElement('div');
        div.style.cssText = 'background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:10px 14px;font-size:13px;';
        div.textContent = '## ' + h2;
        lista.appendChild(div);
      });
    }

    // Markdown raw
    if (data.markdown) {
      document.getElementById('seccionMarkdown').style.display = 'block';
      document.getElementById('markdownRaw').textContent = data.markdown;
    }
  }

  function copiarResultado() {
    if (!markdownCompleto) { alert('Primero optimiza un artículo.'); return; }
    navigator.clipboard.writeText(markdownCompleto).then(() => {
      const btn = document.querySelector('.copy-btn');
      btn.textContent = '✅ Copiado!';
      setTimeout(() => btn.textContent = '📋 Copiar todo', 2000);
    });
  }

  function descargarMarkdown() {
    if (!markdownCompleto) { alert('Primero optimiza un artículo.'); return; }
    const blob = new Blob([markdownCompleto], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (slugActual || 'optimizacion') + '.md';
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

</body>
</html>
"""

def capturar_logs_y_ejecutar(texto, slug):
    """Ejecuta la optimización y captura logs + resultado estructurado."""
    import io, sys
    from agentes import Camilo, Valentina, Pipe, Adriana

    logs = []
    old_stdout = sys.stdout

    class LogCapture(io.TextIOBase):
        def write(self, s):
            if s.strip():
                logs.append(s.strip())
            old_stdout.write(s)
            return len(s)
        def flush(self):
            old_stdout.flush()

    sys.stdout = LogCapture()

    resultado = {
        "logs": logs,
        "texto_optimizado": "",
        "tags": [],
        "h2s": [],
        "markdown": "",
        "output_path": ""
    }

    try:
        camilo = Camilo()
        valentina = Valentina()
        pipe = Pipe()
        adriana = Adriana()

        keywords = pipe.extraer_keywords_principales(texto)
        tendencias = camilo.investigar_tendencias(keywords)
        texto_opt = valentina.optimizar_texto(texto)
        tags_raw = pipe.generar_tags(texto[:1000], tendencias, camilo=camilo)
        markdown = adriana.ensamblar_markdown(texto_opt, tags_raw)

        resultado["texto_optimizado"] = texto_opt
        resultado["markdown"] = markdown

        # Parsear tags del markdown para mostrarlos como chips
        tags_parsed = []
        in_tags = False
        for line in markdown.split('\n'):
            if '## 4.' in line or 'Tags SEO' in line:
                in_tags = True
                continue
            if in_tags and line.startswith('|') and '---' not in line and 'Tag' not in line:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if parts:
                    tag_name = parts[0]
                    score = 0
                    if 'Score real:' in line:
                        try:
                            score = int(line.split('Score real:')[1].split('/')[0].strip())
                        except:
                            pass
                    tags_parsed.append({"tag": tag_name, "score": score})
        resultado["tags"] = tags_parsed

        # Parsear H2s
        h2s = []
        in_h2 = False
        for line in markdown.split('\n'):
            if '## 3.' in line or 'Titulares H2' in line:
                in_h2 = True
                continue
            if in_h2 and line.startswith('## 4.'):
                break
            if in_h2 and line.startswith('|') and '---' not in line and 'Titular' not in line and 'H2' not in line.split('|')[0]:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if parts:
                    h2s.append(parts[0])
        resultado["h2s"] = h2s

        # Guardar archivo
        from datetime import datetime
        fecha = datetime.now().strftime("%Y-%m-%d")
        out_dir = os.path.join("output", fecha, slug)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "optimizacion-seo.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        resultado["output_path"] = out_path

    except Exception as e:
        logs.append(f"❌ Error: {str(e)}")
        resultado["error"] = str(e)
    finally:
        sys.stdout = old_stdout

    resultado["logs"] = logs
    return resultado


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/optimizar', methods=['POST'])
def optimizar():
    data = request.get_json()
    texto = data.get('texto', '').strip()
    slug = data.get('slug', 'articulo').strip()

    if not texto or len(texto) < 50:
        return jsonify({"error": "El texto es muy corto o está vacío."})

    resultado = capturar_logs_y_ejecutar(texto, slug)
    return jsonify(resultado)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    port = int(os.environ.get('PORT', 5000))
    print(f"[OK] Iniciando La Redaccion - App Web SEO en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
