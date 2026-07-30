import subprocess
import os

urls = [
    "https://www.eltiempo.com/bogota/cortes-de-agua-en-bogota-y-soacha-consulte-los-barrios-afectados-del-16-al-18-de-junio-3564620",
    "https://www.eltiempo.com/cultura/gente/tortazo-latinoamericano-en-bogota-musica-gratis-de-colombia-y-argentina-al-aire-libre-3564593",
    "https://www.eltiempo.com/bogota/video-conductor-choco-contra-poste-en-bogota-se-bajo-a-revisar-danos-y-huyo-en-taxi-antes-de-llegada-de-autoridades-revelan-reporte-del-accidente-3564486?mrfhud=true",
    "https://www.eltiempo.com/deportes/futbol-internacional/el-zenit-de-rusia-le-mostro-la-puerta-de-salida-a-jhon-duran-tras-un-adios-lleno-de-misterio-su-proxima-parada-una-gran-incognita-3564604?mrfhud=true",
    "https://www.eltiempo.com/deportes/futbol-internacional/a-gianni-infantino-le-cantaron-la-tabla-se-colo-en-el-vestuario-de-iran-y-el-dt-le-recrimino-por-la-represion-que-vive-su-equipo-en-el-mundial-3564496?mrfhud=true",
    "https://www.eltiempo.com/cultura/gente/adios-al-polvo-rebelde-el-metodo-con-papel-aluminio-en-la-escoba-que-gana-popularidad-en-los-hogares-3564570?mrfhud=true"
]

os.environ["PYTHONIOENCODING"] = "utf-8"

for url in urls:
    print(f"\n====================================")
    print(f"URL: {url}")
    subprocess.run(["python", "optimizar.py", url])
