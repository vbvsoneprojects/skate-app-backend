from fastapi import APIRouter
from database import get_db
from psycopg2.extras import RealDictCursor

router = APIRouter()

@router.get("/api/debug/schema")
def check_schema():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Check usuarios columns
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'usuarios';
        """)
        user_cols = cur.fetchall()

        # 2. Check transacciones_puntos existence via catalog
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE  table_schema = 'public'
                AND    table_name   = 'transacciones_puntos'
            );
        """)
        trans_exists = cur.fetchone()['exists']

@router.get("/api/debug/fix_user/{nickname}")
def fix_user_points(nickname: str):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Buscar usuario
        cur.execute("SELECT id_usuario, saldo_puntos, puntos_actuales FROM usuarios WHERE nickname = %s", (nickname,))
        user = cur.fetchone()
        
        if not user:
            return {"error": "Usuario no encontrado"}
            
        legacy = user['saldo_puntos'] or 0
        new_pts = user['puntos_actuales'] or 0
        
        # 2. Forzar Sincronización (Old -> New)
        cur.execute("""
            UPDATE usuarios 
            SET puntos_actuales = %s, 
                puntos_historicos = %s 
            WHERE id_usuario = %s
        """, (legacy, legacy, user['id_usuario']))
        
        conn.commit()
        
        return {
            "msg": "✅ Usuario reparado exitosamente",
            "nickname": nickname,
            "antes": {"legacy": legacy, "new": new_pts},
            "ahora": {"legacy": legacy, "new": legacy},
            "action": "Sync Forzado completed"
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()
