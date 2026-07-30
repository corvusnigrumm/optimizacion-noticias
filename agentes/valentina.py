from groq import Groq
import os
import json
from huggingface_hub import InferenceClient

class Valentina:
    """
    Valentina: La Redactora.
    Pide a la IA una lista de frases exactas a resaltar (JSON),
    y las aplica programáticamente sobre el texto original.
    El texto JAMAS es modificado.
    """
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        self.model_name = model_name
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.hf_client = InferenceClient(api_key=os.getenv("HF_TOKEN"))
        self.system_instruction = (
            "Eres Valentina, experta editora SEO de medios colombianos. Se te entrega el texto de una noticia periodística.\n"
            "Tu única tarea es devolver un objeto JSON con la llave 'frases', que contiene un arreglo "
            "de cadenas de texto EXACTAS que aparecen en el cuerpo de la noticia y que deben resaltarse en negrilla.\n\n"
            "REGLAS CRÍTICAS DE SELECCIÓN:\n"
            "1. Las frases deben ser LITERALES: copia y pega la frase TAL CUAL aparece en el texto. Ni una letra diferente.\n"
            "2. NUNCA resaltes: el título, subtítulo, pies de foto ('Foto:'), fechas, nombres de autores ni frases de cierre institucional.\n"
            "3. Longitud ideal: entre 5 y 15 palabras. Que la frase tenga sentido completa, sin depender del contexto para entenderse.\n"
            "4. OBLIGATORIO: MÍNIMO 12 FRASES, máximo 18. Si el texto lo permite, ve al máximo.\n\n"
            "CRITERIOS DE QUÉ RESALTAR (en orden de prioridad):\n"
            "a) DATOS DUROS: cifras, estadísticas, porcentajes, fechas históricas, cantidades. Ej: 'cerca de 300 variedades'.\n"
            "b) TÉRMINOS SEO CLAVE: palabras o frases que un usuario colombiano buscaría en Google. Ej: 'arepa rellena de carne desmechada'.\n"
            "c) NOMBRES DE PREPARACIONES O RECETAS: nombres concretos de platos o técnicas. Ej: 'arepa de huevo', 'montaditos de arepa'.\n"
            "d) BENEFICIOS O PROPIEDADES: afirmaciones sobre salud, utilidad o ventaja del tema. Ej: 'respuesta glucémica menos elevada'.\n"
            "e) PASOS CLAVE DE ACCIÓN: instrucciones o pasos concretos que el lector ejecuta. Ej: 'abra la arepa por un costado'.\n"
            "f) CONCLUSIONES O AFIRMACIONES FUERTES: frases de cierre de párrafo que sintetizan la idea central.\n\n"
            "PROHIBIDO: resaltar frases genéricas sin valor informativo ('La arepa es uno de los alimentos'), "
            "frases decorativas o de transición ('Estas propuestas combinan'), ni fragmentos que no funcionen solos.\n\n"
            "Formato de respuesta OBLIGATORIO (solo el JSON, nada más):\n"
            "{\"frases\": [\"frase literal 1\", \"frase literal 2\", ...]}"
        )

    def _aplicar_negrillas(self, texto_original, frases):
        """Envuelve las frases exactas en ** dentro del texto original."""
        texto_resultado = texto_original
        for frase in frases:
            frase = frase.strip()
            if frase and frase in texto_resultado:
                texto_resultado = texto_resultado.replace(frase, f"**{frase}**", 1)
        return texto_resultado

    def _extraer_frases(self, client, model, texto_crudo, extra_kwargs=None):
        kwargs = extra_kwargs or {}
        if client == self.client:
            print("\n[Valentina] Generando respuesta: ", end="", flush=True)
            completion = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": f"Texto de la noticia:\n\n{texto_crudo}"}
                ],
                temperature=0.6,
                max_completion_tokens=2048,
                top_p=0.95,
                reasoning_effort="default",
                stream=True,
                stop=None
            )
            content = ""
            for chunk in completion:
                chunk_text = chunk.choices[0].delta.content or ""
                print(chunk_text, end="", flush=True)
                content += chunk_text
            print()
            content = content.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "", 1)
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        else:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": f"Texto de la noticia:\n\n{texto_crudo}"}
                ],
                model=model,
                response_format={"type": "json_object"},
                **kwargs
            )
            content = response.choices[0].message.content
        data = json.loads(content)
        return data.get("frases", [])

    def optimizar_texto(self, texto_crudo):
        print("[Valentina] ✍️ Identificando frases clave para resaltar...")
        try:
            frases = self._extraer_frases(self.client, self.model_name, texto_crudo)
            texto_optimizado = self._aplicar_negrillas(texto_crudo, frases)
            print(f"[Valentina] ✅ {len(frases)} negrillas aplicadas sobre el texto original.")
            return texto_optimizado
        except Exception as e:
            if "RateLimitError" in type(e).__name__ or "429" in str(e):
                print("[Valentina] ⚠️ Límite de Groq. Usando Hugging Face (Fallback)...")
                try:
                    frases = self._extraer_frases(
                        self.hf_client,
                        "meta-llama/Meta-Llama-3-8B-Instruct",
                        texto_crudo,
                        extra_kwargs={"max_tokens": 2000}
                    )
                    texto_optimizado = self._aplicar_negrillas(texto_crudo, frases)
                    print(f"[Valentina] ✅ {len(frases)} negrillas aplicadas con HF.")
                    return texto_optimizado
                except Exception as e_hf:
                    print(f"[Valentina] ❌ Error en Hugging Face: {e_hf}")
                    return texto_crudo
            else:
                print(f"[Valentina] ❌ Error: {e}")
                return texto_crudo
