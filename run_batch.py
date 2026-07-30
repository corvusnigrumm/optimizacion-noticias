import subprocess
import os

urls_keywords = [
    ("https://www.eltiempo.com/economia/sectores/empresarios-de-la-andi-fenalco-y-consejo-gremial-piden-proteger-resultados-electorales-tras-palabras-del-presidente-gustavo-petro-de-desconocerlos-3561045", "elecciones"),
    ("https://www.eltiempo.com/justicia/delitos/captura-de-jurado-de-votacion-en-hato-corozal-casanare-el-hombre-era-requerido-por-el-presunto-delito-de-acto-sexual-con-menor-de-14-anos-3561126", "casanare"),
    ("https://www.eltiempo.com/cultura/gente/quien-es-callum-turner-el-actor-que-conquisto-a-dua-lipa-y-se-caso-con-ella-el-britanico-hizo-su-debut-en-la-pantalla-grande-en-el-ano-3561127", "dua lipa"),
    ("https://www.eltiempo.com/economia/finanzas-personales/comerciantes-proyectan-crecimiento-de-hasta-25-en-ventas-por-el-dia-del-padre-fenalco-espera-una-fuerte-tendencia-el-fin-de-semana-del-14-de-junio-3561086", "dia del padre"),
    ("https://www.eltiempo.com/cultura/gente/proximo-eclipse-solar-total-ya-tiene-fecha-durara-siete-minutos-y-podra-verse-en-colombia-3561570", "eclipse solar"),
    ("https://www.eltiempo.com/cultura/gente/cardio-durante-la-menopausia-los-expertos-aclaran-si-es-danino-hacer-ejercicio-aerobico-en-esta-etapa-de-la-vida-y-cuales-son-sus-beneficios-reales-3561556", "menopausia"),
    ("https://www.eltiempo.com/vida/mascotas/las-razas-de-gatos-mas-exclusivas-y-caras-del-mundo-en-2026-precios-caracteristicas-y-advertencias-que-debe-conocer-antes-de-comprar-3561604", "gatos"),
    ("https://www.eltiempo.com/politica/partidos-politicos/nuevo-liberalismo-anuncia-que-no-respaldara-a-ivan-cepeda-ni-a-abelardo-de-la-espriella-en-la-segunda-vuelta-presidencial-respeta-la-libertad-3561684", "nuevo liberalismo"),
    ("https://www.eltiempo.com/deportes/futbol-internacional/calendario-de-la-seleccion-colombia-en-el-mundial-2026-conozca-los-dias-exactos-estadios-rivales-y-horarios-oficiales-de-los-partidos-3561748", "seleccion colombia"),
    ("https://www.eltiempo.com/cultura/gente/este-es-el-error-mas-comun-al-lavar-frutas-en-casa-que-aumenta-el-riesgo-de-contaminacion-sin-que-usted-lo-sepa-3561772", "lavar frutas"),
    ("https://www.eltiempo.com/cultura/gente/significado-de-que-una-arana-aparezca-en-un-rincon-de-su-casa-segun-el-feng-shui-3561816", "feng shui"),
    ("https://www.eltiempo.com/cultura/gente/cual-es-la-diferencia-entre-sal-rosada-sal-marina-sal-refinada-y-cual-elegir-3561318", "sal rosada"),
]

os.environ["PYTHONIOENCODING"] = "utf-8"

for url, kw in urls_keywords:
    print(f"\n====================================")
    print(f"Procesando con keyword: '{kw}'")
    print(f"URL: {url}")
    subprocess.run(["python", "optimizar.py", url, "--keyword", kw])
