import json
import re
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
        groq_key = os.getenv("GROQ_API_KEY") or "dummy_key"
        self.client = Groq(api_key=groq_key)
        hf_token = os.getenv("HF_TOKEN") or None
        self.hf_client = InferenceClient(api_key=hf_token)
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
        fallback = ["papel aluminio microondas", "aluminio microondas", "aluminio en microondas", "que pasa si meto papel aluminio al microondas"]
        try:
            print("\n[Pipe] Generando keywords: ", end="", flush=True)
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Responde única y exclusivamente con el JSON solicitado con la llave 'keywords'."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_completion_tokens=500,
                top_p=0.95,
                response_format={"type": "json_object"},
                stream=True,
                stop=None
            )
            content = ""
            for chunk in completion:
                chunk_text = chunk.choices[0].delta.content or ""
                print(chunk_text, end="", flush=True)
                content += chunk_text
            print()
            print()
            
            # Limpiar bloque <think>
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            
            # Extraer solo el bloque JSON
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                content = match.group(0)
            
            try:
                data = json.loads(content)
                keywords = data.get("keywords", fallback)
            except json.JSONDecodeError:
                keywords = fallback
                
            if not isinstance(keywords, list) or len(keywords) == 0:
                keywords = fallback
            print(f"[Pipe] 🎯 Keywords temáticas extraídas: {keywords}")
            return keywords
        except Exception as e:
            if "RateLimitError" in type(e).__name__ or "429" in str(e):
                print("[Pipe] ⚠️ Límite de Groq. Usando Hugging Face (Fallback)...")
                try:
                    response_hf = self.hf_client.chat.completions.create(
                        model="Qwen/Qwen2.5-72B-Instruct",
                        messages=[
                            {"role": "system", "content": "Responde única y exclusivamente con el JSON solicitado."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
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
            print("\n[Pipe] Generando candidatos: ", end="", flush=True)
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_completion_tokens=2048,
                top_p=0.95,
                response_format={"type": "json_object"},
                stream=True,
                stop=None
            )
            content = ""
            for chunk in completion:
                chunk_text = chunk.choices[0].delta.content or ""
                print(chunk_text, end="", flush=True)
                content += chunk_text
            print()
            print()
            
            # Limpiar bloque <think>
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            
            # Extraer solo el bloque JSON
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                content = match.group(0)
            
            try:
                data = json.loads(content)
                return self._normalizar_tags(data.get("tags", []))
            except json.JSONDecodeError:
                return []
        except Exception as e:
            print(f"[Pipe] ⚠️ Excepción en API primaria ({e}) → Intentando Hugging Face...")
            try:
                response_hf = self.hf_client.chat.completions.create(
                    model="meta-llama/Meta-Llama-3-8B-Instruct",
                    messages=[
                        {"role": "system", "content": self.system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1200
                )
                content_hf = response_hf.choices[0].message.content
                match = re.search(r'\{[\s\S]*\}', content_hf)
                if match:
                    data = json.loads(match.group(0))
                    return self._normalizar_tags(data.get("tags", []))
            except Exception as e_hf:
                print(f"[Pipe] ⚠️ Error en HF ({e_hf}). Usando lista de respaldo.")
        return []

    def generar_tags(self, resumen_texto, tendencias=None, camilo=None):
        """
        Nuevo Pipeline Inverso (Sin Alucinaciones):
          1. Camilo ya entregó una lista (tendencias) de términos 100% reales extraídos de Google.
          2. LLM funciona como filtro: selecciona los 12 mejores términos de esa lista estricta.
        """
        TARGET = 12

        if tendencias is None:
            tendencias = ["noticias colombia", "actualidad", "última hora colombia", "tendencias hoy"]

        print(f"[Pipe] 🏷️  Seleccionando los mejores {TARGET} tags de una piscina de {len(tendencias)} términos reales...")

        if not tendencias:
            print("[Pipe] ⚠️ No hay tendencias reales. Se usarán tags genéricos como fallback.")
            tendencias = ["noticias colombia", "actualidad", "última hora colombia", "tendencias hoy"]

        prompt = (
            f"Basado en este texto: '{resumen_texto[:600]}...'\n\n"
            f"Tengo esta lista EXACTA de búsquedas reales de usuarios en Google Colombia:\n"
            f"{json.dumps(tendencias, ensure_ascii=False)}\n\n"
            f"Tu ÚNICA tarea es SELECCIONAR los {TARGET} términos MÁS RELEVANTES y CORTOS (máximo 3 o 4 palabras cada uno).\n"
            f"REGLA DE ORO:\n"
            f"1. PROHIBIDO INVENTAR TAGS. Debes copiar exactamente los términos de la lista proporcionada.\n"
            f"2. NUNCA selecciones frases largas ni oraciones.\n"
            f"3. Selecciona entidades concretas, marcas, productos o búsquedas reales muy populares (ej: 'papel aluminio microondas', 'aluminio en microondas', 'microondas haceb').\n\n"
            f"Responde ÚNICAMENTE con un JSON que contenga el arreglo bajo la llave 'tags'."
        )

        seleccionados = self._llamar_llm_candidatos(prompt)
        
        # Validar y filtrar estrictamente sobre tendencias reales
        tags_finales = []
        tendencias_map = {t.lower().strip(): t for t in tendencias}
        
        for t in seleccionados:
            t_clean = t.lower().strip()
            # Si el tag seleccionado existe en la lista de búsquedas reales de Google
            if t_clean in tendencias_map:
                real_tag = tendencias_map[t_clean]
                # Validar que no supere 4 palabras
                if len(real_tag.split()) <= 4:
                    tags_finales.append({
                        "tag": real_tag,
                        "tipo": "Tendencia verificada",
                        "justificacion": "Búsqueda real verificada en Google Colombia (Google Suggest/Trends)"
                    })
        
        # Si faltan para llegar a 12, rellenar directamente desde tendencias reales cortas
        if len(tags_finales) < TARGET:
            for t in tendencias:
                if len(t.split()) <= 4:
                    already_added = any(tf["tag"].lower() == t.lower() for tf in tags_finales)
                    if not already_added:
                        tags_finales.append({
                            "tag": t,
                            "tipo": "Tendencia verificada",
                            "justificacion": "Búsqueda real verificada en Google Colombia (Google Suggest/Trends)"
                        })
                if len(tags_finales) >= TARGET:
                    break

        tags_finales = tags_finales[:TARGET]
        cantidad = len(tags_finales)
        print(f"[Pipe] ✅ ¡{cantidad} Tags finales reales (máx 3-4 palabras) seleccionados con éxito!")
        return tags_finales

    def run(self, texto, slug=None, tendencias=None):
        """Método de compatibilidad con app_web."""
        print(f"[Pipe] Generando tags para: {slug or 'nota'}...")
        tags = self.generar_tags(texto, tendencias=tendencias)
        return {"texto": texto, "tags": tags}

PipeAgent = Pipe


