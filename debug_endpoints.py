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

        return {
            "usuarios_columns": [c['column_name'] for c in user_cols],
            "transacciones_table_exists": trans_exists,
            "db_connection": "OK"
        }
    finally:
        conn.close()
