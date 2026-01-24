
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets
from main import get_db, RealDictCursor # Import from main to reuse DB connection

router = APIRouter()

# --- MODELS ---
class GameStartRequest(BaseModel):
    id_usuario: int

class ScoreSubmitRequest(BaseModel):
    session_token: str
    score: int

class RewardClaimRequest(BaseModel):
    id_usuario: int
    id_reward: int

# --- ENDPOINTS ---

@router.post("/game/start-session")
def start_session(req: GameStartRequest):
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Validar límite diario (20 partidas)
        cur.execute("""
            SELECT COUNT(*) FROM game_sessions 
            WHERE id_usuario = %s 
            AND fecha_inicio >= NOW() - INTERVAL '1 day'
        """, (req.id_usuario,))
        count = cur.fetchone()[0]
        
        if count >= 20:
            raise HTTPException(429, "Has alcanzado el límite diario de partidas (20).")

        # Generar token
        token = secrets.token_urlsafe(32)
        
        cur.execute("""
            INSERT INTO game_sessions (id_usuario, session_token, fecha_inicio, expires_at)
            VALUES (%s, %s, NOW(), NOW() + INTERVAL '5 minutes')
        """, (req.id_usuario, token))
        
        conn.commit()
        return {"session_token": token, "expires_in": 300}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@router.post("/game/submit-score")
def submit_score(req: ScoreSubmitRequest):
    if req.score > 2000: # Anti-cheat básico
        raise HTTPException(400, "Puntaje inválido")

    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Validar sesión
        cur.execute("""
            SELECT id_usuario, is_valid 
            FROM game_sessions 
            WHERE session_token = %s 
            AND expires_at > NOW()
            AND is_valid = TRUE
        """, (req.session_token,))
        
        session = cur.fetchone()
        if not session:
            raise HTTPException(401, "Sesión inválida o expirada")
            
        user_id = session['id_usuario']
        points_earned = req.score // 10 # 1 punto cada 10 score
        
        # Iniciar transacción
        cur.execute("BEGIN")
        
        # 1. Invalidar sesión usada
        cur.execute("""
            UPDATE game_sessions 
            SET score = %s, is_valid = FALSE 
            WHERE session_token = %s
        """, (req.score, req.session_token))
        
        # 2. Actualizar puntos y racha
        # Verificar último juego para racha
        cur.execute("""
            SELECT ultima_fecha_juego, racha_actual 
            FROM usuarios WHERE id_usuario = %s FOR UPDATE
        """, (user_id,))
        user_data = cur.fetchone()
        
        today = datetime.now().date()
        last_played = user_data['ultima_fecha_juego']
        current_streak = user_data['racha_actual'] or 0
        
        new_streak = current_streak
        
        if last_played:
            delta = (today - last_played).days
            if delta == 1: # Jugó ayer -> Sumar racha
                new_streak += 1
            elif delta > 1: # Perdió racha
                new_streak = 1
            # Si delta == 0 (mismo día), mantiene racha
        else:
            new_streak = 1 # Primer juego
            
        cur.execute("""
            UPDATE usuarios 
            SET puntos_actuales = COALESCE(puntos_actuales, 0) + %s,
                puntos_historicos = COALESCE(puntos_historicos, 0) + %s,
                racha_actual = %s,
                mejor_racha = GREATEST(mejor_racha, %s),
                ultima_fecha_juego = %s
            WHERE id_usuario = %s
        """, (points_earned, points_earned, new_streak, new_streak, today, user_id))
        
        conn.commit()
        
        return {
            "success": True, 
            "points_earned": points_earned,
            "current_streak": new_streak
        }
    except Exception as e:
        conn.rollback()
        print(f"Error submitting score: {e}")
        raise HTTPException(500, str(e))
    finally:
        conn.close()

@router.get("/game/leaderboard")
def get_leaderboard():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id_usuario, nickname, avatar, comuna, puntos_historicos, mejor_racha
            FROM usuarios
            ORDER BY puntos_historicos DESC
            LIMIT 10
        """)
        return cur.fetchall()
    finally:
        conn.close()

@router.get("/game/rewards")
def get_rewards():
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM rewards 
            WHERE activo = TRUE 
            AND stock_disponible > 0
            ORDER BY costo_puntos ASC
        """)
        return cur.fetchall()
    finally:
        conn.close()

@router.post("/game/claim-reward")
def claim_reward(req: RewardClaimRequest):
    conn = get_db()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("BEGIN")
        
        # Verificar usuario y puntos
        cur.execute("SELECT puntos_actuales FROM usuarios WHERE id_usuario = %s FOR UPDATE", (req.id_usuario,))
        user_res = cur.fetchone()
        
        # Verificar premio y stock
        cur.execute("SELECT * FROM rewards WHERE id_reward = %s FOR UPDATE", (req.id_reward,))
        reward_res = cur.fetchone()
        
        if not user_res or not reward_res:
             raise HTTPException(404, "Usuario o premio no encontrado")
             
        if user_res['puntos_actuales'] < reward_res['costo_puntos']:
            raise HTTPException(400, "Puntos insuficientes")
            
        if reward_res['stock_disponible'] <= 0:
            raise HTTPException(400, "Premio agotado")
            
        # Procesar canje
        new_balance = user_res['puntos_actuales'] - reward_res['costo_puntos']
        claim_code = secrets.token_hex(4).upper()
        
        # 1. Descontar puntos
        cur.execute("UPDATE usuarios SET puntos_actuales = %s WHERE id_usuario = %s", (new_balance, req.id_usuario))
        
        # 2. Descontar stock
        cur.execute("UPDATE rewards SET stock_disponible = stock_disponible - 1 WHERE id_reward = %s", (req.id_reward,))
        
        # 3. Registrar transacción
        cur.execute("""
            INSERT INTO user_rewards (id_usuario, id_reward, fecha_canje, codigo_canje, costo_pagado)
            VALUES (%s, %s, NOW(), %s, %s)
        """, (req.id_usuario, req.id_reward, claim_code, reward_res['costo_puntos']))
        
        conn.commit()
        
        return {
            "success": True, 
            "codigo_canje": claim_code,
            "mensaje": "Premio canjeado con éxito"
        }
        
    except HTTPException as he:
        conn.rollback()
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, str(e))
    finally:
        conn.close()