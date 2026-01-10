import requests
import random
import time
from faker import Faker

fake = Faker()
BASE_URL = "http://127.0.0.1:8000"

# CONFIGURACIÓN DEL ATAQUE
CANTIDAD_SKATERS = 20  # Vamos a crear 20 usuarios falsos
COORD_PARQUE = {"latitud": -33.4429, "longitud": -70.6341} # Parque Bustamante

def print_step(msg):
    print(f"\n🛹 --- {msg} ---")

def run_stress_test():
    ids_creados = []

    # 1. GENERACIÓN DE MASAS
    print_step(f"CREANDO {CANTIDAD_SKATERS} SKATERS FALSOS")
    for _ in range(CANTIDAD_SKATERS):
        payload = {
            "nickname": fake.user_name(),
            "email": fake.unique.email(),
            "stance": random.choice(["Regular", "Goofy"])
        }
        try:
            resp = requests.post(f"{BASE_URL}/usuarios", json=payload)
            if resp.status_code == 200:
                uid = resp.json()['id_usuario']
                ids_creados.append(uid)
                print(f"✅ Creado: {payload['nickname']} (ID: {uid})")
            else:
                print(f"❌ Error creando: {resp.text}")
        except Exception as e:
            print(f"Error de conexión: {e}")

    # 2. LA MIGRACIÓN (Mover todos al mismo punto)
    print_step("MOVIENDO A LA MULTITUD AL PARQUE BUSTAMANTE")
    for uid in ids_creados:
        requests.put(f"{BASE_URL}/usuarios/{uid}/ubicacion", json=COORD_PARQUE)
    print(f"📍 {len(ids_creados)} skaters posicionados en Lat: {COORD_PARQUE['latitud']}")

    # 3. EL ESTRÉS (Intentar crear carreras masivamente)
    print_step("INTENTANDO INICIAR CARRERAS AUTOMÁTICAS")
    
    # Simulamos que el sistema intenta armar carreras repetidamente
    carreras_creadas = 0
    for i in range(5): # Intentaremos 5 veces
        resp = requests.post(f"{BASE_URL}/carrera/iniciar?id_spot=1&min_participantes=5")
        
        if resp.status_code == 200:
            data = resp.json()
            carreras_creadas += 1
            print(f"🏆 CARRERA CREADA (Intento {i+1}): ID Evento {data['id_evento']} con {data['participantes']} participantes.")
        else:
            print(f"⚠️ Intento {i+1}: {resp.json().get('mensaje', 'Error desconocido')}")
        
        time.sleep(1) # Esperar 1 segundo entre intentos

    print_step("RESUMEN FINAL")
    print(f"Total Skaters Nuevos: {len(ids_creados)}")
    print(f"Carreras Organizadas: {carreras_creadas}")

if __name__ == "__main__":
    run_stress_test()