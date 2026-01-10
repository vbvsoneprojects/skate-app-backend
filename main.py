from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Intentamos leer la URL de Render, si no existe (como en tu PC), usa Neon o Local
DATABASE_URL = os.environ.get('DATABASE_URL', "postgres://neondb_owner:npg_6LqS3tjoUAFC@ep-broad-tree-ah3h6jb0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require")

def get_db():
    # Se conecta usando el link largo (DATABASE_URL)
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

# --- MODELOS ---
class UserAuth(BaseModel):
    username: str
    password: str

class SpotNuevo(BaseModel):
    nombre: str
    ubicacion: str
    tipo: str
    descripcion: str
    image: str
    lat: float
    lon: float

class Coordenadas(BaseModel):
    lat: float
    lon: float

class ComentarioNuevo(BaseModel):
    id_spot: int
    id_usuario: int
    texto: str

class PerfilFull(BaseModel):
    avatar: str
    edad: int
    comuna: str
    crew: str
    stance: str
    trayectoria: str

@app.get("/")
def read_root():
    return {"mensaje": "API Skate v8.0 - Real Time GPS 🛰️"}

# ==========================================
# 📡 ZONA GPS (LO NUEVO)
# ==========================================

# 1. Actualizar MI posición (El "Latido")
@app.put("/api/users/{id_usuario}/gps")
def update_gps(id_usuario: int, gps: Coordenadas):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE usuarios 
            SET ubicacion_actual = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            WHERE id_usuario = %s
        """, (gps.lon, gps.lat, id_usuario))
        return {"msg": "Ubicación actualizada"}
    except Exception as e:
        print(e)
        raise HTTPException(500, str(e))
    finally:
        conn.close()

# 2. Radar: Ver a OTROS skaters cerca
@app.get("/api/radar")
def get_skaters_nearby(lat: float, lon: float, user_id: int):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Trae usuarios a menos de 5km, EXCLUYENDOME a mí mismo
        query = """
            SELECT id_usuario, nickname, avatar,
                   ST_X(ubicacion_actual::geometry) as lon, 
                   ST_Y(ubicacion_actual::geometry) as lat
            FROM usuarios
            WHERE id_usuario != %s 
            AND ubicacion_actual IS NOT NULL
            AND ST_DWithin(
                ubicacion_actual::geography, 
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                5000
            );
        """
        cur.execute(query, (user_id, lon, lat))
        skaters = cur.fetchall()
        
        for s in skaters:
            if not s['avatar']: s['avatar'] = "https://images.unsplash.com/photo-1544005313-94ddf0286df2"
            
        return skaters
    finally:
        conn.close()

# ==========================================
# 🔐 AUTH, PERFIL Y SPOTS (TU CÓDIGO PROBADO)
# ==========================================

@app.post("/api/login/")
def login(user: UserAuth):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM usuarios WHERE nickname = %s AND password = %s", (user.username, user.password))
        u = cur.fetchone()
        if u:
            return {
                "id_usuario": u['id_usuario'],
                "username": u['nickname'],
                "level": "Pro" if (u['saldo_puntos'] or 0) > 1000 else "Novato",
                "avatar": u['avatar'] if u['avatar'] else "",
                
                # --- AGREGA ESTAS LÍNEAS NUEVAS ---
                "es_premium": u['es_premium'] if u['es_premium'] else False, 
                # ----------------------------------

                "edad": u['edad'] if u['edad'] else 0,
                "comuna": u['comuna'] if u['comuna'] else "",
                "crew": u['crew'] if u['crew'] else "",
                "stance": u['stance'] if u['stance'] else "Regular",
                "trayectoria": u['trayectoria'] if u['trayectoria'] else ""
            }
        else:
            raise HTTPException(401, "Credenciales incorrectas")
    finally:
        conn.close()

@app.post("/api/register/")
def register(user: UserAuth):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO usuarios (nickname, password) VALUES (%s, %s)", (user.username, user.password))
        return {"msg": "OK"}
    except:
        return {"msg": "Error"} # Simplificado
    finally:
        conn.close()

@app.put("/api/users/{id_usuario}/profile")
def update_profile(id_usuario: int, p: PerfilFull):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE usuarios 
            SET avatar=%s, edad=%s, comuna=%s, crew=%s, stance=%s, trayectoria=%s
            WHERE id_usuario=%s
        """, (p.avatar, p.edad, p.comuna, p.crew, p.stance, p.trayectoria, id_usuario))
        return {"msg": "Perfil actualizado"}
    finally:
        conn.close()

