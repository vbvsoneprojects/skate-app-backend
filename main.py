from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import secrets
import os

from database import * # Import everything from our new shared module
from posts_endpoints import router as posts_router

app = FastAPI()

app.include_router(posts_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Permitir todos los orígenes (para desarrollo)
        "https://skate-app-frontend.onrender.com",  # Frontend en producción
        "http://localhost:*",  # Desarrollo local
    ],
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

class MensajeNuevo(BaseModel):
    id_remitente: int
    id_destinatario: int
    texto: str

class ConversacionRequest(BaseModel):
    id1: int
    id2: int

class DueloCreate(BaseModel):
    challenger_id: int
    opponent_id: int

class DueloPenalize(BaseModel):
    id_duelo: int
    id_perdedor: int

class MensajeNuevo(BaseModel):
    id_remitente: int
    id_destinatario: int
    texto: str

class ChallengeAccept(BaseModel):
    id_duelo: int
    id_usuario: int

class ChallengeReject(BaseModel):
    id_duelo: int
    id_usuario: int

class PostNuevo(BaseModel):
    id_usuario: int
    texto: str
    imagen: str = ""
    tipo: str = "general"

class PostLike(BaseModel):
    id_post: int
    id_usuario: int

class PostComment(BaseModel):
    id_post: int
    id_usuario: int
    texto: str

class ClaimRequest(BaseModel):
    id_usuario: int

class GameStartRequest(BaseModel):
    id_usuario: int

class ScoreSubmitRequest(BaseModel):
    session_token: str
    score: int

