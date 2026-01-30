from database import get_db, RealDictCursor

def check():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        print("--- CONSULTANDO USUARIO ID 2 ---")
        cur.execute("SELECT * FROM usuarios WHERE id_usuario = 2")
        user = cur.fetchone()
        if user:
            print(f"Nickname: {user['nickname']}")
            print(f"Puntos Históricos: {user['puntos_historicos']}")
            print(f"Mejor Puntaje (Columna Nueva): {user.get('mejor_puntaje', 'NO EXISTE')}")
            print(f"Puntos Actuales: {user['puntos_actuales']}")
            print("-" * 30)
        else:
            print("Usuario 2 no encontrado")

        # Check column existence in schema
        print("\n--- COLUMNAS EN TABLA USUARIOS ---")
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'usuarios'")
        cols = [row['column_name'] for row in cur.fetchall()]
        print(cols)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check()