@app.get("/api/spots")
@app.get("/api/spots/")
def get_spots():
    print("--- SOLICITANDO SPOTS ---")
    conn = get_db()
    if not conn:
        return []
        
    try:
        cur = conn.cursor()
        
        # Pedimos 'image' (nombre real en BD)
        cur.execute("""
            SELECT 
                id_spot, 
                nombre, 
                descripcion, 
                tipo,
                ubicacion,
                image,   -- Aqui en SQL sí se usan guiones
                ST_X(coordenadas::geometry), 
                ST_Y(coordenadas::geometry)
            FROM spots 
            ORDER BY id_spot DESC
        """)
        rows = cur.fetchall()
        print(f"Spots encontrados en DB: {len(rows)}")

        spots_list = []
        for row in rows:
            # Aquí hacemos la traducción para Flutter
            spot_dict = {
                "id": row[0],
                "nombre": row[1],
                "descripcion": row[2],
                "tipo": row[3],
                "ubicacion": row[4],
                "imagen": row[5],  # <--- CORREGIDO: Usamos # para comentarios en Python
                "longitude": row[6],
                "latitude": row[7],
                "comments": []
            }

            # Parche para imágenes rotas
            if spot_dict["imagen"] and "blob:" in spot_dict["imagen"]:
                 spot_dict["imagen"] = "https://images.unsplash.com/photo-1520045864914-894836162391"

            # Buscar comentarios
            cur.execute("""
                SELECT c.texto, u.nickname, u.avatar
                FROM comentarios c
                JOIN usuarios u ON c.id_usuario = u.id_usuario
                WHERE c.id_spot = %s
                ORDER BY c.fecha DESC
            """, (row[0],))
            
            comentarios = cur.fetchall()
            for c in comentarios:
                avatar = c[2] if c[2] else "https://images.unsplash.com/photo-1544005313-94ddf0286df2"
                spot_dict["comments"].append({
                    "texto": c[0],
                    "user": c[1],
                    "avatar": avatar
                })
            
            spots_list.append(spot_dict)

        return spots_list
        
    except Exception as e:
        print(f"\n🛑 ERROR REAL: {e}\n")
        return []
    finally:
        conn.close()

