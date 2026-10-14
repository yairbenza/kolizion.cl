"""Sincroniza el catalogo del marketplace (este proyecto) hacia el proyecto
vidriera/preview (../app-moda-preview), pedido del usuario (2026-09-11):
mantener 2 proyectos con el mismo catalogo sin duplicar el trabajo de
clasificacion cada vez que se agrega una tienda o producto nuevo.

Copia SOLO los 3 archivos de datos del catalogo (nunca datos de uso, como
favoritos/clics/historial -- esos son propios de cada proyecto):
  - data/catalog.json        (el catalogo real, generado por construir_catalogo_real.py)
  - data/envios_tiendas.json (politica de envio por tienda)
  - data/tiendas.json        (registro de tiendas para "Llegan rapido a ti")

No copia imagenes: todas las fotos del catalogo son URLs externas (CDN de
cada tienda), no archivos locales -- no hay nada que sincronizar ahi.

Uso: correr desde app-moda-ia despues de agregar/actualizar una tienda:
    python sync_catalogo_preview.py
"""

import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PREVIEW_DIR = BASE_DIR.parent / "app-moda-preview"

ARCHIVOS_A_SINCRONIZAR = [
    "data/catalog.json",
    "data/envios_tiendas.json",
    "data/tiendas.json",
]


def main():
    if not PREVIEW_DIR.exists():
        print(f"No encontre el proyecto preview en: {PREVIEW_DIR}")
        print("Revisa que 'app-moda-preview' este al lado de 'app-moda-ia'.")
        return

    for rel_path in ARCHIVOS_A_SINCRONIZAR:
        origen = BASE_DIR / rel_path
        destino = PREVIEW_DIR / rel_path
        if not origen.exists():
            print(f"[saltado] {rel_path} no existe en el proyecto principal")
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, destino)
        print(f"[ok] {rel_path} copiado -> preview")

    print("\nListo. Si ya tienes el proyecto preview corriendo, reinicialo para que cargue los datos nuevos.")
    print("Si ya esta desplegado en Render, hay que subir estos cambios y hacer Manual Deploy alla tambien.")


if __name__ == "__main__":
    main()
