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
        self.system_instruction = """Eres la editora de estilo de un medio colombiano. Lee el artículo completo
y devuelve EXCLUSIVAMENTE JSON: {"frases": ["cita literal", ...]}.

Las negrillas deben reproducir un patrón editorial de noticias de servicio: cerca de
3 o 4 por cada 100 palabras. Elige fragmentos LITERALES de 4 a 16 palabras (pueden ser
fragmentos, no tienen que ser oraciones completas). Si el primer renglón es el titular,
inclúyelo. Incluye todos los subtítulos o preguntas que organizan la nota y, en cada
sección, resalta el concepto que permite leerla rápido: problema, mecanismo, condición,
paso, resultado, beneficio, advertencia o cifra.

Una buena selección cubre el recorrido de la nota —qué es, cómo funciona, qué hacer y
qué precaución tomar—, no una lista de palabras SEO. No resaltes conectores, adjetivos
vacíos, sujetos genéricos, fechas aisladas, autor, créditos, cierre institucional ni
dos variantes de la misma idea. Copia exactamente el texto, sin inventar ni corregir."""

    @staticmethod
    def _texto_normalizado(texto):
        return " ".join(texto.split()).casefold()

    def _filtrar_frases_editoriales(self, texto_crudo, frases):
        """Valida citas literales y conserva la densidad de negrillas del patrón editorial."""
        lineas = [linea.strip() for linea in texto_crudo.splitlines() if linea.strip()]
        titulo = lineas[0].casefold() if lineas else ""
        cuerpo = self._texto_normalizado(texto_crudo)
        objetivo = min(24, max(10, round(len(cuerpo.split()) * 3.5 / 100)))
        aceptadas, vistas = [], set()
        for frase in frases if isinstance(frases, list) else []:
            if not isinstance(frase, str):
                continue
            frase = " ".join(frase.split()).strip(" .,:;-")
            clave, palabras = frase.casefold(), frase.split()
            es_titular = clave == titulo and len(palabras) >= 6
            if (len(palabras) < 3 or len(palabras) > 18 or clave in vistas or
                    clave not in cuerpo):
                continue
            palabras_utiles = re.findall(r"[a-záéíóúüñ]{3,}", clave)
            # Evita marcar restos gramaticales como "en la casa" o "para funcionar".
            if not es_titular and len(set(palabras_utiles) - {
                "para", "como", "esta", "este", "desde", "hasta", "sobre", "entre",
                "tambien", "porque", "cuando", "donde", "todos", "todas", "puede",
                "pueden", "ser", "hacer", "tener", "suele", "solo", "casa",
            }) < 2:
                continue
            if any(clave in previa or previa in clave for previa in vistas):
                continue
            vistas.add(clave)
            aceptadas.append(frase)
            if len(aceptadas) >= objetivo:
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
        """Fallback por fragmentos: conserva conceptos y acciones, no oraciones enteras."""
        candidatas = []
        lineas = [linea.strip() for linea in texto_crudo.splitlines() if linea.strip()]
        if lineas and len(lineas[0].split()) >= 6:
            candidatas.append(lineas[0])
        for linea in lineas[1:]:
            if len(linea.split()) <= 12 and (linea.endswith(":") or linea.endswith("?")):
                candidatas.append(linea)
            for oracion in re.split(r"(?<=[.!?])\s+", linea):
                palabras = oracion.strip().split()
                if not 5 <= len(palabras) <= 40:
                    continue
                # Ventanas cortas alrededor de cifras, verbos de acción y el inicio factual.
                puntos = [0]
                for indice, palabra in enumerate(palabras):
                    if (re.search(r"\d", palabra) or re.search(
                            r"(recom|evit|util|permit|ayud|reduce|aument|protege|sirve|debe)",
                            palabra, re.I)):
                        puntos.append(max(0, indice - 3))
                for inicio in puntos:
                    fragmento = " ".join(palabras[inicio:inicio + 11]).strip(" ,;:")
                    if len(fragmento.split()) >= 4:
                        candidatas.append(fragmento)
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
