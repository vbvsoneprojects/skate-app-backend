from database import get_db, RealDictCursor
import random

def seed():
    print("🚀 Iniciando sembrado de Leaderboard...")
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Lista de IDs y rangos de puntaje para hacerlos competitivos
        # TonyHawk (Pro) -> 20-50
        # Otros -> 3-15
        
        updates = [
            (1, 45),  # TonyHawk: 45 puntos (difícil)
            (3, 12),  # alvaro
            (4, 8),   # vbvsone
            (5, 25),  # raquel (medio)
            (6, 5),   # tete
        ]
        
        print(f"🎯 Actualizando {len(updates)} usuarios con puntajes ficticios...")
        
        for user_id, score in updates:
            # Solo actualizamos si mejor_puntaje es NULL o 0 para no borrar records reales si existieran
            cur.execute("""
                UPDATE usuarios 
                SET mejor_puntaje = %s, 
                    puntos_historicos = GREATEST(puntos_historicos, %s),
                    puntos_actuales = GREATEST(puntos_actuales, %s)
                WHERE id_usuario = %s 
                AND (mejor_puntaje IS NULL OR mejor_puntaje = 0)
            """, (score, score, score, user_id))
            
        conn.commit()
        print("✅ Leaderboard poblada con éxito.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed()