class RewardClaimRequest(BaseModel):
    id_usuario: int
    id_reward: int

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
        visible bool DEFAULT true,
        ultima_conexion timestamp,
        total_retos int4 DEFAULT 0,
        retos_ganados int4 DEFAULT 0,
        retos_perdidos int4 DEFAULT 0,
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

    CREATE TABLE IF NOT EXISTS public.mensajes (
        id_mensaje serial4 NOT NULL,
        id_remitente int4,
        id_destinatario int4,
        texto text,
        leido bool DEFAULT false,
        fecha_envio timestamp DEFAULT NOW(),
        CONSTRAINT mensajes_pkey PRIMARY KEY (id_mensaje)
    );

    CREATE TABLE IF NOT EXISTS public.duelos (
        id_duelo serial4 NOT NULL,
        challenger_id int4,
        opponent_id int4,
        letras_actuales varchar(20) DEFAULT '|',
        estado varchar(20) DEFAULT 'pendiente',
        ganador varchar(100),
        ganador_id int4,
        fecha_creacion timestamp DEFAULT NOW(),
        CONSTRAINT duelos_pkey PRIMARY KEY (id_duelo)
    );

    CREATE TABLE IF NOT EXISTS public.posts (
        id_post serial4 NOT NULL,
        id_usuario int4,
        texto text NOT NULL,
        imagen text,
        tipo varchar(50) DEFAULT 'general',
        likes_count int4 DEFAULT 0,
        comments_count int4 DEFAULT 0,
        fecha_creacion timestamp DEFAULT NOW(),
        CONSTRAINT posts_pkey PRIMARY KEY (id_post)
    );

    CREATE TABLE IF NOT EXISTS public.post_likes (
        id_like serial4 NOT NULL,
        id_post int4,
        id_usuario int4,
        fecha timestamp DEFAULT NOW(),
        CONSTRAINT post_likes_pkey PRIMARY KEY (id_like),
        CONSTRAINT post_likes_unique UNIQUE (id_post, id_usuario)
    );

    CREATE TABLE IF NOT EXISTS public.post_comments (
        id_comment serial4 NOT NULL,
        id_post int4,
        id_usuario int4,
        texto text NOT NULL,
        fecha timestamp DEFAULT NOW(),
        CONSTRAINT post_comments_pkey PRIMARY KEY (id_comment)
    );

    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS puntos_actuales int4 DEFAULT 0;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS puntos_historicos int4 DEFAULT 0;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultima_fecha_juego date;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS racha_actual int4 DEFAULT 0;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS mejor_racha int4 DEFAULT 0;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_juego_fecha date;
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS es_admin bool DEFAULT false;

    CREATE TABLE IF NOT EXISTS public.transacciones_puntos (
        id_transaccion serial4 NOT NULL,
        id_usuario int4,
        cantidad int4,
        tipo_transaccion varchar(50),
        descripcion text,
        fecha_creacion timestamp DEFAULT NOW(),
        CONSTRAINT transacciones_puntos_pkey PRIMARY KEY (id_transaccion),
        CONSTRAINT fk_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
    );

    CREATE TABLE IF NOT EXISTS public.game_sessions (
        id_session serial4 PRIMARY KEY,
        id_usuario int4 REFERENCES usuarios(id_usuario),
        session_token varchar(64) UNIQUE NOT NULL,
        fecha_inicio timestamp DEFAULT NOW(),
        fecha_expiracion timestamp NOT NULL,
        score_final int4,
        estado varchar(20) DEFAULT 'active',
        ip_address varchar(45)
    );

    CREATE TABLE IF NOT EXISTS public.rewards (
        id_reward serial4 PRIMARY KEY,
        nombre varchar(100) NOT NULL,
        descripcion text,
        imagen text,
        costo_puntos int4 NOT NULL,
        marca varchar(100),
        stock int4 DEFAULT 0,
        activo bool DEFAULT true,
        fecha_creacion timestamp DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS public.user_rewards (
        id_claim serial4 PRIMARY KEY,
        id_usuario int4 REFERENCES usuarios(id_usuario),
        id_reward int4 REFERENCES rewards(id_reward),
        fecha_canje timestamp DEFAULT NOW(),
        estado varchar(20) DEFAULT 'pendiente',
        codigo_canje varchar(20) UNIQUE
    );

    UPDATE usuarios SET es_premium = true;
    UPDATE usuarios SET es_admin = true WHERE LOWER(nickname) IN ('alvaro', 'vbvsone');
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

@app.get("/api/debug/admins")
def debug_admins():
    """Endpoint temporal para verificar usuarios admin"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id_usuario, nickname, es_admin FROM usuarios WHERE es_admin = true OR LOWER(nickname) IN ('alvaro', 'vbvsone')")
        return cur.fetchall()
    finally:
        conn.close()


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
            SELECT id_usuario, nickname, avatar, crew, stance,
                   ST_X(ubicacion_actual::geometry) as longitude, 
                   ST_Y(ubicacion_actual::geometry) as latitude
            FROM usuarios
            WHERE id_usuario != %s 
            AND visible = true              -- 👈 Solo gente en "Online"
            AND ubicacion_actual IS NOT NULL 
            AND ultima_conexion >= NOW() - INTERVAL '5 minutes' -- 👈 Solo usuarios activos en los últimos 5 minutos
            AND ST_DWithin(
                ubicacion_actual::geography, 
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                12000000  -- 👈 12.000km para cubrir toda América
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
# 💬 SISTEMA DE MENSAJERÍA
# ==========================================

@app.post("/api/messages")
def send_message(msg: MensajeNuevo):
    """Enviar un mensaje de un usuario a otro"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mensajes (id_remitente, id_destinatario, texto)
            VALUES (%s, %s, %s)
            RETURNING id_mensaje, fecha_envio
        """, (msg.id_remitente, msg.id_destinatario, msg.texto))
        result = cur.fetchone()
        conn.commit()
        
        print(f"💬 Mensaje enviado: User {msg.id_remitente} → User {msg.id_destinatario}")
        return {
            "success": True,
            "id_mensaje": result[0],
            "fecha_envio": result[1]
        }
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.get("/api/messages/conversation")
def get_conversation(user1: int, user2: int):
    """Obtener todos los mensajes entre dos usuarios con timestamps en timezone de Chile"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                m.id_mensaje,
                m.id_remitente,
                m.id_destinatario,
                m.texto,
                m.leido,
                to_char(m.fecha_envio AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago', 'YYYY-MM-DD\"T\"HH24:MI:SS\"−03:00\"') as fecha_envio,
                u.nickname as remitente_nombre,
                u.avatar as remitente_avatar
            FROM mensajes m
            JOIN usuarios u ON m.id_remitente = u.id_usuario
            WHERE (id_remitente = %s AND id_destinatario = %s)
               OR (id_remitente = %s AND id_destinatario = %s)
            ORDER BY fecha_envio ASC
        """, (user1, user2, user2, user1))
        
        msgs = cur.fetchall()
        print(f"💬 Conversación User {user1} ↔ User {user2}: {len(msgs)} mensajes")
        return msgs
    except Exception as e:
        print(f"❌ Error obteniendo conversación: {e}")
        return []
    finally:
        conn.close()

@app.get("/api/messages/unread")
def get_unread_messages(user_id: int):
    """Obtener mensajes no leídos agrupados por remitente (para notificaciones)"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                id_remitente,
                u.nickname,
                u.avatar,
                COUNT(*) as cantidad,
                MAX(fecha_envio) as ultimo_mensaje
            FROM mensajes m
            JOIN usuarios u ON m.id_remitente = u.id_usuario
            WHERE id_destinatario = %s AND leido = FALSE
            GROUP BY id_remitente, u.nickname, u.avatar
            ORDER BY ultimo_mensaje DESC
        """, (user_id,))
        
        unread = cur.fetchall()
        total = sum([u['cantidad'] for u in unread])
        print(f"🔔 User {user_id} tiene {total} mensajes no leídos")
        return unread
    except Exception as e:
        print(f"❌ Error obteniendo no leídos: {e}")
        return []
    finally:
        conn.close()

@app.post("/api/messages/mark_read")
def mark_as_read(data: dict):
    """Marcar mensajes como leídos cuando se abre el chat"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE mensajes 
            SET leido = TRUE
            WHERE id_destinatario = %s 
              AND id_remitente = %s
              AND leido = FALSE
        """, (data['id_destinatario'], data['id_remitente']))
        conn.commit()
        
        updated = cur.rowcount
        print(f"✅ Marcados {updated} mensajes como leídos")
        return {"success": True, "updated": updated}
    except Exception as e:
        print(f"❌ Error marcando como leído: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.get("/api/messages/conversations/{user_id}")
def get_user_conversations(user_id: int):
    """Obtener todas las conversaciones de un usuario con el último mensaje y fecha en timezone de Chile"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Obtenemos todas las conversaciones donde el usuario participó
        cur.execute("""
            WITH conversaciones AS (
                SELECT DISTINCT
                    CASE 
                        WHEN id_remitente = %s THEN id_destinatario
                        ELSE id_remitente
                    END as otro_usuario_id
                FROM mensajes
                WHERE id_remitente = %s OR id_destinatario = %s
            )
            SELECT 
                c.otro_usuario_id,
                u.nickname,
                u.avatar,
                (SELECT texto 
                 FROM mensajes m 
                 WHERE (m.id_remitente = %s AND m.id_destinatario = c.otro_usuario_id)
                    OR (m.id_remitente = c.otro_usuario_id AND m.id_destinatario = %s)
                 ORDER BY m.fecha_envio DESC 
                 LIMIT 1) as ultimo_mensaje,
                (SELECT to_char(fecha_envio AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago', 'YYYY-MM-DD\"T\"HH24:MI:SS\"−03:00\"')
                 FROM mensajes m 
                 WHERE (m.id_remitente = %s AND m.id_destinatario = c.otro_usuario_id)
                    OR (m.id_remitente = c.otro_usuario_id AND m.id_destinatario = %s)
                 ORDER BY m.fecha_envio DESC 
                 LIMIT 1) as fecha_ultimo_mensaje,
                (SELECT COUNT(*) 
                 FROM mensajes m 
                 WHERE m.id_remitente = c.otro_usuario_id 
                   AND m.id_destinatario = %s 
                   AND m.leido = FALSE) as mensajes_no_leidos
            FROM conversaciones c
            JOIN usuarios u ON c.otro_usuario_id = u.id_usuario
            ORDER BY fecha_ultimo_mensaje DESC
        """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id))
        
        conversations = cur.fetchall()
        print(f"💬 Usuario {user_id} tiene {len(conversations)} conversaciones")
        return conversations
    except Exception as e:
        print(f"❌ Error obteniendo conversaciones: {e}")
        return []
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
                "es_admin": u.get('es_admin', False) or False,
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
        # Pedimos 'image' y calculamos el promedio de estrellas
        cur.execute("""
            SELECT 
                s.id_spot, 
                s.nombre, 
                s.descripcion, 
                s.tipo,
                s.ubicacion,
                s.image,
                ST_X(s.coordenadas::geometry), 
                ST_Y(s.coordenadas::geometry),
                COALESCE(AVG(c.estrellas), 0) as promedio
            FROM spots s
            LEFT JOIN calificaciones c ON s.id_spot = c.id_spot
            GROUP BY s.id_spot
            ORDER BY s.id_spot DESC
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
                "imagen": row[5],
                "longitude": row[6],
                "latitude": row[7],
                "promedio": float(row[8]),  # <--- NUEVO CAMPO AGREGADO
                "comments": []
            }

            # Parche para imágenes rotas
            if spot_dict["imagen"] and "blob:" in spot_dict["imagen"]:
                 spot_dict["imagen"] = "https://images.unsplash.com/photo-1520045864914-894836162391"

            cur.execute("""
                SELECT c.texto, u.nickname, u.avatar, c.id_comentario
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
                    "avatar": avatar,
                    "id": c[3] # ID de comentario para borrar
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


# ==========================================
# 🛡️ ZONA DE ADMIN (NUEVO)
# ==========================================

@app.delete("/api/spots/{id_spot}")
def delete_spot(id_spot: int, user_id: int):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar permisos (solo admin puede borrar spots? O creador?)
        # Asumamos solo Admin por seguridad para spots, o el creador.
        # Primero obtenemos el spot para ver quién lo creó (si guardamos eso? spots no tiene id_usuario creador explícito en el modelo SpotNuevo, pero debería tenerlo)
        # Revisando modelo SpotNuevo: no tiene id_usuario. Revisando tabla spots...
        # CREATE TABLE spots (id_spot serial4, ...). No tiene id_usuario.
        # Entonces solo ADMIN puede borrar spots.
        
        cur.execute("SELECT es_admin FROM usuarios WHERE id_usuario = %s", (user_id,))
        user_result = cur.fetchone()
        
        is_admin = False
        if user_result:
            is_admin = user_result['es_admin'] or False
        
        if not is_admin:
            raise HTTPException(403, "Solo administradores pueden eliminar spots")

        # Borrar comentarios asociados primero
        cur.execute("DELETE FROM comentarios WHERE id_spot = %s", (id_spot,))
        # Borrar spot
        cur.execute("DELETE FROM spots WHERE id_spot = %s", (id_spot,))
        
        conn.commit()
        return {"msg": "Spot eliminado"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.delete("/api/comments/{id_comentario}")
def delete_comment(id_comentario: int, user_id: int):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar dueño del comentario
        cur.execute("SELECT id_usuario FROM comentarios WHERE id_comentario = %s", (id_comentario,))
        comment = cur.fetchone()
        if not comment:
            raise HTTPException(404, "Comentario no encontrado")
            
        cur.execute("SELECT es_admin FROM usuarios WHERE id_usuario = %s", (user_id,))
        user_result = cur.fetchone()
        
        is_admin = False
        if user_result:
            is_admin = user_result['es_admin'] or False
        
        if comment['id_usuario'] != user_id and not is_admin:
            raise HTTPException(403, "No tienes permiso")

        cur.execute("DELETE FROM comentarios WHERE id_comentario = %s", (id_comentario,))
        conn.commit()
        return {"msg": "Comentario eliminado"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        conn.close()

class SpotImageUpdate(BaseModel):
    image: str

@app.put("/api/spots/{id_spot}/image")
def update_spot_image(id_spot: int, data: SpotImageUpdate):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE spots SET image = %s WHERE id_spot = %s", (data.image, id_spot))
        return {"msg": "Imagen actualizada"}
    finally:
        conn.close()

# ==========================================
# 🔔 CHALLENGE NOTIFICATIONS
# ==========================================

@app.get("/api/challenges/pending/{user_id}")
def get_pending_challenges(user_id: int):
    """Obtener todos los retos pendientes para un usuario"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                d.id_duelo,
                d.challenger_id,
                d.fecha_creacion,
                u.nickname as challenger_name,
                u.avatar as challenger_avatar
            FROM duelos d
            JOIN usuarios u ON d.challenger_id = u.id_usuario
            WHERE d.opponent_id = %s 
              AND d.estado = 'pendiente'
            ORDER BY d.fecha_creacion DESC
        """, (user_id,))
        
        challenges = cur.fetchall()
        print(f"🔔 Usuario {user_id} tiene {len(challenges)} retos pendientes")
        return challenges
    except Exception as e:
        print(f"❌ Error obteniendo retos pendientes: {e}")
        return []
    finally:
        conn.close()

@app.post("/api/challenges/accept")
def accept_challenge(data: ChallengeAccept):
    """Aceptar un reto"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar que el usuario es el oponente del duelo
        cur.execute("""
            SELECT challenger_id, opponent_id 
            FROM duelos 
            WHERE id_duelo = %s AND estado = 'pendiente'
        """, (data.id_duelo,))
        
        duelo = cur.fetchone()
        if not duelo:
            raise HTTPException(404, "Duelo no encontrado o ya fue respondido")
        
        if duelo['opponent_id'] != data.id_usuario:
            raise HTTPException(403, "No tienes permiso para aceptar este duelo")
        
        # Actualizar estado a 'en_curso'
        cur.execute("""
            UPDATE duelos 
            SET estado = 'en_curso' 
            WHERE id_duelo = %s
        """, (data.id_duelo,))
        
        conn.commit()
        print(f"✅ Reto {data.id_duelo} aceptado por usuario {data.id_usuario}")
        return {"success": True, "msg": "Reto aceptado"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error aceptando reto: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.post("/api/challenges/reject")
def reject_challenge(data: ChallengeReject):
    """Rechazar un reto"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar que el usuario es el oponente del duelo
        cur.execute("""
            SELECT opponent_id 
            FROM duelos 
            WHERE id_duelo = %s AND estado = 'pendiente'
        """, (data.id_duelo,))
        
        duelo = cur.fetchone()
        if not duelo:
            raise HTTPException(404, "Duelo no encontrado o ya fue respondido")
        
        if duelo['opponent_id'] != data.id_usuario:
            raise HTTPException(403, "No tienes permiso para rechazar este duelo")
        
        # Actualizar estado a 'rechazado'
        cur.execute("""
            UPDATE duelos 
            SET estado = 'rechazado' 
            WHERE id_duelo = %s
        """, (data.id_duelo,))
        
        conn.commit()
        print(f"❌ Reto {data.id_duelo} rechazado por usuario {data.id_usuario}")
        return {"success": True, "msg": "Reto rechazado"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error rechazando reto: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.get("/api/users/{id_usuario}/stats")
def get_user_stats(id_usuario: int):
    """Obtener estadísticas de retos de un usuario"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                total_retos,
                retos_ganados,
                retos_perdidos,
                CASE 
                    WHEN total_retos > 0 THEN ROUND((retos_ganados::numeric / total_retos::numeric) * 100, 1)
                    ELSE 0 
                END as win_rate
            FROM usuarios
            WHERE id_usuario = %s
        """, (id_usuario,))
        
        stats = cur.fetchone()
        if stats:
            print(f"📊 Estadísticas usuario {id_usuario}: {stats['total_retos']} retos, {stats['retos_ganados']} ganados")
            return stats
        else:
            return {
                "total_retos": 0,
                "retos_ganados": 0,
                "retos_perdidos": 0,
                "win_rate": 0
            }
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return {
            "total_retos": 0,
            "retos_ganados": 0,
            "retos_perdidos": 0,
            "win_rate": 0
        }
    finally:
        conn.close()

@app.get("/api/challenges/status/{id_duelo}")
def get_challenge_status(id_duelo: int):
    """Verificar el estado de un duelo específico"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                d.id_duelo,
                d.estado,
                d.challenger_id,
                d.opponent_id,
                u.nickname as opponent_name
            FROM duelos d
            JOIN usuarios u ON d.opponent_id = u.id_usuario
            WHERE d.id_duelo = %s
        """, (id_duelo,))
        
        duelo = cur.fetchone()
        if duelo:
            return duelo
        else:
            raise HTTPException(404, "Duelo no encontrado")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error obteniendo estado del duelo: {e}")
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
        
        if len(c_letters) >= 5 or len(o_letters) >= 5:
            game_over = True
            winner_id = row[2] if is_challenger else row[1]
            loser_id = row[1] if is_challenger else row[2]
            
            cur.execute("SELECT nickname FROM usuarios WHERE id_usuario = %s", (winner_id,))
            w_name = cur.fetchone()[0]
            winner_msg = f"¡Ganó {w_name}!"
            
            # Actualizar duelo
            cur.execute("""
                UPDATE duelos 
                SET estado = 'finalizado', ganador = %s, ganador_id = %s 
                WHERE id_duelo = %s
            """, (w_name, winner_id, pen.id_duelo))
            
            # 🏆 ACTUALIZAR ESTADÍSTICAS
            cur.execute("""
                UPDATE usuarios 
                SET total_retos = total_retos + 1,
                    retos_ganados = retos_ganados + 1
                WHERE id_usuario = %s
            """, (winner_id,))
            
            cur.execute("""
                UPDATE usuarios 
                SET total_retos = total_retos + 1,
                    retos_perdidos = retos_perdidos + 1
                WHERE id_usuario = %s
            """, (loser_id,))
            
            print(f"📊 Estadísticas actualizadas: Ganador={winner_id} ({w_name}), Perdedor={loser_id}")
            print(f"🏆 Estado final: {new_state}, Game Over: {game_over}, Ganador: {winner_msg}")
            
        # IMPORTANTE: Hacer commit ANTES de devolver
        conn.commit()

        return {
            "letras_actuales": new_state,
            "game_over": game_over, 
            "ganador": winner_msg
        }

    except Exception as e:
        print(f"❌ Error penalizar: {e}")
        import traceback
        traceback.print_exc()
        return {"letras_actuales": "", "game_over": False} 
    finally:
        conn.close()

# ==================== ENDPOINTS DE MENSAJERÍA ====================

@app.post("/api/messages/conversation")
async def get_conversation(data: ConversacionRequest):
    """Obtener mensajes entre dos usuarios"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id_mensaje, id_remitente, id_destinatario, texto, fecha_envio, leido
            FROM mensajes
            WHERE (id_remitente = %s AND id_destinatario = %s)
               OR (id_remitente = %s AND id_destinatario = %s)
            ORDER BY fecha_envio ASC
        """
        cur.execute(query, (data.id1, data.id2, data.id2, data.id1))
        mensajes = cur.fetchall()
        
        return mensajes
    
    except Exception as e:
        print(f"❌ Error obteniendo conversación: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/messages")
async def send_message(mensaje: MensajeNuevo):
    """Enviar un nuevo mensaje"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        query = """
            INSERT INTO mensajes (id_remitente, id_destinatario, texto, fecha_envio, leido)
            VALUES (%s, %s, %s, NOW(), FALSE)
        """
        cur.execute(query, (mensaje.id_remitente, mensaje.id_destinatario, mensaje.texto))
        conn.commit()
        
        print(f"✅ Mensaje enviado: {mensaje.id_remitente} -> {mensaje.id_destinatario}")
        return {"success": True}
    
        print(f"❌ Error enviando mensaje: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ==================== ENDPOINT DE CALIFICACIÓN ====================

class RatingData(BaseModel):
    id_spot: int
    id_usuario: int
    estrellas: int

@app.post("/api/rate/")
async def rate_spot(rating: RatingData):
    """Calificar un spot con estrellas (1-5) y recalcular promedio"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Insertar o actualizar calificación del usuario
        query = """
            INSERT INTO calificaciones (id_spot, id_usuario, estrellas)
            VALUES (%s, %s, %s)
            ON CONFLICT (id_spot, id_usuario) 
            DO UPDATE SET estrellas = EXCLUDED.estrellas
        """
        cur.execute(query, (rating.id_spot, rating.id_usuario, rating.estrellas))
        
        # Recalcular promedio del spot
        avg_query = """
            UPDATE spots
            SET promedio = (
                SELECT AVG(estrellas)::numeric(3,2)
                FROM calificaciones
                WHERE id_spot = %s
            )
            WHERE id_spot = %s
        """
        cur.execute(avg_query, (rating.id_spot, rating.id_spot))
        
        conn.commit()
        print(f"⭐ Spot {rating.id_spot} calificado con {rating.estrellas} estrellas por usuario {rating.id_usuario}")
        
        return {"success": True, "message": "Calificación guardada"}
    
    except Exception as e:
        print(f"❌ Error guardando calificación: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ==========================================
# 📸 SOCIAL FEED - POSTS API
# ==========================================

@app.get("/api/posts/")
def get_posts(offset: int = 0, limit: int = 20):
    """Obtener posts del feed social (cronológico)"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                p.id_post,
                p.id_usuario,
                p.texto,
                p.imagen,
                p.tipo,
                p.likes_count,
                p.comments_count,
                p.fecha_creacion,
                u.nickname as usuario_nombre,
                u.avatar as usuario_avatar
            FROM posts p
            JOIN usuarios u ON p.id_usuario = u.id_usuario
            ORDER BY p.fecha_creacion DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        posts = cur.fetchall()
        print(f"📸 Obteniendo {len(posts)} posts (offset: {offset}, limit: {limit})")
        return posts
    except Exception as e:
        print(f"❌ Error obteniendo posts: {e}")
        return []
    finally:
        conn.close()

@app.post("/api/posts/")
def create_post(post: PostNuevo):
    """Crear un nuevo post en el feed"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO posts (id_usuario, texto, imagen, tipo)
            VALUES (%s, %s, %s, %s)
            RETURNING id_post, fecha_creacion
        """, (post.id_usuario, post.texto, post.imagen, post.tipo))
        
        result = cur.fetchone()
        conn.commit()
        
        print(f"📸 Nuevo post creado: ID={result['id_post']} por usuario {post.id_usuario}")
        return {
            "success": True,
            "id_post": result['id_post'],
            "fecha_creacion": result['fecha_creacion']
        }
    except Exception as e:
        print(f"❌ Error creando post: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.post("/api/posts/{id_post}/like")
def toggle_like(id_post: int, like: PostLike):
    """Dar o quitar like a un post"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar si ya existe el like
        cur.execute("""
            SELECT id_like FROM post_likes 
            WHERE id_post = %s AND id_usuario = %s
        """, (id_post, like.id_usuario))
        
        existing_like = cur.fetchone()
        
        if existing_like:
            # Quitar like
            cur.execute("""
                DELETE FROM post_likes 
                WHERE id_post = %s AND id_usuario = %s
            """, (id_post, like.id_usuario))
            
            cur.execute("""
                UPDATE posts 
                SET likes_count = likes_count - 1 
                WHERE id_post = %s
            """, (id_post,))
            
            action = "removido"
        else:
            # Agregar like
            cur.execute("""
                INSERT INTO post_likes (id_post, id_usuario)
                VALUES (%s, %s)
            """, (id_post, like.id_usuario))
            
            cur.execute("""
                UPDATE posts 
                SET likes_count = likes_count + 1 
                WHERE id_post = %s
            """, (id_post,))
            
            action = "agregado"
        
        conn.commit()
        print(f"❤️ Like {action}: Post {id_post} por usuario {like.id_usuario}")
        
        # Obtener el nuevo conteo
        cur.execute("SELECT likes_count FROM posts WHERE id_post = %s", (id_post,))
        new_count = cur.fetchone()['likes_count']
        
        return {
            "success": True,
            "liked": action == "agregado",
            "likes_count": new_count
        }
    except Exception as e:
        print(f"❌ Error con like: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.post("/api/posts/{id_post}/comment")
def add_post_comment(id_post: int, comment: PostComment):
    """Agregar comentario a un post"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            INSERT INTO post_comments (id_post, id_usuario, texto)
            VALUES (%s, %s, %s)
            RETURNING id_comment, fecha
        """, (id_post, comment.id_usuario, comment.texto))
        
        result = cur.fetchone()
        
        # Incrementar contador de comentarios
        cur.execute("""
            UPDATE posts 
            SET comments_count = comments_count + 1 
            WHERE id_post = %s
        """, (id_post,))
        
        conn.commit()
        
        print(f"💬 Comentario agregado: Post {id_post} por usuario {comment.id_usuario}")
        return {
            "success": True,
            "id_comment": result['id_comment'],
            "fecha": result['fecha']
        }
    except Exception as e:
        print(f"❌ Error agregando comentario: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.get("/api/posts/{id_post}/comments")
def get_post_comments(id_post: int):
    """Obtener comentarios de un post"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                c.id_comment,
                c.id_usuario,
                c.texto,
                c.fecha,
                u.nickname as usuario_nombre,
                u.avatar as usuario_avatar
            FROM post_comments c
            JOIN usuarios u ON c.id_usuario = u.id_usuario
            WHERE c.id_post = %s
            ORDER BY c.fecha ASC
        """, (id_post,))
        
        comments = cur.fetchall()
        print(f"💬 Obteniendo {len(comments)} comentarios para post {id_post}")
        return comments
    except Exception as e:
        print(f"❌ Error obteniendo comentarios: {e}")
        return []
    finally:
        conn.close()

# ==========================================
# === SKATE ECONOMY ===
# ==========================================

@app.post("/api/game/claim-daily")
def claim_daily_points(claim: ClaimRequest):
    """Reclamar 10 puntos diarios (una vez por día)"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Validar si el usuario existe
        cur.execute("SELECT id_usuario, ultima_fecha_juego FROM usuarios WHERE id_usuario = %s", (claim.id_usuario,))
        usuario = cur.fetchone()
        
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Validar si ya jugó hoy
        hoy = date.today()
        if usuario['ultima_fecha_juego'] == hoy:
            raise HTTPException(status_code=400, detail="Ya jugó hoy")
        
        # Iniciar transacción para otorgar puntos
        # a) Sumar 10 puntos a puntos_actuales y puntos_historicos
        cur.execute("""
            UPDATE usuarios 
            SET puntos_actuales = puntos_actuales + 10,
                puntos_historicos = puntos_historicos + 10,
                ultima_fecha_juego = %s
            WHERE id_usuario = %s
        """, (hoy, claim.id_usuario))
        
        # b) Insertar registro en transacciones_puntos
        cur.execute("""
            INSERT INTO transacciones_puntos (id_usuario, cantidad, tipo_transaccion, descripcion)
            VALUES (%s, 10, 'daily_claim', 'Reclamo diario de puntos')
        """, (claim.id_usuario,))
        
        conn.commit()
        
        print(f"🎮 Usuario {claim.id_usuario} reclamó 10 puntos diarios")
        return {
            "success": True,
            "puntos_otorgados": 10,
            "mensaje": "¡10 puntos otorgados!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en claim-daily: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/game/leaderboard")
def get_leaderboard():
    """Obtener el top 10 de usuarios por puntos históricos"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                id_usuario,
                nickname,
                avatar,
                puntos_historicos,
                puntos_actuales
            FROM usuarios
            ORDER BY puntos_historicos DESC
            LIMIT 10
        """)
        
        leaderboard = cur.fetchall()
        print(f"🏆 Obteniendo leaderboard: {len(leaderboard)} usuarios")
        return leaderboard
        
    except Exception as e:
        print(f"❌ Error obteniendo leaderboard: {e}")
        return []
    finally:
        conn.close()

# ==========================================
# === GAME SESSIONS & SCORE VALIDATION ===
# ==========================================

@app.post("/api/game/start-session")
def start_game_session(req: GameStartRequest):
    """Iniciar nueva sesión de juego (anti-cheat)"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Límite diario: 500 partidas max (AUMENTADO PARA TESTING)
        cur.execute("""
            SELECT COUNT(*) as count FROM game_sessions 
            WHERE id_usuario = %s 
            AND DATE(fecha_inicio) = CURRENT_DATE
        """, (req.id_usuario,))
        
        if cur.fetchone()['count'] >= 500:
            raise HTTPException(status_code=429, detail="Límite diario alcanzado (500 partidas)")
        
        # Generar token seguro
        token = secrets.token_urlsafe(32)
        expiration = datetime.now() + timedelta(minutes=5)
        
        cur.execute("""
            INSERT INTO game_sessions (id_usuario, session_token, fecha_expiracion)
            VALUES (%s, %s, %s)
            RETURNING id_session
        """, (req.id_usuario, token, expiration))
        
        session_id = cur.fetchone()['id_session']
        conn.commit()
        
        print(f"🎮 Sesión iniciada: {session_id} para usuario {req.id_usuario}")
        return {"session_token": token, "expires_in": 300}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creando sesión: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/game/submit-score")
def submit_game_score(req: ScoreSubmitRequest):
    """Enviar puntaje del juego con validación anti-cheat"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Validar sesión
        cur.execute("""
            SELECT id_session, id_usuario, fecha_expiracion, estado
            FROM game_sessions
            WHERE session_token = %s
        """, (req.session_token,))
        
        session = cur.fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Sesión inválida")
        
        if session['estado'] != 'active':
            raise HTTPException(status_code=400, detail="Sesión ya completada")
        
        if datetime.now() > session['fecha_expiracion']:
            raise HTTPException(status_code=400, detail="Sesión expirada")
        
        # Anti-cheat: Puntaje máximo realista
        if req.score > 1000:
            raise HTTPException(status_code=400, detail="Puntaje sospechoso")
        
        # Marcar sesión como completada
        cur.execute("""
            UPDATE game_sessions 
            SET score_final = %s, estado = 'completed'
            WHERE id_session = %s
        """, (req.score, session['id_session']))
        
        # Otorgar puntos (1 punto por cada 1 de score, directo)
        points_earned = req.score 
        
        # Calcular racha
        hoy = date.today()
        cur.execute("""
            SELECT ultimo_juego_fecha, racha_actual
            FROM usuarios WHERE id_usuario = %s
        """, (session['id_usuario'],))
        
        user_data = cur.fetchone()
        ultima_fecha = user_data['ultimo_juego_fecha']
        racha = user_data['racha_actual'] or 0
        
        # Lógica de racha
        if ultima_fecha:
            dias_diff = (hoy - ultima_fecha).days
            if dias_diff == 1:
                racha += 1  # Día consecutivo
            elif dias_diff > 1:
                racha = 1   # Racha rota
        else:
            racha = 1
        
        # Actualizar usuario
        cur.execute("""
            UPDATE usuarios 
            SET puntos_actuales = puntos_actuales + %s,
                puntos_historicos = puntos_historicos + %s,
                ultimo_juego_fecha = %s,
                racha_actual = %s,
                mejor_racha = GREATEST(mejor_racha, %s),
                mejor_puntaje = GREATEST(COALESCE(mejor_puntaje, 0), %s) 
            WHERE id_usuario = %s
        """, (points_earned, points_earned, hoy, racha, racha, req.score, session['id_usuario']))
        
        # Registrar transacción
        cur.execute("""
            INSERT INTO transacciones_puntos (id_usuario, cantidad, tipo_transaccion, descripcion)
            VALUES (%s, %s, 'game_score', %s)
        """, (session['id_usuario'], points_earned, f"Puntaje de juego: {req.score}"))
        
        conn.commit()
        
        print(f"✅ Score {req.score} → {points_earned} puntos. Racha: {racha}")
        return {
            "success": True,
            "points_earned": points_earned,
            "current_streak": racha,
            "score": req.score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error submit-score: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ==========================================
# === REWARDS CATALOG & REDEMPTION ===
# ==========================================

@app.get("/api/game/rewards")
def get_rewards():
    """Obtener catálogo de premios disponibles"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id_reward, nombre, descripcion, imagen, 
                   costo_puntos, marca, stock
            FROM rewards
            WHERE activo = true AND stock > 0
            ORDER BY costo_puntos ASC
        """)
        
        rewards = cur.fetchall()
        print(f"🎁 Catálogo: {len(rewards)} premios disponibles")
        return rewards
        
    except Exception as e:
        print(f"❌ Error obteniendo rewards: {e}")
        return []
    finally:
        conn.close()

@app.post("/api/game/claim-reward")
def claim_reward(req: RewardClaimRequest):
    """Canjear puntos por premio"""
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener costo del premio
        cur.execute("SELECT costo_puntos, stock, nombre FROM rewards WHERE id_reward = %s", (req.id_reward,))
        reward = cur.fetchone()
        
        if not reward or reward['stock'] <= 0:
            raise HTTPException(status_code=404, detail="Premio no disponible")
        
        # Verificar puntos del usuario
        cur.execute("SELECT puntos_actuales FROM usuarios WHERE id_usuario = %s", (req.id_usuario,))
        user = cur.fetchone()
        
        if user['puntos_actuales'] < reward['costo_puntos']:
            raise HTTPException(status_code=400, detail="Puntos insuficientes")
        
        # Descontar puntos
        cur.execute("""
            UPDATE usuarios 
            SET puntos_actuales = puntos_actuales - %s
            WHERE id_usuario = %s
        """, (reward['costo_puntos'], req.id_usuario))
        
        # Reducir stock
        cur.execute("UPDATE rewards SET stock = stock - 1 WHERE id_reward = %s", (req.id_reward,))
        
        # Crear registro de canje
        codigo = secrets.token_hex(4).upper()
        cur.execute("""
            INSERT INTO user_rewards (id_usuario, id_reward, codigo_canje)
            VALUES (%s, %s, %s)
            RETURNING id_claim
        """, (req.id_usuario, req.id_reward, codigo))
        
        claim_id = cur.fetchone()['id_claim']
        
        # Registrar transacción negativa
        cur.execute("""
            INSERT INTO transacciones_puntos (id_usuario, cantidad, tipo_transaccion, descripcion)
            VALUES (%s, %s, 'reward_claim', %s)
        """, (req.id_usuario, -reward['costo_puntos'], f"Premio: {reward['nombre']} - Código: {codigo}"))
        
        conn.commit()
        
        print(f"🎁 Usuario {req.id_usuario} canjeó premio. Código: {codigo}")
        return {
            "success": True,
            "codigo_canje": codigo,
            "mensaje": f"¡Premio canjeado! Tu código: {codigo}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error canjeando premio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/game/start-session")
def start_session(req: GameStartRequest):
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Validar límite diario (20 partidas)
        cur.execute("""
            SELECT COUNT(*) FROM game_sessions 
            WHERE id_usuario = %s 
            AND fecha_inicio >= NOW() - INTERVAL '1 day'
        """, (req.id_usuario,))
        count = cur.fetchone()[0]
        
        if count >= 20:
            raise HTTPException(429, "Has alcanzado el límite diario de partidas (20).")

        # Generar token
        token = secrets.token_urlsafe(32)
        
        cur.execute("""
            INSERT INTO game_sessions (id_usuario, session_token, fecha_inicio, expires_at)
            VALUES (%s, %s, NOW(), NOW() + INTERVAL '5 minutes')
        """, (req.id_usuario, token))
        
        conn.commit()
        return {"session_token": token, "expires_in": 300}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.post("/api/game/submit-score")
def submit_score(req: ScoreSubmitRequest):
    if req.score > 2000: # Anti-cheat básico
        raise HTTPException(400, "Puntaje inválido")

    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Validar sesión
        cur.execute("""
            SELECT id_usuario, is_valid 
            FROM game_sessions 
            WHERE session_token = %s 
            AND expires_at > NOW()
            AND is_valid = TRUE
        """, (req.session_token,))
        
        session = cur.fetchone()
        if not session:
            raise HTTPException(401, "Sesión inválida o expirada")
            
        user_id = session['id_usuario']
        points_earned = req.score # 1 punto cada 1 score (CORREGIDO DUPLICADO)
        
        # Iniciar transacción
        cur.execute("BEGIN")
        
        # 1. Invalidar sesión usada
        cur.execute("""
            UPDATE game_sessions 
            SET score = %s, is_valid = FALSE 
            WHERE session_token = %s
        """, (req.score, req.session_token))
        
        # 2. Actualizar puntos y racha
        # Verificar último juego para racha
        cur.execute("""
            SELECT ultima_fecha_juego, racha_actual 
            FROM usuarios WHERE id_usuario = %s FOR UPDATE
        """, (user_id,))
        user_data = cur.fetchone()
        
        today = datetime.now().date()
        last_played = user_data['ultima_fecha_juego']
        current_streak = user_data['racha_actual'] or 0
        
        new_streak = current_streak
        
        if last_played:
            delta = (today - last_played).days
            if delta == 1: # Jugó ayer -> Sumar racha
                new_streak += 1
            elif delta > 1: # Perdió racha
                new_streak = 1
            # Si delta == 0 (mismo día), mantiene racha
        else:
            new_streak = 1 # Primer juego
            
        cur.execute("""
            UPDATE usuarios 
            SET puntos_actuales = COALESCE(puntos_actuales, 0) + %s,
                puntos_historicos = COALESCE(puntos_historicos, 0) + %s,
                racha_actual = %s,
                mejor_racha = GREATEST(mejor_racha, %s),
                ultima_fecha_juego = %s,
                mejor_puntaje = GREATEST(COALESCE(mejor_puntaje, 0), %s)
            WHERE id_usuario = %s
        """, (points_earned, points_earned, new_streak, new_streak, today, req.score, user_id))
        
        conn.commit()
        
        return {
            "success": True, 
            "points_earned": points_earned,
            "current_streak": new_streak
        }
    except Exception as e:
        conn.rollback()
        print(f"Error submitting score: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.get("/api/game/rewards")
def get_game_rewards(): # Renamed to avoid confusion with any other get_rewards
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM rewards 
            WHERE activo = TRUE 
            AND stock_disponible > 0
            ORDER BY costo_puntos ASC
        """)
        return cur.fetchall()
    finally:
        conn.close()

@app.post("/api/game/claim-reward")
def claim_reward(req: RewardClaimRequest):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("BEGIN")
        
        # Verificar usuario y puntos
        cur.execute("SELECT puntos_actuales FROM usuarios WHERE id_usuario = %s FOR UPDATE", (req.id_usuario,))
        user_res = cur.fetchone()
        
        # Verificar premio y stock
        cur.execute("SELECT * FROM rewards WHERE id_reward = %s FOR UPDATE", (req.id_reward,))
        reward_res = cur.fetchone()
        
        if not user_res or not reward_res:
             raise HTTPException(404, "Usuario o premio no encontrado")
             
        if user_res['puntos_actuales'] < reward_res['costo_puntos']:
            raise HTTPException(400, "Puntos insuficientes")
            
        if reward_res['stock_disponible'] <= 0:
            raise HTTPException(400, "Premio agotado")
            
        # Procesar canje
        new_balance = user_res['puntos_actuales'] - reward_res['costo_puntos']
        claim_code = secrets.token_hex(4).upper()
        
        # 1. Descontar puntos
        cur.execute("UPDATE usuarios SET puntos_actuales = %s WHERE id_usuario = %s", (new_balance, req.id_usuario))
        
        # 2. Descontar stock
        cur.execute("UPDATE rewards SET stock_disponible = stock_disponible - 1 WHERE id_reward = %s", (req.id_reward,))
        
        # 3. Registrar transacción
        cur.execute("""
            INSERT INTO user_rewards (id_usuario, id_reward, fecha_canje, codigo_canje, costo_pagado)
            VALUES (%s, %s, NOW(), %s, %s)
        """, (req.id_usuario, req.id_reward, claim_code, reward_res['costo_puntos']))
        
        conn.commit()
        
        return {
            "success": True, 
            "codigo_canje": claim_code,
            "mensaje": "Premio canjeado con éxito"
        }
        
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@app.get("/api/game/leaderboard")
def get_leaderboard():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id_usuario, nickname, avatar, comuna, puntos_historicos, mejor_racha, mejor_puntaje
            FROM usuarios
            ORDER BY mejor_puntaje DESC NULLS LAST
            LIMIT 10
        """)
        return cur.fetchall()
    finally:
        conn.close()

