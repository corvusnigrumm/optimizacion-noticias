import json
import os
import re

from groq import Groq
from huggingface_hub import InferenceClient


class Valentina:
    """Selecciona negrillas editoriales sin alterar el artículo original."""

    def __init__(self, model_name="qwen-2.5-32b"):
        self.model_name = model_name
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY") or "dummy_key")
        self.hf_client = InferenceClient(api_key=os.getenv("HF_TOKEN") or None)
        self.system_instruction = """Eres una editora de noticias colombianas. Lee el artículo completo y devuelve
EXCLUSIVAMENTE JSON: {"frases": ["cita literal", ...]}.

Cada cita debe copiarse literalmente del cuerpo de la noticia. Selecciona de 4 a 8,
solo si mejora la lectura rápida: datos verificables, consecuencias, decisiones,
declaraciones atribuidas o contexto indispensable. Una negrilla debe entenderse por sí
misma y tener entre 4 y 22 palabras. No uses el título, subtítulos, créditos, autor,
fechas aisladas, frases de transición, ni fragmentos genéricos. La calidad es más
importante que la cantidad: si el texto no justifica una frase, no la incluyas."""

    @staticmethod
    def _texto_normalizado(texto):
        return " ".join(texto.split()).casefold()

    def _filtrar_frases_editoriales(self, texto_crudo, frases):
        """Protege el resultado ante citas inventadas, vagas o repetidas del modelo."""
        lineas = [linea.strip() for linea in texto_crudo.splitlines() if linea.strip()]
        titulo = lineas[0].casefold() if lineas else ""
        cuerpo = self._texto_normalizado(texto_crudo)
        aceptadas, vistas = [], set()
        for frase in frases if isinstance(frases, list) else []:
            if not isinstance(frase, str):
                continue
            frase = " ".join(frase.split()).strip(" .,:;-")
            clave, palabras = frase.casefold(), frase.split()
            if (len(palabras) < 4 or len(palabras) > 22 or clave == titulo or
                    clave in vistas or clave not in cuerpo):
                continue
            tiene_dato = bool(re.search(r"\d|%|\$|\b(?:mil|millones|años|meses)\b", frase, re.I))
            tiene_entidad = bool(re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúüñ]{2,}", frase))
            tiene_hecho = bool(re.search(
                r"\b(?:anunci\w*|confirm\w*|inform\w*|explic\w*|advirti\w*|"
                r"report\w*|hall\w*|aument\w*|reduc\w*|orden\w*|aprob\w*)", frase, re.I))
            if not (tiene_dato or tiene_entidad or tiene_hecho):
                continue
            if any(clave in previa or previa in clave for previa in vistas):
                continue
            vistas.add(clave)
            aceptadas.append(frase)
            if len(aceptadas) >= 8:
                break
        return aceptadas

    def _aplicar_negrillas(self, texto_original, frases):
        resultado = texto_original
        for frase in frases:
            escaped = re.escape(frase).replace(r"\ ", r"\s+")
            resultado = re.sub(f"({escaped})", r"**\1**", resultado, count=1, flags=re.IGNORECASE)
        return resultado

    def _extraer_frases(self, client, model, texto_crudo, extra_kwargs=None):
        kwargs = extra_kwargs or {}
        if client == self.client:
            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": self.system_instruction},
                          {"role": "user", "content": f"ARTÍCULO COMPLETO:\n{texto_crudo}"}],
                temperature=0.2, max_completion_tokens=1200, response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
        else:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": self.system_instruction},
                          {"role": "user", "content": f"ARTÍCULO COMPLETO:\n{texto_crudo}"}],
                response_format={"type": "json_object"}, **kwargs,
            )
            content = response.choices[0].message.content
        try:
            return self._filtrar_frases_editoriales(texto_crudo, json.loads(content).get("frases", []))
        except (json.JSONDecodeError, AttributeError):
            return []

    def _fallback_heuristico(self, texto_crudo):
        """Fallback conservador: resalta oraciones completas con información comprobable."""
        candidatas = []
        lineas = [linea.strip() for linea in texto_crudo.splitlines() if linea.strip()]
        for linea in lineas[1:]:  # el primer renglón suele ser el título
            candidatas.extend(re.split(r"(?<=[.!?])\s+", linea))
        return self._filtrar_frases_editoriales(texto_crudo, candidatas)

    def optimizar_texto(self, texto_crudo):
        print("[Valentina] Identificando negrillas editoriales...")
        try:
            frases = self._extraer_frases(self.client, self.model_name, texto_crudo)
        except Exception as error:
            print(f"[Valentina] API principal no disponible: {error}")
            try:
                frases = self._extraer_frases(self.hf_client, "Qwen/Qwen2.5-72B-Instruct", texto_crudo,
                                               {"max_tokens": 1200})
            except Exception as hf_error:
                print(f"[Valentina] Fallback remoto no disponible: {hf_error}")
                frases = []
        if not frases:
            frases = self._fallback_heuristico(texto_crudo)
        print(f"[Valentina] {len(frases)} negrillas editoriales aplicadas.")
        return self._aplicar_negrillas(texto_crudo, frases)

    def run(self, texto, slug=None):
        texto_opt = self.optimizar_texto(texto)
        return {"texto": texto_opt, "frases": re.findall(r"\*\*(.*?)\*\*", texto_opt)}


ValentinaAgent = Valentina
