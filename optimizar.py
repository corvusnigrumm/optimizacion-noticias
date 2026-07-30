import os
import argparse
from datetime import datetime
from groq import Groq
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv

# Importar a nuestros 4 agentes
from agentes import Camilo, Valentina, Pipe, Adriana

# Cargar variables de entorno (ej. GROQ_API_KEY)
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    print("❌ ERROR CRÍTICO: No se encontró la variable GROQ_API_KEY.")
    print("Por favor, crea un archivo .env en la raíz del proyecto y agrega: GROQ_API_KEY=tu_clave_aqui")
    exit(1)

def extraer_texto(url):
    print(f"🌐 Extrayendo contenido de: {url}")
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraer título del artículo
        titulo = ""
        titulo_tag = soup.find('h1')
        if titulo_tag:
            titulo = titulo_tag.get_text().strip()
        
        # Estrategia mejorada para El Tiempo: buscar el contenedor del artículo
        # El Tiempo usa clases como 'article-content', 'c-detail__body', 'articulo-body'
        contenido = None
        selectores_articulo = [
            'div.c-detail__body',
            'div.article-content', 
            'div.articulo-body',
            'article',
            'div[class*="article"]',
            'div[class*="content-body"]',
        ]
        
        for selector in selectores_articulo:
            contenido = soup.select_one(selector)
            if contenido:
                break
        
        if contenido:
            elementos = contenido.find_all(['p', 'h2', 'h3', 'ul', 'ol'])
        else:
            # Fallback: todos los elementos relevantes
            elementos = soup.find_all(['p', 'h2', 'h3', 'ul', 'ol'])
        
        # Filtrar elementos que son ruido de UI (cookies, menús, banners, etc.)
        frases_basura = [
            'cookies', 'suscríbete', 'iniciar sesión', 'regístrese', 'regístrate',
            'verificar correo', 'boletines', 'newsletter', 'google news',
            'whatsapp', 'descarga la app', 'mantente informado', 'información confiable',
            'reproducción total o parcial', 'correo ha sido verificado',
            'cuenta en el tiempo', 'personaliza tu perfil', 'no ha sido verificado',
            'bandeja de entrada', 'correo no deseado', 'zona de usuario',
            'ya tienes una cuenta', 'datos de navegación', 'facebook y twitter',
            'conforme a los criterios', 'superintendencia de industria',
        ]
        
        textos_limpios = []
        for elem in elementos:
            texto = elem.get_text(separator=" ").strip()
            if len(texto) < 20: # Reducido a 20 para permitir subtitulos cortos
                continue
            texto_lower = texto.lower()
            if any(frase in texto_lower for frase in frases_basura):
                continue
            textos_limpios.append(texto)
        
        texto_crudo = "\n\n".join(textos_limpios)
        
        if titulo and titulo not in texto_crudo:
            texto_crudo = f"{titulo}\n\n{texto_crudo}"
        
        if len(texto_crudo) < 100:
            print("⚠️ Advertencia: Se extrajo muy poco texto. Verifica la URL.")
        
        return texto_crudo
    except Exception as e:
        print(f"❌ Error al extraer la URL: {e}")
        return None

def ejecutar_optimizacion(texto_crudo, slug):
    # Inicializar equipo
    from agentes import Camilo, Valentina, Pipe, Adriana
    camilo = Camilo()
    valentina = Valentina()
    pipe = Pipe()
    adriana = Adriana()

    # Ejecución en cadena
    print("\n🚀 Iniciando cadena de optimización SEO...")
    
    # Pipe: Extraer múltiples keywords temáticas automáticamente
    keywords = pipe.extraer_keywords_principales(texto_crudo)
    
    # Camilo: Rastrea tendencias para cada keyword y acumula sugerencias reales
    tendencias = camilo.investigar_tendencias(keywords)
    
    # Valentina: Aplica negrillas sin tocar el texto original
    texto_optimizado = valentina.optimizar_texto(texto_crudo)
    
    # Pipe: Genera 24 candidatos y selecciona los 12 de mayor volumen real (pytrends)
    tags = pipe.generar_tags(texto_crudo[:1000], tendencias, camilo=camilo)
    
    # Adriana: Ensambla el documento final
    markdown_final = adriana.ensamblar_markdown(texto_optimizado, tags)

    # Guardar en archivo
    fecha = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join("output", fecha, slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "optimizacion-seo.md")
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown_final)
    
    print(f"\n🎉 ¡Proceso finalizado! El archivo optimizado está en:\n{out_path}")
    return out_path

def main():
    parser = argparse.ArgumentParser(description='Equipo de Agentes SEO "La Redacción"')
    parser.add_argument('input_source', type=str, help='URL de la noticia o RUTA al archivo de texto a optimizar')
    parser.add_argument('--keyword', type=str, default='Colombia', help='Palabra clave principal para Google Trends')
    args = parser.parse_args()

    # 1. Extraer texto base (URL o Archivo)
    input_str = args.input_source
    if os.path.isfile(input_str):
        print(f"📄 Leyendo artículo desde el archivo local: {input_str}")
        with open(input_str, "r", encoding="utf-8") as f:
            texto_crudo = f.read()
        slug = os.path.basename(input_str).split('.')[0][:50]
    else:
        texto_crudo = extraer_texto(input_str)
        slug = input_str.split('/')[-1].split('.')[0][:50]
        
    if not texto_crudo:
        print("Finalizando ejecución por error de lectura o extracción.")
        return

    ejecutar_optimizacion(texto_crudo, slug)



if __name__ == "__main__":
    main()
