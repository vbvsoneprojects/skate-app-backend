from database import get_db

def init_db():
    print("🛠️ Inicializando Base de Datos Local...")
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # --- EXTENSION POSTGIS (PRIMERO QUE TODO) ---
        print("Enabling PostGIS")
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        
        # --- TABLA USUARIOS ---
        print("Creating table: usuarios")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id_usuario SERIAL PRIMARY KEY,
                nickname VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                avatar TEXT DEFAULT '',
                edad INT DEFAULT 0,
                comuna VARCHAR(50),
                crew VARCHAR(50),
                stance VARCHAR(20) DEFAULT 'Regular',
                trayectoria VARCHAR(50),
                puntos_actuales INT DEFAULT 0,
                puntos_historicos INT DEFAULT 0,
                mejor_puntaje INT DEFAULT 0,
                racha_actual INT DEFAULT 0,
                mejor_racha INT DEFAULT 0,
                saldo_puntos INT DEFAULT 0,
                es_premium BOOLEAN DEFAULT FALSE,
                ultima_fecha_juego TIMESTAMP,
                ubicacion_actual VARCHAR(100)
            );
        """)

        # --- TABLA POSTS ---
        print("Creating table: posts")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id_post SERIAL PRIMARY KEY,
                id_usuario INT REFERENCES usuarios(id_usuario),
                texto TEXT,
                imagen TEXT,
                tipo VARCHAR(20) DEFAULT 'general',
                likes_count INT DEFAULT 0,
                comments_count INT DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # --- TABLA LIKES ---
        print("Creating table: post_likes")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_likes (
                id_like SERIAL PRIMARY KEY,
                id_post INT REFERENCES posts(id_post) ON DELETE CASCADE,
                id_usuario INT REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
                fecha TIMESTAMP DEFAULT NOW(),
                CONSTRAINT post_likes_unique UNIQUE (id_post, id_usuario)
            );
        """)
        
        # --- TABLA COMENTARIOS POSTS ---
        print("Creating table: post_comments")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_comments (
                id_comment SERIAL PRIMARY KEY,
                id_post INT REFERENCES posts(id_post) ON DELETE CASCADE,
                id_usuario INT REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
                texto TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- TABLA SPOTS ---
        print("Creating table: spots")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS spots (
                id_spot SERIAL PRIMARY KEY,
                nombre VARCHAR(100),
                descripcion TEXT,
                tipo VARCHAR(50),
                ubicacion VARCHAR(100),
                image TEXT,
                coordenadas geometry(point, 4326)
            );
        """)

        # --- TABLA COMENTARIOS SPOTS ---
        print("Creating table: comentarios (spots)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id_comentario SERIAL PRIMARY KEY,
                id_spot INT REFERENCES spots(id_spot) ON DELETE CASCADE,
                id_usuario INT REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
                texto TEXT,
                fecha TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- TABLA CALIFICACIONES ---
        print("Creating table: calificaciones")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS calificaciones (
                id_calificacion SERIAL PRIMARY KEY,
                id_spot INT REFERENCES spots(id_spot) ON DELETE CASCADE,
                id_usuario INT REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
                estrellas INT,
                fecha TIMESTAMP DEFAULT NOW(),
                CONSTRAINT unique_calificacion UNIQUE (id_spot, id_usuario)
            );
        """)

        # --- TABLA MENSAJES ---
        print("Creating table: mensajes")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id_mensaje SERIAL PRIMARY KEY,
                id_remitente INT REFERENCES usuarios(id_usuario),
                id_destinatario INT REFERENCES usuarios(id_usuario),
                texto TEXT,
                leido BOOLEAN DEFAULT FALSE,
                fecha_envio TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- TABLA DUELOS ---
        print("Creating table: duelos")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duelos (
                id_duelo SERIAL PRIMARY KEY,
                challenger_id INT REFERENCES usuarios(id_usuario),
                opponent_id INT REFERENCES usuarios(id_usuario),
                letras_actuales VARCHAR(20) DEFAULT '|',
                estado VARCHAR(20) DEFAULT 'pendiente',
                ganador VARCHAR(100),
                ganador_id INT,
                fecha_creacion TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- TABLA TRANSACCIONES PUNTOS ---
        print("Creating table: transacciones_puntos")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transacciones_puntos (
                id_transaccion SERIAL PRIMARY KEY,
                id_usuario INT REFERENCES usuarios(id_usuario),
                cantidad INT,
                tipo_transaccion VARCHAR(50),
                descripcion TEXT,
                fecha_creacion TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- TABLA GAME SESSIONS ---
        print("Creating table: game_sessions")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id_session SERIAL PRIMARY KEY,
                id_usuario INT REFERENCES usuarios(id_usuario),
                session_token VARCHAR(64) UNIQUE NOT NULL,
                fecha_inicio TIMESTAMP DEFAULT NOW(),
                fecha_expiracion TIMESTAMP NOT NULL,
                score_final INT,
                estado VARCHAR(20) DEFAULT 'active',
                ip_address VARCHAR(45)
            );
        """)

        # --- TABLA REWARDS ---
        print("Creating table: rewards")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rewards (
                id_reward SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT,
                imagen TEXT,
                costo_puntos INT NOT NULL,
                marca VARCHAR(100),
                stock INT DEFAULT 0,
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT NOW()
            );
        """)

        # --- TABLA USER REWARDS ---
        print("Creating table: user_rewards")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_rewards (
                id_claim SERIAL PRIMARY KEY,
                id_usuario INT REFERENCES usuarios(id_usuario),
                id_reward INT REFERENCES rewards(id_reward),
                fecha_canje TIMESTAMP DEFAULT NOW(),
                estado VARCHAR(20) DEFAULT 'pendiente',
                codigo_canje VARCHAR(20) UNIQUE,
                costo_pagado INT
            );
        """)

        # --- EXTENSION POSTGIS (Requerida para geometria) ---
        print("Enabling PostGIS")
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

        conn.commit()
        print("✅ Base de Datos Inicializada Correctamente.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al inicializar: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
