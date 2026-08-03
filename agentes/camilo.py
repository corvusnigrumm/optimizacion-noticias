import requests
import json
import random
import xml.etree.ElementTree as ET
from pytrends.request import TrendReq

USER_AGENT_PROFILES = [
    {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
    {"ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"},
    {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"},
]

class Camilo:
    """
    Camilo: El Rastreador (v2).
    Se conecta al endpoint de autocompletado de Google Suggest rotando User-Agents
    para obtener las consultas exactas que los usuarios escriben en Colombia.
    Reemplaza a PyTrends.
    """
    def __init__(self, lang='es', country='CO'):
        self.lang = lang
        self.country = country
        self.session = requests.Session()
        self.pytrends = TrendReq(hl=f'{lang}-{country.lower()}', tz=360)
        
    def _consultar_keyword(self, keyword):
        """Consulta Google Suggest para un keyword y retorna la lista de sugerencias."""
        endpoints = [
            "https://suggestqueries.google.com/complete/search?client=chrome&hl={lang}&gl={country}&q={query}",
            "https://suggestqueries.google.com/complete/search?client=firefox&hl={lang}&gl={country}&q={query}",
            "https://www.google.com/complete/search?client=psy-ab&hl={lang}&gl={country}&q={query}",
            "https://suggestqueries.google.com/complete/search?client=psy&hl={lang}&gl={country}&q={query}",
            "https://www.google.com/complete/search?client=chrome&hl={lang}&q={query}"
        ]
        for url_template in endpoints:
            url = url_template.format(
                lang=self.lang,
                country=self.country,
                query=requests.utils.quote(keyword),
            )
            perfil = random.choice(USER_AGENT_PROFILES)
            headers = {
                "User-Agent": perfil["ua"],
                "Accept": "*/*",
                "Accept-Language": f"{self.lang}-{self.country},{self.lang};q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.google.com/",
                "X-Requested-With": "XMLHttpRequest"
            }
            try:
                resp = self.session.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    content = resp.text
                    if content.startswith("window.google.ac.h("):
                        content = content[content.find("(")+1 : content.rfind(")")]
                    try:
                        data = json.loads(content)
                    except:
                        continue
                    if isinstance(data, list) and len(data) >= 2:
                        suggestions = data[1]
                        if not suggestions:
                            continue
                        extracted = []
                        for s in suggestions:
                            if isinstance(s, str):
                                extracted.append(s)
                            elif isinstance(s, list) and s and isinstance(s[0], str):
                                extracted.append(s[0])
                            elif isinstance(s, dict):
                                phrase = s.get("phrase") or s.get("q") or s.get("suggestion")
                                if phrase:
                                    extracted.append(phrase)
                        if extracted:
                            clean = [s.replace('<b>', '').replace('</b>', '').strip() for s in extracted]
                            return clean
                elif resp.status_code == 429:
                    continue
        # Fallback a DuckDuckGo si Google bloquea la IP (429) en Data Centers como Render
        try:
            ddg_url = f"https://duckduckgo.com/ac/?q={requests.utils.quote(keyword)}&kl={self.country.lower()}-{self.lang}"
            ddg_headers = {"User-Agent": random.choice(USER_AGENT_PROFILES)["ua"]}
            res = self.session.get(ddg_url, headers=ddg_headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                extracted = [item.get('phrase') for item in data if isinstance(item, dict) and item.get('phrase')]
                if extracted:
                    print(f"[Camilo] 🦆 Usando fallback de DuckDuckGo para '{keyword}' (Google bloqueado)")
                    return extracted
        except Exception:
            pass

        return []

    def _obtener_tendencias_rss(self):
        """Obtiene las tendencias calientes del día directamente del RSS de Google Trends para Colombia."""
        print(f"[Camilo] \U0001f525 Buscando tendencias en caliente del día en Google Trends RSS ({self.country})...")
        url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={self.country}"
        perfil = random.choice(USER_AGENT_PROFILES)
        headers = {"User-Agent": perfil["ua"]}
        tendencias = []
        try:
            resp = self.session.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    if title is not None and title.text:
                        tendencias.append(title.text.strip())
        except Exception as e:
            print(f"[Camilo] \u26a0\ufe0f Error obteniendo RSS Trends: {e}")
        return tendencias

    def rankear_tags_por_volumen(self, tags_candidatos, timeframe='now 7-d'):
        """
        Recibe una lista de strings (tags candidatos) y consulta pytrends para
        obtener el interés de búsqueda real en Colombia (escala 0-100) de cada uno.

        Procesa en lotes de 5 (límite de pytrends) con pausa entre lotes.
        Devuelve lista de dicts ordenada de mayor a menor score:
          [{"tag": "...", "score": 85, "fuente": "Google Trends (7 días, CO)"}, ...]
        """
        import time

        print(f"[Camilo] 📊 Midiendo volumen real de {len(tags_candidatos)} tags candidatos con pytrends (CO)...")

        scores = {}
        medidos = set()
        BATCH = 5
        lotes = [tags_candidatos[i:i+BATCH] for i in range(0, len(tags_candidatos), BATCH)]

        for idx, lote in enumerate(lotes):
            try:
                self.pytrends.build_payload(lote, cat=0, timeframe=timeframe, geo=self.country, gprop='')
                df = self.pytrends.interest_over_time()

                if df.empty:
                    for tag in lote:
                        scores[tag] = 0
                else:
                    cols = [c for c in df.columns if c != 'isPartial']
                    for tag in lote:
                        if tag in cols:
                            scores[tag] = int(df[tag].mean())
                            medidos.add(tag)
                        else:
                            scores[tag] = 0

                if idx < len(lotes) - 1:
                    time.sleep(8 + random.uniform(1, 4))  # pausa más larga para evitar rate limit

            except Exception as e:
                err = str(e)
                if "429" in err or "Too Many Requests" in err:
                    print(f"[Camilo] ⚠️ Rate limit de Google Trends en lote {idx+1}. Esperando 20s y continuando...")
                    time.sleep(20)
                else:
                    print(f"[Camilo] ⚠️ Error en lote {idx+1}: {e}")
                for tag in lote:
                    scores[tag] = 0

        resultado = sorted(
            [{"tag": t, "score": scores.get(t, 0),
              "fuente": "Google Trends (7 días, CO)" if t in medidos else "Google Trends sin datos"}
             for t in tags_candidatos],
            key=lambda x: x["score"],
            reverse=True
        )

        print(f"[Camilo] ✅ Ranking completado. Top 5 por volumen real:")
        for item in resultado[:5]:
            print(f"[Camilo]   🏆 '{item['tag']}': score {item['score']}/100")

        return resultado

    def investigar_tendencias(self, keywords):
        """
        Recibe una lista de keywords (o un string) y consulta Google Suggest
        para cada uno. Retorna una lista combinada y deduplicada de sugerencias reales.
        """
        if isinstance(keywords, str):
            keywords = [keywords]

        print(f"[Camilo] \U0001f575\ufe0f\u200d\u2642\ufe0f Consultando Google Suggest para {len(keywords)} keywords: {keywords}")

        todas_las_sugerencias = []
        vistas = set()

        for kw in keywords:
            sugerencias = self._consultar_keyword(kw)
            nuevas = []
            for s in sugerencias:
                s_lower = s.lower()
                if s_lower not in vistas:
                    vistas.add(s_lower)
                    nuevas.append(s)
            if nuevas:
                print(f"[Camilo]   \u2192 '{kw}': {len(nuevas)} sugerencias nuevas")
                todas_las_sugerencias.extend(nuevas)
            else:
                print(f"[Camilo]   \u26a0\ufe0f '{kw}': sin sugerencias")

        total = len(todas_las_sugerencias)
        if total > 0:
            print(f"[Camilo] \u2705 Total acumulado Suggest: {total} sugerencias.")
        
        # No se añaden tendencias globales del RSS: pueden ser populares, pero no
        # prueban relación con la nota. Trends medirá los candidatos de Suggest.

        return todas_las_sugerencias

    def run(self, texto, slug=None):
        """Método de compatibilidad con el pipeline de app_web."""
        print(f"[Camilo] Ejecutando análisis semántico para: {slug or 'nota'}...")
        kw = slug.replace('_', ' ') if slug else "noticias colombia"
        sugerencias = self.investigar_tendencias([kw])
        return {"texto": texto, "tags": sugerencias, "sugerencias": sugerencias}

CamiloAgent = Camilo
