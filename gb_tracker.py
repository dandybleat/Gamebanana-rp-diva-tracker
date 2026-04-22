import requests
import json
import os
import datetime

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
GAME_ID = "8501" 
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
    
    # Extraemos la imagen manteniendo la ruta y archivo en su dimensión original
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

    # Calculamos el timestamp exacto del día 1 del mes actual
    hoy = datetime.datetime.now()
    inicio_mes = datetime.datetime(hoy.year, hoy.month, 1).timestamp()

    for mod in mods:
        mod_id = str(mod.get("_idRow"))
        fecha_actualizacion = mod.get("_tsDateUpdated")
        
        # Si detectamos algo que no está en la memoria o es más nuevo...
        if mod_id not in historial or historial[mod_id] < fecha_actualizacion:
            
            # Si el historial está vacío (es nuestra primera ejecución de calibración)
            if not historial:
                # Solo disparamos a Discord si se actualizó durante este mes
                if fecha_actualizacion >= inicio_mes:
                    enviar_discord(mod)
            # Si ya hay historial (funcionamiento normal en las próximas horas)
            else:
                enviar_discord(mod)
                
            nuevos_datos[mod_id] = fecha_actualizacion
            hubo_cambios = True

    if hubo_cambios:
        guardar_historial(nuevos_datos)

if __name__ == "__main__":
    main()
