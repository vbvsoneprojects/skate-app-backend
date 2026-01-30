import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import date

DATABASE_URL = "postgresql://skateuser:skatepass@localhost:5432/skate_app"

def fix_data():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        print("🔍 Buscando usuario 'vbvsone'...")
        cur.execute("SELECT * FROM usuarios WHERE nickname = 'vbvsone'")
        user = cur.fetchone()
        
        if not user:
            print("❌ Usuario 'vbvsone' no encontrado en la DB.")
            # Listar quienes estan
            cur.execute("SELECT id_usuario, nickname FROM usuarios")
            print("👥 Usuarios existentes:", cur.fetchall())
            return

        print(f"✅ Usuario encontrado: ID {user['id_usuario']}")
        print("Estado actual:", user)

        print("🛠️ Reparando valores NULL...")
        cur.execute("""
            UPDATE usuarios 
            SET puntos_actuales = COALESCE(puntos_actuales, 0),
                puntos_historicos = COALESCE(puntos_historicos, 0),
                mejor_puntaje = COALESCE(mejor_puntaje, 0),
                racha_actual = COALESCE(racha_actual, 0),
                mejor_racha = COALESCE(mejor_racha, 0),
                retos_ganados = COALESCE(retos_ganados, 0),
                retos_perdidos = COALESCE(retos_perdidos, 0),
                total_retos = COALESCE(total_retos, 0),
                visible = COALESCE(visible, true)
            WHERE id_usuario = %s
        """, (user['id_usuario'],))
        
        # Tambien asegurar la fecha
        cur.execute("""
            UPDATE usuarios SET ultimo_juego_fecha = %s WHERE id_usuario = %s AND ultimo_juego_fecha IS NULL
        """, (date.today(), user['id_usuario']))

        conn.commit()
        print("✅ Reparación completada.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_data()
