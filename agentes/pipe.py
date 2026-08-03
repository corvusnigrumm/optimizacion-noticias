import json
import os
import re
import unicodedata

from groq import Groq
from huggingface_hub import InferenceClient


class Pipe:
    """Genera tags a partir de la lectura del artículo, no de su URL ni de tendencias ajenas."""

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
Lee el artículo completo antes de etiquetarlo. Devuelve EXCLUSIVAMENTE JSON:
{"tags": ["tag 1", "tag 2"]}.

Propón de 4 a 10 tags editoriales concretos: protagonista/entidad, evento o decisión,
lugar cuando sea central, tema específico y concepto de servicio si aplica. Cada tag
debe tener de 1 a 5 palabras, estar respaldado por el texto y servir para agrupar esta
nota con otras del mismo asunto. No uses la URL, el slug, tendencias del día, frases de
autocompletado ni tags genéricos como "Noticias Colombia", "Actualidad" o "Última hora".
No inventes nombres, cifras, relaciones ni hechos que el artículo no mencione."""

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
        return sum(token in texto_tokens for token in tokens) / len(tokens) >= 0.6

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
        """Compatibilidad con Camilo: semillas extraídas del texto, sin fallback temático fijo."""
        return self._fallback_del_texto(texto_crudo)[:4]

    def generar_tags(self, texto_articulo, tendencias=None, camilo=None):
        """Etiqueta desde el artículo completo; ``tendencias`` es deliberadamente secundario."""
        print("[Pipe] Leyendo el artículo completo para generar tags editoriales...")
        candidatos = self._llamar_llm(f"ARTÍCULO COMPLETO:\n{texto_articulo}")
        tags = self._normalizar_y_filtrar(candidatos, texto_articulo)
        if not tags:
            tags = self._fallback_del_texto(texto_articulo)
        resultado = [{
            "tag": tag,
            "tipo": "Etiqueta editorial",
            "justificacion": "Etiqueta validada contra el contenido del artículo",
        } for tag in tags]
        print(f"[Pipe] {len(resultado)} tags pertinentes generados.")
        return resultado

    def run(self, texto, slug=None, tendencias=None):
        return {"texto": texto, "tags": self.generar_tags(texto, tendencias=tendencias)}


PipeAgent = Pipe
