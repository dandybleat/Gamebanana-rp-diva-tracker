import requests
import json
import os
import datetime
import re
import time

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
GAME_ID = "7886" 
API_URL = f"https://gamebanana.com/apiv11/Game/{GAME_ID}/Subfeed?_nPage=1&_sSort=updated"
DATA_FILE = "historial.json"

def cargar_historial():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def guardar_historial(datos):
    with open(DATA_FILE, "w") as f:
        json.dump(datos, f, indent=4)

def limpiar_texto(html):
    # Quita etiquetas HTML y limpia espacios extra de la descripción
    if not html: return ""
    clean = re.compile('<.*?>')
    texto = re.sub(clean, '', html)
    return (texto[:300] + '...') if len(texto) > 300 else texto

def enviar_discord(mod, tipo):
    nombre_mod = mod.get("_sName", "Mod")
    version = mod.get("_sVersion", "")
    
    # El título dirá "Publicado" o "Actualizado" según corresponda
    titulo_alerta = f"✨ ¡Nuevo Mod {tipo}! ✨" if tipo == "Publicado" else f"🔄 ¡Mod {tipo}! 🔄"
    
    mod_id = mod.get("_idRow")
    link = f"https://gamebanana.com/mods/{mod_id}"
    
    # Obtenemos la descripción real del mod
    descripcion_real = limpiar_texto(mod.get("_sDescription", "Sin descripción disponible."))
    
    # Extraemos la imagen manteniendo dimensiones y nombres originales
    imagenes = mod.get("_aPreviewMedia", {}).get("_aImages", [])
    imagen_url = ""
    if imagenes:
        base_url = imagenes[0].get("_sBaseUrl", "")
        archivo = imagenes[0].get("_sFile", "")
        imagen_url = f"{base_url}/{archivo}"

    color = 3066993 if tipo == "Publicado" else 15844367 # Verde para nuevo, Amarillo para update

    data = {
        "content": f"**{titulo_alerta}**",
        "embeds": [{
            "title": f"{nombre_mod} {'['+version+']' if version else ''}",
            "url": link,
            "description": descripcion_real,
            "color": color,
            "image": {"url": imagen_url},
            "footer": {"text": f"ID del mod: {mod_id}"},
            "timestamp": datetime.datetime.utcnow().isoformat()
        }]
    }
    requests.post(WEBHOOK_URL, json=data)
    time.sleep(2)  # <-- ESTE ES EL FRENO MAGICO

def main():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        mods = response.json().get("_aRecords", [])
    except Exception as e:
        print(f"Error: {e}")
        return

    historial = cargar_historial()
    nuevos_datos = historial.copy()
    hubo_cambios = False

    hoy = datetime.datetime.now()
    inicio_mes = datetime.datetime(hoy.year, hoy.month, 1).timestamp()

    for mod in mods:
        mod_id = str(mod.get("_idRow"))
        fecha_upd = mod.get("_tsDateUpdated")
        fecha_add = mod.get("_tsDateAdded")
        
        # Determinamos si es Publicado o Actualizado
        # Si la fecha de update es la misma que la de creación (o muy cercana), es nuevo.
        tipo_evento = "Publicado" if abs(fecha_upd - fecha_add) < 60 else "Actualizado"

        if mod_id not in historial or historial[mod_id] < fecha_upd:
            if not historial:
                if fecha_upd >= inicio_mes:
                    enviar_discord(mod, tipo_evento)
            else:
                enviar_discord(mod, tipo_evento)
                
            nuevos_datos[mod_id] = fecha_upd
            hubo_cambios = True

    if hubo_cambios:
        guardar_historial(nuevos_datos)

if __name__ == "__main__":
    main()
