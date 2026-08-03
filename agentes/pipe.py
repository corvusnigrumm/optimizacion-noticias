import json
import os
import re
import unicodedata

from groq import Groq
from huggingface_hub import InferenceClient


class Pipe:
    """Cruza el contenido editorial con Google Suggest y Google Trends."""

    STOPWORDS = {
        "a", "al", "ante", "con", "contra", "de", "del", "desde", "el", "en", "entre", "es",
        "esta", "este", "la", "las", "lo", "los", "más", "no", "o", "para", "por", "que", "se",
        "sin", "sobre", "su", "sus", "un", "una", "y", "ya", "también", "como", "cuando", "donde",
        "noticias", "noticia", "colombia", "actualidad", "última", "hora", "caso", "tema", "país",
    }

    def __init__(self, model_name="qwen-2.5-32b"):
        self.model_name = model_name
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY") or "dummy_key")
        self.hf_client = InferenceClient(api_key=os.getenv("HF_TOKEN") or None)
        self.system_instruction = """Eres el responsable de etiquetas de un medio colombiano.
Lee el artículo completo y las consultas reales de Google Suggest. Devuelve EXCLUSIVAMENTE JSON:
{"tags": ["tag 1", "tag 2"]}.

Selecciona entre 4 y 10 tags de la lista de consultas de Google proporcionada; cópialos
exactamente. Un tag debe estar respaldado por el artículo, describir su protagonista,
hecho, lugar o tema específico, y servir para agrupar notas del mismo asunto. Descarta
consultas que solo sean tendencia pero no pertenezcan a esta nota. No uses URL, slug,
"Noticias Colombia", "Actualidad" ni "Última hora". No inventes nombres, cifras,
relaciones ni hechos que el artículo no mencione."""

    @staticmethod
    def _normalizar(texto):
        texto = unicodedata.normalize("NFKD", texto.casefold())
        return "".join(c for c in texto if not unicodedata.combining(c))

    def _palabras_significativas(self, texto):
        return [p for p in re.findall(r"[a-záéíóúüñ]{3,}", self._normalizar(texto))
                if p not in self.STOPWORDS]

    def _tag_pertinente(self, tag, texto):
        if not isinstance(tag, str):
            return False
        tag = " ".join(tag.split()).strip(".,;:!?")
        if not tag or len(tag.split()) > 5 or len(tag) > 70:
            return False
        tokens = self._palabras_significativas(tag)
        texto_tokens = set(self._palabras_significativas(texto))
        if not tokens or all(token in self.STOPWORDS for token in tokens):
            return False
        # Un tag debe poder justificarse al leer el artículo, no solo sonar relacionado.
        # Se toleran flexiones normales: "ampliación" / "ampliará".
        def aparece(token):
            return any(token == palabra or (len(token) >= 5 and token[:5] == palabra[:5])
                       for palabra in texto_tokens)
        return sum(aparece(token) for token in tokens) / len(tokens) >= 0.6

    def _normalizar_y_filtrar(self, tags, texto, limite=10):
        resultado, vistos = [], set()
        for tag in tags if isinstance(tags, list) else []:
            if isinstance(tag, dict):
                tag = tag.get("tag") or tag.get("nombre") or tag.get("name")
            if not isinstance(tag, str):
                continue
            tag = " ".join(tag.split()).strip(".,;:!?")
            clave = self._normalizar(tag)
            if clave in vistos or not self._tag_pertinente(tag, texto):
                continue
            vistos.add(clave)
            resultado.append(tag)
            if len(resultado) >= limite:
                break
        return resultado

    def _semillas_del_texto(self, texto_crudo):
        """Extrae anclas temáticas del artículo para consultar Google sin usar su URL."""
        candidatos = []
        candidatos.extend(re.findall(
            r"\b[A-ZÁÉÍÓÚÑ][\wáéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÑ][\wáéíóúüñ]+){1,3}\b", texto_crudo
        ))
        palabras = self._palabras_significativas(texto_crudo)
        frecuencias = {}
        for palabra in palabras:
            frecuencias[palabra] = frecuencias.get(palabra, 0) + 1
        candidatos.extend([p for p, _ in sorted(frecuencias.items(), key=lambda item: (-item[1], item[0]))])
        return self._normalizar_y_filtrar(candidatos, texto_crudo, limite=4)

    def _llamar_llm(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "system", "content": self.system_instruction},
                          {"role": "user", "content": prompt}],
                temperature=0.15, max_completion_tokens=900, response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content).get("tags", [])
        except Exception as error:
            print(f"[Pipe] API principal no disponible: {error}")
            try:
                response = self.hf_client.chat.completions.create(
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=[{"role": "system", "content": self.system_instruction},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}, max_tokens=900,
                )
                return json.loads(response.choices[0].message.content).get("tags", [])
            except Exception as hf_error:
                print(f"[Pipe] Fallback remoto no disponible: {hf_error}")
                return []

    def _fallback_del_texto(self, texto):
        """Construye pocas etiquetas trazables al texto si el modelo no responde."""
        candidatos = []
        # Entidades de dos o más palabras primero; suelen ser las etiquetas más útiles.
        candidatos.extend(re.findall(r"\b[A-ZÁÉÍÓÚÑ][\wáéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÑ][\wáéíóúüñ]+){1,3}\b", texto))
        frecuencias = {}
        palabras = self._palabras_significativas(texto)
        for palabra in palabras:
            frecuencias[palabra] = frecuencias.get(palabra, 0) + 1
        candidatos.extend([p for p, _ in sorted(frecuencias.items(), key=lambda item: (-item[1], item[0]))])
        return self._normalizar_y_filtrar(candidatos, texto, limite=8)

    def extraer_keywords_principales(self, texto_crudo):
        """Semillas para Google Suggest obtenidas exclusivamente del contenido."""
        semillas = self._semillas_del_texto(texto_crudo)
        return semillas or self._fallback_del_texto(texto_crudo)[:4]

    def generar_tags(self, texto_articulo, tendencias=None, camilo=None):
        """Selecciona consultas reales de Google que además sean pertinentes a la nota."""
        tendencias = tendencias or []
        candidatos_google = self._normalizar_y_filtrar(tendencias, texto_articulo, limite=30)
        print(f"[Pipe] {len(candidatos_google)} consultas de Google Suggest pertinentes para evaluar.")
        if candidatos_google:
            prompt = (
                f"ARTÍCULO COMPLETO:\n{texto_articulo}\n\n"
                f"CONSULTAS REALES DE GOOGLE SUGGEST:\n{json.dumps(candidatos_google, ensure_ascii=False)}"
            )
            candidatos = self._llamar_llm(prompt)
            # El modelo solo puede devolver consultas que Google Suggest entregó.
            mapa_google = {self._normalizar(tag): tag for tag in candidatos_google}
            candidatos = [mapa_google[self._normalizar(tag)] for tag in candidatos
                           if isinstance(tag, str) and self._normalizar(tag) in mapa_google]
        else:
            candidatos = []
        tags = self._normalizar_y_filtrar(candidatos, texto_articulo)
        if not tags:
            tags = candidatos_google[:10]
        resultado = [{
            "tag": tag,
            "tipo": "Google Suggest + relevancia editorial",
            "justificacion": "Consulta real de Google Suggest validada contra el artículo",
        } for tag in tags]
        print(f"[Pipe] {len(resultado)} tags de Google Suggest pertinentes generados.")
        return resultado

    def run(self, texto, slug=None, tendencias=None):
        return {"texto": texto, "tags": self.generar_tags(texto, tendencias=tendencias)}


PipeAgent = Pipe
