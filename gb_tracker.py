import requests
import json
import os

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
GAME_ID = "7886" # Hatsune Miku: Project DIVA Mega Mix+
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

def enviar_discord(mod):
    titulo = mod.get("_sName", "Actualización detectada")
    version = mod.get("_sVersion", "")
    if version:
        titulo = f"{titulo} [{version}]"
        
    mod_id = mod.get("_idRow")
    link = f"https://gamebanana.com/mods/{mod_id}"
    
    # Extraemos la imagen directamente desde los servidores para asegurar que 
    # mantenga los nombres originales y su dimensión original intacta.
    imagenes = mod.get("_aPreviewMedia", {}).get("_aImages", [])
    imagen_url = ""
    if imagenes:
        base_url = imagenes[0].get("_sBaseUrl", "")
        archivo = imagenes[0].get("_sFile", "")
        imagen_url = f"{base_url}/{archivo}"

    data = {
        "embeds": [{
            "title": titulo,
            "url": link,
            "description": "¡El mod ha sido actualizado!",
            "color": 16763904,
            "image": {"url": imagen_url}
        }]
    }
    requests.post(WEBHOOK_URL, json=data)

def main():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        mods = response.json().get("_aRecords", [])
    except Exception as e:
        print(f"Error al conectar con la API: {e}")
        return

    historial = cargar_historial()
    nuevos_datos = historial.copy()
    hubo_cambios = False

    for mod in mods:
        mod_id = str(mod.get("_idRow"))
        fecha_actualizacion = mod.get("_tsDateUpdated")
        
        # Si el mod no está en el historial, o si la fecha es más nueva
        if mod_id not in historial or historial[mod_id] < fecha_actualizacion:
            # Solo enviamos alerta si el historial ya existía (para evitar spam la primera vez)
            if historial: 
                enviar_discord(mod)
            nuevos_datos[mod_id] = fecha_actualizacion
            hubo_cambios = True

    if hubo_cambios:
        guardar_historial(nuevos_datos)

if __name__ == "__main__":
    main()
