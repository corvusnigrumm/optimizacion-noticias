"""
optimizar_word.py — Orquestador principal (versión Word)

Toma un artículo (en texto plano o URL) y genera:
  1. Un .docx con negrillas inteligentes y H1/H2 formateados
  2. Busquedas activas de Google Colombia para enriquecer las negrillas

Uso:
    python optimizar_word.py articulo_papel_aluminio.txt
    python optimizar_word.py https://www.ejemplo.com/noticia
    python optimizar_word.py articulo.txt --sin-busquedas
"""
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Verificar API key
if not os.getenv("GROQ_API_KEY"):
    print("❌ ERROR: No se encontró GROQ_API_KEY en el .env")
    sys.exit(1)

from agentes.valentina_word import ValentinaWord
from agentes.buscador_google import obtener_busquedas_activas, obtener_keywords_articulo


def extraer_texto_url(url):
    """Extrae el texto de una URL usando BeautifulSoup."""
    try:
        import requests
        from bs4 import BeautifulSoup
        print(f"🌐 Extrayendo contenido de: {url}")
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extraer título
        titulo = ""
        titulo_tag = soup.find("h1")
        if titulo_tag:
            titulo = titulo_tag.get_text().strip()

        # Buscar contenedor principal del artículo
        contenido = None
        for selector in ["div.c-detail__body", "div.article-content", "article", "div[class*='article']"]:
            contenido = soup.select_one(selector)
            if contenido:
                break

        elementos = contenido.find_all(["p", "h2", "h3"]) if contenido else soup.find_all(["p", "h2", "h3"])
        basura = ["cookies", "suscríbete", "iniciar sesión", "newsletter", "whatsapp", "descarga la app"]
        textos = []
        for elem in elementos:
            t = elem.get_text(separator=" ").strip()
            if len(t) < 20:
                continue
            if any(b in t.lower() for b in basura):
                continue
            textos.append(t)

        texto = "\n\n".join(textos)
        if titulo and titulo not in texto:
            texto = f"{titulo}\n\n{texto}"
        return texto
    except Exception as e:
        print(f"❌ Error extrayendo URL: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Generador de Word con negrillas inteligentes y búsquedas activas de Google'
    )
    parser.add_argument(
        "input_source",
        type=str,
        help="Ruta al archivo de texto o URL del artículo"
    )
    parser.add_argument(
        "--sin-busquedas",
        action="store_true",
        help="Omite la consulta a Google Suggest (más rápido)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Ruta de salida del .docx (por defecto: output/FECHA/SLUG/articulo.docx)"
    )
    args = parser.parse_args()

    # 1. Leer el artículo
    input_str = args.input_source
    if os.path.isfile(input_str):
        print(f"📄 Leyendo artículo desde: {input_str}")
        with open(input_str, "r", encoding="utf-8") as f:
            texto_crudo = f.read()
        slug = os.path.basename(input_str).split(".")[0][:50]
    else:
        texto_crudo = extraer_texto_url(input_str)
        slug = input_str.split("/")[-1].split(".")[0][:50] or "articulo"

    if not texto_crudo or len(texto_crudo) < 50:
        print("❌ No se pudo obtener el texto del artículo. Revisa la ruta o la URL.")
        sys.exit(1)

    # 2. Búsquedas activas de Google (enriquecimiento)
    busquedas_activas = []
    if not args.sin_busquedas:
        keywords_semilla = obtener_keywords_articulo(texto_crudo, n=3)
        print(f"🎯 Keywords semilla extraídas: {keywords_semilla}")
        for kw in keywords_semilla:
            nuevas = obtener_busquedas_activas(kw, n_sugerencias=15)
            busquedas_activas.extend(nuevas)
        # Deduplicar
        vistas = set()
        busquedas_unicas = []
        for b in busquedas_activas:
            if b.lower() not in vistas:
                vistas.add(b.lower())
                busquedas_unicas.append(b)
        busquedas_activas = busquedas_unicas[:40]
        print(f"🔎 Total búsquedas activas para enriquecimiento: {len(busquedas_activas)}")
    else:
        print("⏩ Modo sin búsquedas activado. Saltando Google Suggest.")

    # 3. Definir ruta de salida
    if args.output:
        ruta_docx = args.output
    else:
        fecha = datetime.now().strftime("%Y-%m-%d")
        out_dir = os.path.join("output", fecha, slug)
        os.makedirs(out_dir, exist_ok=True)
        ruta_docx = os.path.join(out_dir, "articulo_optimizado.docx")

    # 4. Generar Tags SEO con Pipe
    print("\n🏷️  Generando tags SEO...")
    from agentes import Pipe
    pipe_agent = Pipe()
    tags_seo = pipe_agent.generar_tags(texto_crudo[:1000], busquedas_activas)

    # 5. Ejecutar ValentinaWord
    print("\n🚀 Iniciando generación del documento Word con negrillas editoriales...\n")
    agente = ValentinaWord()
    resultado = agente.generar_docx(
        texto_crudo=texto_crudo,
        ruta_salida=ruta_docx,
        busquedas_activas=busquedas_activas,
        tags_seo=tags_seo
    )

    if resultado:
        print(f"\n🎉 ¡Listo! Documento Word generado en:\n{os.path.abspath(resultado)}")
    else:
        print("\n❌ Error generando el documento Word.")
        sys.exit(1)


if __name__ == "__main__":
    main()
