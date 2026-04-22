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
    # 1. Quitamos las etiquetas HTML
    clean = re.compile('<.*?>')
    texto = re.sub(clean, '', html)
    texto = texto.replace('&nbsp;', ' ').strip()
    
    # 2. Recolector de basura
    basura_ui = ["Manage Collections", "Files", "File Info", "Archived Files", "Comments", "Embed", "Credits", "THANKS FOR:"]
    for palabra in basura_ui:
        if palabra in texto:
            texto = texto.split(palabra)[0].strip()
            
    # 3. Límite de seguridad
    return (texto[:300] + '...') if len(texto) > 300 else texto

def enviar_discord(mod_resumen, tipo):
    mod_id = mod_resumen.get("_idRow")
    
    try:
        perfil_url = f"https://gamebanana.com/apiv11/Mod/{mod_id}/Profile"
        res = requests.get(perfil_url)
        res.raise_for_status()
        mod_completo = res.json()
    except Exception as e:
        print(f"Advertencia al leer mod {mod_id} (Quizá fue borrado u oculto): {e}")
        mod_completo = mod_resumen # Fallback seguro

    nombre_mod = mod_completo.get("_sName", "Mod")
    version = mod_completo.get("_sVersion", "")
    link = f"https://gamebanana.com/mods/{mod_id}"
    
    descripcion_real = ""
    
    if tipo == "Actualizado":
        try:
            updates_url = f"https://gamebanana.com/apiv11/Mod/{mod_id}/Updates"
            res_upd = requests.get(updates_url)
            if res_upd.status_code == 200:
                updates_data = res_upd.json()
                if isinstance(updates_data, list) and len(updates_data) > 0:
                    titulo_upd = updates_data[0].get("_sTitle", "").strip()
                    texto_upd = updates_data[0].get("_sText", "").strip()
                    
                    texto_limpio = limpiar_texto(texto_upd)
                    
                    if titulo_upd and texto_limpio:
                        descripcion_real = f"**{titulo_upd}**\n{texto_limpio}"
                    elif titulo_upd:
                        descripcion_real = f"**{titulo_upd}**"
                    elif texto_limpio:
                        descripcion_real = texto_limpio
        except Exception:
            pass
            
        if not descripcion_real:
            descripcion_real = "*El autor actualizó los archivos pero no dejó notas del parche.*"
    else:
        descripcion_raw = mod_completo.get("_sDescription") or mod_completo.get("_sText", "")
        descripcion_real = limpiar_texto(descripcion_raw)
        if not descripcion_real:
            descripcion_real = "*Sin descripción disponible en la portada.*"

    # --- CORRECCIÓN DEL FALLO DE FECHAS AQUÍ ---
    fecha_upd = mod_completo.get("_tsDateUpdated")
    if not fecha_upd:  
        fecha_upd = mod_completo.get("_tsDateAdded")
    if not fecha_upd:  
        fecha_upd = int(time.time()) # Usa el time global correctamente
        
    timestamp_iso = datetime.datetime.fromtimestamp(fecha_upd, tz=datetime.timezone.utc).isoformat()

    titulo_alerta = f"✨ ¡Nuevo Mod {tipo}! ✨" if tipo == "Publicado" else f"🔄 ¡Mod {tipo}! 🔄"
    color = 3066993 if tipo == "Publicado" else 15844367

    imagenes = mod_completo.get("_aPreviewMedia", {}).get("_aImages", [])
    imagen_url = ""
    if imagenes:
        base_url = imagenes[0].get("_sBaseUrl", "")
        archivo = imagenes[0].get("_sFile", "")
        imagen_url = f"{base_url}/{archivo}"

    data = {
        "content": f"**{titulo_alerta}**",
        "embeds": [{
            "title": f"{nombre_mod} {'['+version+']' if version else ''}",
            "url": link,
            "description": descripcion_real,
            "color": color,
            "image": {"url": imagen_url},
            "footer": {"text": f"ID: {mod_id} • Actualización real"},
            "timestamp": timestamp_iso 
        }]
    }
    
    requests.post(WEBHOOK_URL, json=data)
    time.sleep(2) # El freno mágico ahora funciona bien siempre

def main():
    mods = []
    for page in range(1, 6):
        url = f"https://gamebanana.com/apiv11/Game/{GAME_ID}/Subfeed?_nPage={page}&_nPerpage=50&_sSort=updated"
        try:
            response = requests.get(url)
            response.raise_for_status()
            records = response.json().get("_aRecords", [])
            if not records: break
            mods.extend(records)
        except Exception as e:
            print(f"Error en página {page}: {e}")
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
        
        # Red de seguridad para el cálculo de eventos
        if not fecha_upd or not fecha_add:
            tipo_evento = "Actualizado"
            fecha_upd = fecha_upd or int(time.time())
        else:
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
