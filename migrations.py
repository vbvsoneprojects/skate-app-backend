import psycopg2
from database import get_db

def run_migrations():
    print("🔄 Running Auto-Migrations...")
    try:
        conn = get_db()
        cur = conn.cursor()

        # 1. Asegurar columnas en tabla USUARIOS
        # puntos_actuales
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='usuarios' AND column_name='puntos_actuales';")
        if not cur.fetchone():
            print("➕ Adding column 'puntos_actuales'...")
            cur.execute("ALTER TABLE usuarios ADD COLUMN puntos_actuales INTEGER DEFAULT 0;")
        
        # puntos_historicos
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='usuarios' AND column_name='puntos_historicos';")
        if not cur.fetchone():
            print("➕ Adding column 'puntos_historicos'...")
            cur.execute("ALTER TABLE usuarios ADD COLUMN puntos_historicos INTEGER DEFAULT 0;")

        # mejor_puntaje
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='usuarios' AND column_name='mejor_puntaje';")
        if not cur.fetchone():
            print("➕ Adding column 'mejor_puntaje'...")
            cur.execute("ALTER TABLE usuarios ADD COLUMN mejor_puntaje INTEGER DEFAULT 0;")

        # avatar (por si acaso)
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='usuarios' AND column_name='avatar';")
        if not cur.fetchone():
            print("➕ Adding column 'avatar'...")
            cur.execute("ALTER TABLE usuarios ADD COLUMN avatar TEXT DEFAULT '';")


        # 2. Crear tabla de Transacciones (si no existe)
        print("🔨 Checking table 'transacciones_puntos'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transacciones_puntos (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES usuarios(id),
                puntos INTEGER,
                tipo VARCHAR(50),
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Crear indices básicos (Optimización solicitada)
        print("🚀 Optimizing indexes...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_puntos ON usuarios(puntos_actuales DESC);")

        conn.commit()
        conn.close()
        print("✅ Migrations Complete!")
        
    except Exception as e:
        print(f"❌ Migration Failed: {e}")
