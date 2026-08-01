"""
buscador_google.py — Adaptador ligero de Google Suggest

Conecta con el motor de búsquedas activas del PROYECTO PREGUNTAS GOOGLE
para enriquecer los artículos con términos que la gente realmente busca.
Si el proyecto externo no está disponible, usa una implementación directa.
"""
import sys
import os
import time
import random
import json
import requests

# --- Intento de importación del proyecto KeySearch ---
KEYSEARCH_PATH = r"C:\Users\photo\Downloads\DESCARGAS\DESCARGAS\PROYECTOS\PROYECTO PREGUNTAS GOOGLE"

_keysearch_disponible = False
if os.path.isdir(KEYSEARCH_PATH) and KEYSEARCH_PATH not in sys.path:
    sys.path.insert(0, KEYSEARCH_PATH)

try:
    from scraper.autocomplete import get_autocomplete_suggestions, get_question_suggestions
    _keysearch_disponible = True
    print("[BuscadorGoogle] ✅ Motor KeySearch conectado.")
except ImportError:
    _keysearch_disponible = False
    print("[BuscadorGoogle] ⚠️ KeySearch no disponible. Usando implementación directa.")


# --- Implementación directa (fallback sin dependencias externas) ---
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

_PREFIJOS_PREGUNTAS = [
    "qué es ", "cómo ", "por qué ", "para qué sirve ",
    "cuándo ", "cuál es ", "se puede ", "es bueno ", "es malo ",
    "cómo hacer ", "cómo saber ", "riesgos de ", "beneficios de ",
]


def _fetch_suggest(query, lang="es", country="CO"):
    """Consulta Google Suggest directamente."""
    endpoints = [
        f"https://suggestqueries.google.com/complete/search?client=chrome&hl={lang}&gl={country}&q={requests.utils.quote(query)}",
        f"https://suggestqueries.google.com/complete/search?client=firefox&hl={lang}&gl={country}&q={requests.utils.quote(query)}",
    ]
    session = requests.Session()
    for url in endpoints:
        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": f"{lang}-{country},{lang};q=0.9",
            "Referer": "https://www.google.com/",
        }
        try:
            resp = session.get(url, headers=headers, timeout=7)
            if resp.status_code == 200:
                content = resp.text
                if content.startswith("window.google.ac.h("):
                    content = content[content.find("(") + 1: content.rfind(")")]
                data = json.loads(content)
                if isinstance(data, list) and len(data) >= 2:
                    results = []
                    for s in data[1]:
                        if isinstance(s, str):
                            results.append(s.replace("<b>", "").replace("</b>", "").strip())
                        elif isinstance(s, list) and s and isinstance(s[0], str):
                            results.append(s[0].replace("<b>", "").replace("</b>", "").strip())
                    return [r for r in results if r]
        except Exception:
            continue
    return []


def obtener_busquedas_activas(keyword, n_sugerencias=30, country="CO"):
    """
    Obtiene búsquedas activas de Google Colombia para una keyword.

    Si KeySearch está disponible, lo usa. Si no, usa implementación directa.

    Args:
        keyword: Término principal del artículo
        n_sugerencias: Número máximo de sugerencias a retornar
        country: Código de país (CO = Colombia)

    Returns:
        Lista de strings con búsquedas reales de Google, filtradas y deduplicadas
    """
    print(f"[BuscadorGoogle] 🔍 Buscando tendencias activas para: '{keyword}' (CO)...")

    todas = []
    vistas = set()

    def _agregar(nuevas):
        for s in nuevas:
            s = s.strip()
            key = s.lower()
            if key and key not in vistas and keyword.lower() in key:
                vistas.add(key)
                todas.append(s)

    if _keysearch_disponible:
        try:
            ctx = {"language_code": "es", "country_code": country}
            _agregar(get_autocomplete_suggestions(keyword, expandir=True, search_context=ctx))
            _agregar(get_question_suggestions(keyword, search_context=ctx))
        except Exception as e:
            print(f"[BuscadorGoogle] ⚠️ Error KeySearch: {e}. Usando fallback.")
            _keysearch_disponible_local = False
    
    if not _keysearch_disponible or len(todas) < 5:
        # Fallback: búsqueda base
        _agregar(_fetch_suggest(keyword))
        time.sleep(random.uniform(0.5, 1.0))

        # Expandir con prefijos de preguntas
        for prefijo in _PREFIJOS_PREGUNTAS[:8]:
            _agregar(_fetch_suggest(f"{prefijo}{keyword}"))
            time.sleep(random.uniform(0.3, 0.8))
            if len(todas) >= n_sugerencias:
                break

    resultado = todas[:n_sugerencias]
    print(f"[BuscadorGoogle] ✅ {len(resultado)} búsquedas activas obtenidas.")
    return resultado


def obtener_keywords_articulo(texto_crudo, n=4):
    """
    Extrae los términos más relevantes del artículo para usar como
    semillas de búsqueda en Google Suggest.

    Retorna una lista de strings (máx n).
    """
    # Heurística rápida: extraer palabras/frases de 2-3 palabras más frecuentes
    # El pipeline completo usa Pipe para esto; aquí es un extractor ligero
    texto_lower = texto_crudo.lower()

    # Buscar preguntas del artículo como semillas naturales
    preguntas = re.findall(r"¿([^?]+)\?", texto_crudo)
    keywords = []
    for p in preguntas[:n]:
        # Tomar las primeras 4 palabras de la pregunta
        palabras = p.strip().split()[:4]
        kw = " ".join(palabras).lower()
        if len(kw) > 5:
            keywords.append(kw)

    # Complementar si hacen falta con el título
    if len(keywords) < n:
        titulo = texto_crudo.split("\n")[0].strip()
        palabras_titulo = titulo.split()
        for i in range(0, len(palabras_titulo) - 1, 2):
            chunk = " ".join(palabras_titulo[i:i+3]).lower()
            if chunk and chunk not in keywords:
                keywords.append(chunk)
                if len(keywords) >= n:
                    break

    return keywords[:n]


import re  # noqa: E402 (necesario al final para la función obtener_keywords_articulo)
