from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# --- MODELS ---
class UserAuth(BaseModel):
    username: str
    password: str

class Coordenadas(BaseModel):
    lat: float
    lon: float

class PerfilFull(BaseModel):
    avatar: str = ""
    edad: int = 0
    comuna: str = ""
    crew: str = ""
    stance: str = "Regular"
    trayectoria: str = ""

class SpotNuevo(BaseModel):
    nombre: str
    tipo: str
    descripcion: str
    ubicacion: str
    image: str
    lat: float
    lon: float

class ComentarioNuevo(BaseModel):
    id_spot: int
    id_usuario: int
    texto: str

class MensajeNuevo(BaseModel):
    id_remitente: int
    id_destinatario: int
    texto: str

class ConversacionRequest(BaseModel):
    id1: int
    id2: int

class DueloCreate(BaseModel):
    challenger_id: int
    opponent_id: int

class DueloPenalize(BaseModel):
    id_duelo: int
    id_perdedor: int

class ChallengeAccept(BaseModel):
    id_duelo: int
    id_usuario: int

class ChallengeReject(BaseModel):
    id_duelo: int
    id_usuario: int

class PostNuevo(BaseModel):
    id_usuario: int
    texto: str
    imagen: str = ""
    tipo: str = "general"

class PostLike(BaseModel):
    id_post: int
    id_usuario: int

class PostComment(BaseModel):
    id_post: int
    id_usuario: int
    texto: str

class ClaimRequest(BaseModel):
    id_usuario: int

class GameStartRequest(BaseModel):
    id_usuario: int

class ScoreSubmitRequest(BaseModel):
    session_token: str
    score: int

class RewardClaimRequest(BaseModel):
    id_usuario: int
    id_reward: int

# --- DATABASE CONNECTION ---
DATABASE_URL = os.environ.get('DATABASE_URL', "postgres://neondb_owner:npg_6LqS3tjoUAFC@ep-broad-tree-ah3h6jb0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require")

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    return conn
