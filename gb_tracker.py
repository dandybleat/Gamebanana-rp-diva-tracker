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
    texto = texto.replace('&nbsp;', ' ').strip()
    
    basura_ui = ["Manage Collections", "Files", "File Info", "Archived Files", "Comments", "Embed", "Credits", "THANKS FOR:"]
    for palabra in basura_ui:
        if palabra in texto:
            texto = texto.split(palabra)[0].strip()
            
    return (texto[:300] + '...') if len(texto) > 300 else texto

def enviar_discord(mod_resumen, tipo):
    mod_id = mod_resumen.get("_idRow")
    
    nombre_mod = mod_resumen.get("_sName", "Mod")
    version = mod_resumen.get("_sVersion", "")
    link = f"https://gamebanana.com/mods/{mod_id}"
    
    # 1. Asignamos la fecha exacta y la formateamos a DD/MM/AAAA HH:MM (24 hrs)
    if tipo == "Publicado":
        ts_fecha = mod_resumen.get("_tsDateAdded") or mod_resumen.get("_tsDateUpdated")
    else:
        ts_fecha = mod_resumen.get("_tsDateUpdated") or mod_resumen.get("_tsDateAdded")
        
    if not ts_fecha:
        ts_fecha = int(time.time())
        
    # Magia de Python: Convertimos el número a tu formato exacto
    fecha_formateada = datetime.datetime.fromtimestamp(ts_fecha).strftime('%d/%m/%Y %H:%M')

    try:
        perfil_url = f"https://gamebanana.com/apiv11/Mod/{mod_id}/Profile"
        res = requests.get(perfil_url)
        res.raise_for_status()
        mod_completo = res.json()
    except Exception as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            print(f"Mod {mod_id} fantasma (404). Se omitirá hasta la próxima hora.")
            return False 
        mod_completo = {}

    descripcion_real = ""
    
    if tipo == "Actualizado":
        try:
            updates_url = f"https://gamebanana.com/apiv11/Mod/{mod_id}/Updates"
            res_upd = requests.get(updates_url)
            if res_upd.status_code == 200:
                updates_data = res_upd.json()
                
                if isinstance(updates_data, dict):
                    lista_upd = updates_data.get("_aRecords", [])
                else:
                    lista_upd = updates_data
                    
                if isinstance(lista_upd, list) and len(lista_upd) > 0:
                    upd = lista_upd[0]
                    titulo_upd = upd.get("_sTitle", "") or upd.get("_sName", "")
                    texto_upd = upd.get("_sText", "") or upd.get("_sDescription", "")
                    
                    titulo_upd = titulo_upd.strip()
                    texto_upd = texto_upd.strip()
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
        descripcion_raw = mod_completo.get("_sDescription") or mod_completo.get("_sText") or mod_resumen.get("_sDescription", "")
        descripcion_real = limpiar_texto(descripcion_raw)
        if not descripcion_real:
            descripcion_real = "*Sin descripción disponible en la portada.*"

    titulo_alerta = f"✨ ¡Nuevo Mod {tipo}! | ¡New Mod Relased! ✨" if tipo == "Publicado" else f"🔄 ¡Mod {tipo}! | ¡Mod Updated! 🔄"
    color = 3066993 if tipo == "Publicado" else 15844367

    imagenes = mod_resumen.get("_aPreviewMedia", {}).get("_aImages", [])
    if not imagenes: 
        imagenes = mod_completo.get("_aPreviewMedia", {}).get("_aImages", [])

    imagen_url = ""
    if imagenes:
        base_url = imagenes[0].get("_sBaseUrl", "")
        archivo = imagenes[0].get("_sFile", "")
        if base_url and archivo:
            imagen_url = f"{base_url}/{archivo}"

    # 2. Armamos el mensaje (Hemos quitado "timestamp" y pusimos la fecha en el "footer")
    data = {
        "content": f"**{titulo_alerta}**",
        "embeds": [{
            "title": f"{nombre_mod} {'['+version+']' if version else ''}",
            "url": link,
            "description": descripcion_real,
            "color": color,
            "image": {"url": imagen_url},
            "footer": {"text": f"ID: {mod_id} • Date: {fecha_formateada}"}
        }]
    }
    
    requests.post(WEBHOOK_URL, json=data)
    time.sleep(2)
    return True

def main():
    mods = []
    for page in range(1, 6):
                url = f"https://gamebanana.com/apiv11/Mod/Index?_aFilters[Generic_Game]={GAME_ID}&_sSort=updated&_nPage={page}&_nPerpage=50"

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
        
        if not fecha_upd or not fecha_add:
            tipo_evento = "Actualizado"
            fecha_upd = fecha_upd or int(time.time())
        else:
            tipo_evento = "Publicado" if abs(fecha_upd - fecha_add) < 60 else "Actualizado"

        if mod_id not in historial or historial[mod_id] < fecha_upd:
            enviado = True 
            
            if not historial:
                if fecha_upd >= inicio_mes:
                    enviado = enviar_discord(mod, tipo_evento)
            else:
                enviado = enviar_discord(mod, tipo_evento)
                
            if enviado is not False:
                nuevos_datos[mod_id] = fecha_upd
                hubo_cambios = True

    if hubo_cambios:
        guardar_historial(nuevos_datos)

if __name__ == "__main__":
    main()
