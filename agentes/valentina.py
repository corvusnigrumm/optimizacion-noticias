from groq import Groq
import os
import json
import re
from huggingface_hub import InferenceClient

class Valentina:
    """
    Valentina: La Redactora.
    Pide a la IA una lista de frases exactas a resaltar (JSON),
    y las aplica programáticamente sobre el texto original.
    El texto JAMAS es modificado.
    """
    def __init__(self, model_name="qwen-2.5-32b"):
        self.model_name = model_name
        groq_key = os.getenv("GROQ_API_KEY") or "dummy_key"
        self.client = Groq(api_key=groq_key)
        hf_token = os.getenv("HF_TOKEN") or None
        self.hf_client = InferenceClient(api_key=hf_token)
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
        """Envuelve las frases exactas en ** dentro del texto original usando regex tolerante."""
        texto_resultado = texto_original
        for frase in frases:
            frase = frase.strip()
            if frase:
                # Escape para regex y permitir espacios variables/saltos de línea
                escaped = re.escape(frase).replace(r'\ ', r'\s+')
                # Reemplazar la primera ocurrencia ignorando mayúsculas/minúsculas
                texto_resultado = re.sub(f'({escaped})', r'**\1**', texto_resultado, count=1, flags=re.IGNORECASE)
        return texto_resultado

    def _extraer_frases(self, client, model, texto_crudo, extra_kwargs=None):
        kwargs = extra_kwargs or {}
        if client == self.client:
            print("\n[Valentina] Generando respuesta: ", end="", flush=True)
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": f"Texto de la noticia:\n\n{texto_crudo}"}
                ],
                temperature=0.6,
                max_completion_tokens=2048,
                top_p=0.95,
                stream=True,
                stop=None
            )
            content = ""
            for chunk in completion:
                chunk_text = chunk.choices[0].delta.content or ""
                print(chunk_text, end="", flush=True)
                content += chunk_text
            print()
            
            # Limpiar bloque <think>
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            
            # Extraer solo el bloque JSON
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                content = match.group(0)
            
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
            
        try:
            data = json.loads(content)
            return data.get("frases", [])
        except json.JSONDecodeError as e:
            print(f"[Valentina] ❌ Error decodificando JSON: {e}")
            return []

    def _fallback_heuristico(self, texto_crudo):
        """Genera negrillas por regla heurística cuando no hay API Key o falla el LLM."""
        import re
        lineas = [l.strip() for l in texto_crudo.split("\n") if l.strip()]
        frases = []
        for i, l_str in enumerate(lineas):
            # 1. Extraer entidades, fechas, cifras y nombres propios
            coincidencias = re.findall(r'([A-ZÁÉÍÓÚÑ][a-záéíóúüñ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ0-9][a-záéíóúüñ0-9]*)*|\$\d+(?:\.\d+)?|\d+%\s*|\b\d{4}\b)', l_str)
            for c in coincidencias:
                c_clean = c.strip()
                if len(c_clean) >= 4 and c_clean not in frases:
                    frases.append(c_clean)
            # 2. Si no hay suficientes coincidencias, tomar tramos de 4 a 7 palabras
            if len(frases) < 4 and len(l_str.split()) >= 4:
                palabras = l_str.split()
                sub = " ".join(palabras[:min(7, len(palabras))])
                if sub not in frases:
                    frases.append(sub)
        return frases[:14]

    def optimizar_texto(self, texto_crudo):
        print("[Valentina] ✍️ Identificando frases clave para resaltar...")
        try:
            frases = self._extraer_frases(self.client, self.model_name, texto_crudo)
            if not frases:
                frases = self._fallback_heuristico(texto_crudo)
            texto_optimizado = self._aplicar_negrillas(texto_crudo, frases)
            print(f"[Valentina] ✅ {len(frases)} negrillas aplicadas sobre el texto original.")
            return texto_optimizado
        except Exception as e:
            print(f"[Valentina] ⚠️ Excepción en API primaria: {e}. Intentando fallback HF...")
            try:
                frases = self._extraer_frases(
                    self.hf_client,
                    "Qwen/Qwen2.5-72B-Instruct",
                    texto_crudo,
                    extra_kwargs={"max_tokens": 2000}
                )
                if not frases:
                    frases = self._fallback_heuristico(texto_crudo)
                texto_optimizado = self._aplicar_negrillas(texto_crudo, frases)
                print(f"[Valentina] ✅ {len(frases)} negrillas aplicadas con HF.")
                return texto_optimizado
            except Exception as e_hf:
                print(f"[Valentina] ⚠️ Error en HF ({e_hf}). Aplicando heurística local...")
                frases = self._fallback_heuristico(texto_crudo)
                texto_optimizado = self._aplicar_negrillas(texto_crudo, frases)
                print(f"[Valentina] ✅ {len(frases)} negrillas aplicadas localmente.")
                return texto_optimizado

    def run(self, texto, slug=None):
        """Método de compatibilidad con app_web."""
        texto_opt = self.optimizar_texto(texto)
        frases = re.findall(r'\*\*(.*?)\*\*', texto_opt)
        return {"texto": texto_opt, "frases": frases}

ValentinaAgent = Valentina

