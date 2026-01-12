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
    """Obtener todos los mensajes entre dos usuarios"""
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
                m.fecha_envio,
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