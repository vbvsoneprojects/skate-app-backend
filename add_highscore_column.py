from database import get_db

def migrate():
    print("Iniciando migración...")
    conn = get_db()
    try:
        cur = conn.cursor()
        print("Agregando columna mejor_puntaje...")
        cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS mejor_puntaje INTEGER DEFAULT 0;")
        conn.commit()
        print("✅ Columna mejor_puntaje agregada (o ya existía).")
    except Exception as e:
        print(f"❌ Error migrando: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
