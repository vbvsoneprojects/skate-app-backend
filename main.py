from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Configuración de Base de Datos
DATABASE_URL = os.environ.get('DATABASE_URL', "postgres://neondb_owner:npg_6LqS3tjoUAFC@ep-broad-tree-ah3h6jb0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require")

# 2. DEFINICIÓN DE MODELOS (Lo que faltaba)
class UserAuth(BaseModel):
    username: str
    password: str

class Coordenadas(BaseModel):
    lat: float
    lon: float

class PerfilFull(BaseModel):
    avatar: str = ""
    edad: int = 0
    comuna: str = ""
    crew: str = ""
    stance: str = "Regular"
    trayectoria: str = ""

class SpotNuevo(BaseModel):
    nombre: str
    tipo: str
    descripcion: str
    ubicacion: str
    image: str
    lat: float
    lon: float

class ComentarioNuevo(BaseModel):
    id_spot: int
    id_usuario: int
    texto: str

class DueloCreate(BaseModel):
    challenger_id: int
    opponent_id: int

class DueloPenalize(BaseModel):
    id_duelo: int
    id_perdedor: int

# 3. FUNCIONES DE CONEXIÓN
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Esto borrará las ubicaciones antiguas para que todos deban marcar su GPS de nuevo
    cur.execute("UPDATE usuarios SET ubicacion_actual = NULL;")
    script_sql = """
    CREATE EXTENSION IF NOT EXISTS postgis;

    CREATE TABLE IF NOT EXISTS public.usuarios (
        id_usuario serial4 NOT NULL,
        nickname varchar(50) NOT NULL,
        "password" text DEFAULT '1234',
        email varchar(100) DEFAULT 'skater@mail.com',
        avatar text,
        edad int4,
        comuna varchar(100),
        crew varchar(100),
        stance varchar(20) DEFAULT 'Regular',
        trayectoria varchar(50),
        saldo_puntos int4 DEFAULT 0,
        ubicacion_actual geometry(point, 4326),
        es_premium bool DEFAULT false,
        CONSTRAINT usuarios_nickname_key UNIQUE (nickname),
        CONSTRAINT usuarios_pkey PRIMARY KEY (id_usuario)
    );

    CREATE TABLE IF NOT EXISTS public.spots (
        id_spot serial4 NOT NULL,
        nombre varchar(100),
        descripcion text,
        tipo varchar(50),
        ubicacion varchar(100),
        image text,
        coordenadas geometry(point, 4326),
        CONSTRAINT spots_pkey PRIMARY KEY (id_spot)
    );

    CREATE TABLE IF NOT EXISTS public.comentarios (
        id_comentario serial4 NOT NULL,
        id_spot int4,
        id_usuario int4,
        texto text,
        fecha timestamp DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT comentarios_pkey PRIMARY KEY (id_comentario)
    );

    CREATE TABLE IF NOT EXISTS public.duelos (
        id_duelo serial4 NOT NULL,
        challenger_id int4,
        opponent_id int4,
        letras_actuales varchar(20) DEFAULT '|',
        estado varchar(20) DEFAULT 'pendiente',
        ganador varchar(100),
        fecha_creacion timestamp DEFAULT NOW(),
        CONSTRAINT duelos_pkey PRIMARY KEY (id_duelo)
    );
    UPDATE usuarios SET es_premium = true;
    """
    cur.execute(script_sql)
    conn.commit()
    cur.close()
    conn.close()

# Iniciar tablas al arrancar
init_db()

@app.get("/")
def read_root():
    return {"mensaje": "API Skate v8.0 - Live en Render 🚀"}

# ==========================================
# 📡 ZONA GPS (LO NUEVO)
# ==========================================

# 1. Actualizar MI posición (El "Latido")
# 1. Actualizar MI posición y marcar actividad reciente
@app.put("/api/users/{id_usuario}/gps")
def update_gps(id_usuario: int, gps: Coordenadas):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE usuarios 
            SET ubicacion_actual = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                ultima_conexion = NOW()  -- 👈 Esto elimina los "fantasmas"
            WHERE id_usuario = %s
        """, (gps.lon, gps.lat, id_usuario))
        return {"msg": "Ubicación actualizada"}
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        conn.close()

# 2. Radar de 80km con filtros de privacidad y tiempo
@app.get("/api/radar")
def get_skaters_nearby(lat: float, lon: float, user_id: int):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT id_usuario, nickname, avatar,
                   ST_X(ubicacion_actual::geometry) as longitude, 
                   ST_Y(ubicacion_actual::geometry) as latitude
            FROM usuarios
            WHERE id_usuario != %s 
            AND visible = true              -- 👈 Solo gente en "Online"
            AND ubicacion_actual IS NOT NULL 
            AND ultima_conexion >= NOW() - INTERVAL '60 minutes' -- 👈 Filtro de 1 hora
            AND ST_DWithin(
                ubicacion_actual::geography, 
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                80000  -- 👈 80km para cubrir todo Santiago
            );
        """
        cur.execute(query, (user_id, lon, lat))
        return cur.fetchall()
    finally:
        conn.close()

# 3. Nuevo Endpoint para el Switch de Flutter (CORREGIDO)
@app.post("/api/users/status")
def update_status(data: dict):
    conn = get_db()
    try:
        cur = conn.cursor()
        # 1. Corregimos el nombre de la tabla a 'usuarios'
        # 2. Agregamos que actualice la ubicación si viene en el paquete
        if data.get('lat') and data.get('lon'):
            cur.execute("""
                UPDATE usuarios 
                SET visible = %s, 
                    ubicacion_actual = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    ultima_conexion = NOW()
                WHERE id_usuario = %s
            """, (data['visible'], data['lon'], data['lat'], data['id']))
        else:
            # Si no hay GPS, al menos cambiamos la visibilidad
            cur.execute("UPDATE usuarios SET visible = %s WHERE id_usuario = %s", 
                       (data['visible'], data['id']))
        
        conn.commit()  # 🔥 CRÍTICO: Sin esto, nada se guarda en PostgreSQL
        return {"success": True, "db_updated": True}
    except Exception as e:
        print(f"Error en status: {e}")
        raise HTTPException(500, str(e))
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