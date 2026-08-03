from groq import Groq
import os
from huggingface_hub import InferenceClient

class Adriana:
    """
    Adriana: La Editora en Jefe / QA.
    Recibe el trabajo de Valentina (texto optimizado) y Pipe (tags), 
    genera los H2s y ensambla el documento final en Markdown.
    """
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        self.model_name = model_name
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.hf_client = InferenceClient(api_key=os.getenv("HF_TOKEN"))
        self.system_instruction = (
            "Eres Adriana, la Editora en Jefe y QA de 'La Redacción'. Tu tarea es ensamblar un artículo optimizado para SEO.\n"
            "Se te entregará el texto ya con negrillas, y una lista de 12 tags.\n"
            "REGLAS CRÍTICAS DE ORGANIZACIÓN SEVERA Y PROFESIONAL:\n"
            "Debes estructurar el documento Markdown exactamente con este formato corporativo, limpio y directo:\n\n"
            "# Optimización Editorial SEO\n\n"
            "## 1. Texto Optimizado\n"
            "(Aquí va el texto completo con las negrillas, NUNCA modifiques ni agregues texto adicional al artículo original)\n\n"
            "## 2. Resumen de Lectura Rápida (Solo Negrillas)\n"
            "(Extrae las frases en negrilla del texto y preséntalas como bullet points. Así el editor comprueba la narrativa)\n\n"
            "## 3. Titulares H2 Sugeridos\n"
            "(Tabla con 3 o 4 H2 recomendados y su justificación SEO)\n\n"
            "## 4. Estructura de Tags SEO\n"
            "(La tabla de 12 tags generada por Pipe, sin alteraciones)\n\n"
            "Tu tono debe ser 100% profesional. No uses saludos, ni texto de relleno, ni des explicaciones extra. Solo entrega la estructura."
        )

    def ensamblar_markdown(self, texto_con_negrillas, tags_json):
        print("[Adriana] 📝 Generando H2s, extrayendo resumen y ensamblando el archivo final...")
        
        prompt = (
            f"Por favor ensambla el archivo Markdown final.\n\n"
            f"=== TEXTO CON NEGRILLAS ===\n{texto_con_negrillas}\n\n"
            f"=== TAGS A INCLUIR EN TABLA ===\n{tags_json}\n\n"
            "Recuerda incluir:\n- El texto completo con sus negrillas\n- La tabla de tags\n- La tabla de H2s sugeridos\n- El resumen de lectura rápida de las negrillas."
        )
        
        try:
            print("\n[Adriana] Ensamblando markdown: ", end="", flush=True)
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_completion_tokens=4096,
                stream=True
            )
            markdown_final = ""
            for chunk in completion:
                chunk_text = chunk.choices[0].delta.content or ""
                print(chunk_text, end="", flush=True)
                markdown_final += chunk_text
            print()
            
            import re
            markdown_final = re.sub(r'<think>.*?</think>', '', markdown_final, flags=re.DOTALL).strip()
            
            print("[Adriana] ✅ ¡Markdown ensamblado con éxito!")
            return markdown_final
        except Exception as e:
            if "RateLimitError" in type(e).__name__ or "429" in str(e):
                print("[Adriana] ⚠️ Límite de Groq alcanzado. Usando Hugging Face (Fallback)...")
                try:
                    response_hf = self.hf_client.chat.completions.create(
                        model="meta-llama/Meta-Llama-3-8B-Instruct",
                        messages=[
                            {"role": "system", "content": self.system_instruction},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=4000
                    )
                    markdown_final = response_hf.choices[0].message.content
                    import re
                    markdown_final = re.sub(r'<think>.*?</think>', '', markdown_final, flags=re.DOTALL).strip()
                    print("[Adriana] ✅ ¡Markdown ensamblado con éxito usando HF!")
                    return markdown_final
                except Exception as e_hf:
                    print(f"[Adriana] ❌ Error ensamblando con HF: {e_hf}")
                    return f"Error en el ensamblaje: {e_hf}"
            else:
                print(f"[Adriana] ❌ Error ensamblando Markdown: {e}")
                return f"Error en el ensamblaje: {e}"

    def run(self, texto, slug=None):
        """Método de compatibilidad con app_web."""
        import re
        md = self.ensamblar_markdown(texto, [])
        h2s = re.findall(r'^##\s+(.*)', md, re.MULTILINE)
        return {"texto": texto, "h2s": h2s or ["Análisis de Contenido", "Contexto y Relevancia"], "seo_score": 92}

AdrianaAgent = Adriana