@app.post("/api/spots/")
def create_spot(spot: SpotNuevo):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO spots (nombre, tipo, descripcion, ubicacion, image, coordenadas) 
            VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        """, (spot.nombre, spot.tipo, spot.descripcion, spot.ubicacion, spot.image, spot.lon, spot.lat))
        return {"msg": "Spot creado"}
    finally:
        conn.close()

@app.get("/api/users/") # Para S.K.A.T.E
def get_users(exclude_id: int = 0):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id_usuario, nickname, avatar, saldo_puntos FROM usuarios WHERE id_usuario != %s", (exclude_id,))
        return cur.fetchall()
    finally:
        conn.close()
# --- ESTO ES LO QUE TE FALTA ---

@app.post("/api/comments/")
def add_comment(comment: ComentarioNuevo): # Usamos tu clase 'ComentarioNuevo'
    conn = get_db()
    try:
        cur = conn.cursor()
        # Guardamos en la tabla 'comentarios' de la base de datos
        cur.execute(
            "INSERT INTO comentarios (id_spot, id_usuario, texto) VALUES (%s, %s, %s)",
            (comment.id_spot, comment.id_usuario, comment.texto)
        )
        return {"msg": "Comentario agregado"}
    except Exception as e:
        print(f"Error comentarios: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()
        # ==========================================
# 🥊 ZONA DE DUELOS (LO QUE FALTABA)
# ==========================================

# 1. Definimos qué datos llegan desde el iPhone
class DueloCreate(BaseModel):
    challenger_id: int
    opponent_id: int

# 2. Creamos la ruta para recibir el desafío
@app.post("/api/duelo/crear")
@app.post("/api/duelo/crear/") 
def crear_duelo(duelo: DueloCreate):
    conn = get_db()
    try:
        print(f"🔥 NUEVO DUELO: {duelo.challenger_id} vs {duelo.opponent_id}")
        cur = conn.cursor()
        
        # Guardamos el duelo en la base de datos
        # (Estado inicial: 'pendiente')
        cur.execute("""
            INSERT INTO duelos (challenger_id, opponent_id, estado, fecha_creacion)
            VALUES (%s, %s, 'pendiente', NOW())
            RETURNING id_duelo
        """, (duelo.challenger_id, duelo.opponent_id))
        
        new_id = cur.fetchone()[0]
        return {"msg": "Duelo enviado", "id_duelo": new_id}
        
    except Exception as e:
        print(f"Error creando duelo: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()
# --- MODELO PARA EL CASTIGO ---
class DueloPenalize(BaseModel):
    id_duelo: int
    id_perdedor: int

# --- FUNCION DE PENALIZACIÓN (S.K.A.T.E.) ---
@app.post("/api/duelo/penalizar")
@app.post("/api/duelo/penalizar/")
def penalizar_duelo(pen: DueloPenalize):
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # 1. Buscamos cómo va el duelo
        cur.execute("SELECT letras_actuales, challenger_id, opponent_id, ganador FROM duelos WHERE id_duelo = %s", (pen.id_duelo,))
        row = cur.fetchone()
        
        if not row:
            return {"letras_actuales": "", "game_over": False}
            
        # Si ya hay ganador, no hacemos nada
        if row[3]: 
            return {"letras_actuales": row[0], "game_over": True, "ganador": f"¡Ganó {row[3]}!"}

        raw_state = row[0] if row[0] else "|" 
        parts = raw_state.split("|")
        if len(parts) < 2: parts = ["", ""]
        
        c_letters = parts[0] # Retador
        o_letters = parts[1] # Rival
        
        # 2. Sumamos letra al perdedor
        is_challenger = (pen.id_perdedor == row[1])
        word = "SKATE"
        
        if is_challenger:
            if len(c_letters) < 5: c_letters += word[len(c_letters)]
        else:
            if len(o_letters) < 5: o_letters += word[len(o_letters)]
            
        # 3. Guardamos
        new_state = f"{c_letters}|{o_letters}"
        cur.execute("UPDATE duelos SET letras_actuales = %s WHERE id_duelo = %s", (new_state, pen.id_duelo))
        
        # 4. Revisamos si alguien perdió (Game Over)
        game_over = False
        winner_msg = ""
        
        # Variable para devolver al frontend (solo las letras de quien perdió esta ronda o el estado general)
        # En tu App muestras las dos, así que devolvemos el string completo "XXX|YYY" y tú lo separas, 
        # Ojo: Tu App espera 'letras_actuales' ya separadas o procesadas. 
        # Para simplificar, devolvemos el estado tal cual y tu App lo pinta.
        
        if len(c_letters) >= 5 or len(o_letters) >= 5:
            game_over = True
            winner_id = row[2] if is_challenger else row[1]
            cur.execute("SELECT nickname FROM usuarios WHERE id_usuario = %s", (winner_id,))
            w_name = cur.fetchone()[0]
            winner_msg = f"¡Ganó {w_name}!"
            cur.execute("UPDATE duelos SET estado = 'FINALIZADO', ganador = %s WHERE id_duelo = %s", (w_name, pen.id_duelo))

        return {
            "letras_actuales": new_state, # Devolvemos "SKA|S"
            "game_over": game_over, 
            "ganador": winner_msg
        }

    except Exception as e:
        print(f"Error penalizar: {e}")
        return {"letras_actuales": "", "game_over": False} 
    finally:
        conn.close()        