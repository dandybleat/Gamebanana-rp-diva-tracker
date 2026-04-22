import requests
import json
import os
import datetime
import re
import time

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
GAME_ID = "7886" 
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
    if not html: return ""
    clean = re.compile('<.*?>')
    texto = re.sub(clean, '', html)
    return (texto[:300] + '...') if len(texto) > 300 else texto

def enviar_discord(mod, tipo):
    nombre_mod = mod.get("_sName", "Mod")
    version = mod.get("_sVersion", "")
    
    titulo_alerta = f"✨ ¡Nuevo Mod {tipo}! ✨" if tipo == "Publicado" else f"🔄 ¡Mod {tipo}! 🔄"
    
    mod_id = mod.get("_idRow")
    link = f"https://gamebanana.com/mods/{mod_id}"
    
    descripcion_real = limpiar_texto(mod.get("_sDescription", "Sin descripción disponible."))
    
    imagenes = mod.get("_aPreviewMedia", {}).get("_aImages", [])
    imagen_url = ""
    if imagenes:
        base_url = imagenes[0].get("_sBaseUrl", "")
        archivo = imagenes[0].get("_sFile", "")
        imagen_url = f"{base_url}/{archivo}"

    color = 3066993 if tipo == "Publicado" else 15844367

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
    time.sleep(2) # Freno para que Discord no nos bloquee

def main():
    mods = []
    
    # Hacemos que el bot revise las primeras 5 páginas (50 mods por página = 250 mods)
    for page in range(1, 6):
        url = f"https://gamebanana.com/apiv11/Game/{GAME_ID}/Subfeed?_nPage={page}&_nPerpage=50&_sSort=updated"
        try:
            response = requests.get(url)
            response.raise_for_status()
            records = response.json().get("_aRecords", [])
            
            if not records:
                break # Si llegamos a una página vacía, dejamos de buscar
                
            mods.extend(records)
        except Exception as e:
            print(f"Error al conectar con la API en la página {page}: {e}")
            break

    historial = cargar_historial()
    nuevos_datos = historial.copy()
    hubo_cambios = False

    hoy = datetime.datetime.now()
    inicio_mes = datetime.datetime(hoy.year, hoy.month, 1).timestamp()

    for mod in mods:
        mod_id = str(mod.get("_idRow"))
        fecha_upd = mod.get("_tsDateUpdated")
        fecha_add = mod.get("_tsDateAdded")
        
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
