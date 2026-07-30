import json
from groq import Groq
import os
from huggingface_hub import InferenceClient


class Pipe:
    """
    Pipe: El Estratega SEO (v2).
    Pipeline de 2 etapas:
      Etapa 1 → LLM genera 24 tags candidatos (pool amplio).
      Etapa 2 → pytrends mide el volumen real (0-100) de cada candidato en CO.
      Resultado → Top 12 por score real, con el dato de volumen en la justificación.
    """
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        self.model_name = model_name
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.hf_client = InferenceClient(api_key=os.getenv("HF_TOKEN"))
        self.system_instruction = (
            "Eres Pipe, un experto estratega de SEO y Google Discover para medios de comunicación en Colombia. "
            "Debes leer el resumen de un texto y generar una lista de tags enfocados al 100% en optimización para Google Discover.\n\n"
            "REGLAS CRÍTICAS:\n"
            "1. Discover usa nodos de interés amplios, entidades reales y categorías temáticas de tendencia.\n"
            "2. Debes generar EXACTAMENTE 24 TAGS candidatos como un arreglo de strings simples.\n"
            "3. Todos los tags deben ser búsquedas reales basadas en los términos de Google Trends/Suggest provistos.\n"
            "4. PROHIBICIÓN: NUNCA uses créditos de imágenes (iStock, Getty, Shutterstock, etc.).\n"
            "5. Cada tag: máximo 3 palabras. NUNCA frases largas ni oraciones.\n"
            "6. Evita términos genéricos de una sola palabra abstracta (ej. 'Educación', 'Niños', 'País').\n\n"
            "Tu respuesta DEBE ser EXCLUSIVAMENTE un objeto JSON con la llave 'tags' conteniendo el arreglo de strings:\n"
            "{\"tags\": [\"Tag Uno\", \"Tag Dos\", \"Tag Tres\", ...]}"
        )

    def extraer_keywords_principales(self, texto_crudo):
        """
        Extrae 4 keywords temáticas amplias del artículo para que Camilo
        consulte Google Suggest con cada una y acumule tendencias reales.
        """
        print("[Pipe] 🧠 Analizando el texto para extraer múltiples keywords temáticas...")
        prompt = (
            "Eres un experto en SEO de noticias para medios colombianos. Lee el siguiente fragmento de una noticia "
            "periodística y genera EXACTAMENTE 4 palabras clave o términos de búsqueda MUY ESPECÍFICOS, "
            "basados en 'tendencias en caliente' (hot trends). "
            "Deben incluir nombres propios, enfrentamientos concretos, eventos de última hora o la controversia central. "
            "Por ejemplo, si el artículo habla de la cancelación de la Finalissima, "
            "los keywords serían: 'Finalissima 2026', 'España vs Argentina', "
            "'por qué se canceló Finalissima', 'Mundial 2026 Finalissima'. "
            "Responde ÚNICAMENTE con un objeto JSON válido con la llave 'keywords' que contenga el arreglo. "
            "Ejemplo: {\"keywords\": [\"termino uno\", \"termino dos\", \"termino tres\", \"termino cuatro\"]}\n\n"
            f"TEXTO:\n{texto_crudo[:1500]}"
        )
        fallback = ["noticias colombia", "bogota hoy", "colombia actualidad", "noticias bogota"]
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Responde única y exclusivamente con el JSON solicitado."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model_name,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            keywords = data.get("keywords", fallback)
            if not isinstance(keywords, list) or len(keywords) == 0:
                keywords = fallback
            print(f"[Pipe] 🎯 Keywords temáticas extraídas: {keywords}")
            return keywords
        except Exception as e:
            if "RateLimitError" in type(e).__name__ or "429" in str(e):
                print("[Pipe] ⚠️ Límite de Groq. Usando Hugging Face (Fallback)...")
                try:
                    response_hf = self.hf_client.chat.completions.create(
                        model="meta-llama/Meta-Llama-3-8B-Instruct",
                        messages=[
                            {"role": "system", "content": "Responde única y exclusivamente con el JSON solicitado."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150
                    )
                    data = json.loads(response_hf.choices[0].message.content)
                    keywords = data.get("keywords", fallback)
                    print(f"[Pipe] 🎯 Keywords extraídas con HF: {keywords}")
                    return keywords
                except Exception as e_hf:
                    print(f"[Pipe] ❌ Error extrayendo keywords con HF: {e_hf}")
                    return fallback
            else:
                print(f"[Pipe] ❌ Error extrayendo keywords: {e}")
                return fallback

    def _normalizar_tags(self, raw):
        """Convierte la respuesta del LLM (lista de strings o lista de dicts) a lista de strings."""
        resultado = []
        for t in raw:
            if isinstance(t, str) and t.strip():
                resultado.append(t.strip())
            elif isinstance(t, dict):
                tag_str = t.get("tag") or t.get("nombre") or t.get("name") or ""
                if tag_str.strip():
                    resultado.append(tag_str.strip())
        return resultado

    def _llamar_llm_candidatos(self, prompt):
        """Llama al LLM principal o al fallback de HF para obtener tags candidatos."""
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": prompt}
                ],
                model=self.model_name,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return self._normalizar_tags(data.get("tags", []))
        except Exception as e:
            if "RateLimitError" in type(e).__name__ or "429" in str(e):
                print("[Pipe] ⚠️ Rate limit Groq → usando Hugging Face para candidatos...")
                try:
                    response_hf = self.hf_client.chat.completions.create(
                        model="meta-llama/Meta-Llama-3-8B-Instruct",
                        messages=[
                            {"role": "system", "content": self.system_instruction},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=1200
                    )
                    data = json.loads(response_hf.choices[0].message.content)
                    return self._normalizar_tags(data.get("tags", []))
                except Exception as e_hf:
                    print(f"[Pipe] ❌ Error HF generando candidatos: {e_hf}")
            else:
                print(f"[Pipe] ❌ Error LLM generando candidatos: {e}")
        return []

    def generar_tags(self, resumen_texto, tendencias, camilo=None):
        """
        Pipeline de 2 etapas:
          Etapa 1 → LLM genera 24 tags candidatos (pool amplio de strings simples).
          Etapa 2 → Camilo rankea los candidatos con pytrends (score 0-100 real en CO).
          Resultado → Top 12 por volumen real, con score documentado en justificación.

        Si camilo=None se salta el ranking y se devuelven los primeros 12 sin score.
        """
        TARGET = 12
        N_CANDIDATOS = 24

        print(f"[Pipe] 🏷️  Etapa 1/2 — Generando {N_CANDIDATOS} tags candidatos con el LLM...")

        prompt = (
            f"Basado en este texto: '{resumen_texto[:600]}...'\n"
            f"Y estas tendencias reales de Google Suggest/Trends para Colombia: {tendencias}\n\n"
            f"Genera EXACTAMENTE {N_CANDIDATOS} tags candidatos bajo la llave 'tags' como arreglo de strings cortos. "
            f"Mezcla: términos específicos del artículo + términos reales de las tendencias provistas. "
            f"Máximo 3 palabras por tag. Sin créditos de fotos. Sin frases genéricas abstractas. "
            f"CUENTA antes de responder que sean exactamente {N_CANDIDATOS}."
        )

        # Intentar hasta 2 veces para obtener al menos 12 candidatos
        candidatos = []
        for intento in range(1, 3):
            candidatos_intento = self._llamar_llm_candidatos(prompt)
            if len(candidatos_intento) > len(candidatos):
                candidatos = candidatos_intento
            if len(candidatos) >= TARGET:
                break
            if intento < 2:
                print(f"[Pipe] ⚠️ Solo {len(candidatos)} candidatos en intento {intento}. Reintentando...")

        if not candidatos:
            print("[Pipe] ❌ No se obtuvieron candidatos. Abortando generación de tags.")
            return []

        print(f"[Pipe] 🎲 {len(candidatos)} candidatos generados.")

        # Etapa 2: Ranking por volumen real con pytrends
        if camilo is not None and len(candidatos) > TARGET:
            print(f"[Pipe] 📈 Etapa 2/2 — Rankeando {len(candidatos)} candidatos por volumen real en Google Trends CO...")
            ranking = camilo.rankear_tags_por_volumen(candidatos)
            tags_finales = []
            for item in ranking[:TARGET]:
                score = item["score"]
                if score > 0:
                    tipo = "Tendencia verificada"
                    justificacion = f"Score real: {score}/100 — Google Trends CO (últimos 7 días)"
                else:
                    tipo = "Relevancia temática"
                    justificacion = "Relevante para el tema (volumen no disponible en Google Trends)"
                tags_finales.append({
                    "tag": item["tag"],
                    "tipo": tipo,
                    "justificacion": justificacion
                })
        else:
            if camilo is None:
                print("[Pipe] ⚠️ Sin instancia de Camilo — seleccionando primeros 12 sin ranking de volumen.")
            tags_finales = [
                {
                    "tag": t,
                    "tipo": "Candidato LLM",
                    "justificacion": "Seleccionado por relevancia temática (sin ranking de volumen)"
                }
                for t in candidatos[:TARGET]
            ]

        cantidad = len(tags_finales)
        if cantidad == TARGET:
            print(f"[Pipe] ✅ ¡{TARGET} Tags finales seleccionados con éxito!")
        else:
            print(f"[Pipe] ⚠️ Se obtuvieron {cantidad}/{TARGET} tags.")
        return tags_finales
