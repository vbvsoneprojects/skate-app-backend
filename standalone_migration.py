import psycopg2
import os

DATABASE_URL = "postgres://neondb_owner:npg_6LqS3tjoUAFC@ep-broad-tree-ah3h6jb0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

def migrate():
    print("Iniciando migración (Standalone)...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        print("Agregando columna mejor_puntaje...")
        cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS mejor_puntaje INTEGER DEFAULT 0;")
        print("✅ Columna mejor_puntaje agregada (o ya existía).")
        conn.close()
    except Exception as e:
        print(f"❌ Error migrando: {e}")

if __name__ == "__main__":
    migrate()
