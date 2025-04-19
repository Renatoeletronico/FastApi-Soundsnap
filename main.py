from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import base64
import httpx
import random
import string
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ou coloque apenas o domínio do FlutterFlow se quiser limitar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_access_token():
    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()["access_token"]

@app.get("/search")
async def search_albums(
    query: str = Query(None, description="Nome do álbum ou artista"),
    limit: int = 1
):
    token = await get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        results = []

        # Se não houver query, fazer 10 buscas aleatórias
        queries = [query] if query else [random.choice(string.ascii_lowercase) for _ in range(10)]

        for q in queries:
            search_params = {
                "q": q,
                "type": "album",
                "limit": limit,
                "market": "NL"
            }

            search_resp = await client.get("https://api.spotify.com/v1/search", headers=headers, params=search_params)
            if search_resp.status_code != 200:
                continue  # Pula se der erro na busca

            search_data = search_resp.json()
            albums = search_data.get("albums", {}).get("items", [])

            for album in albums:
                album_id = album["id"]
                album_name = album["name"]
                release_date = album["release_date"][:4]
                image = album["images"][1]["url"] if album["images"] else None
                artist = album["artists"][0]
                artist_name = artist["name"]
                artist_id = artist["id"]
                faixas = album["total_tracks"]

                # Buscar gêneros do artista
                artist_resp = await client.get(f"https://api.spotify.com/v1/artists/{artist_id}", headers=headers)
                genres = []
                if artist_resp.status_code == 200:
                    artist_data = artist_resp.json()
                    genres = artist_data.get("genres", [])

                results.append({
                    "id": album_id,
                    "album": album_name,
                    "ano": release_date,
                    "artista": artist_name,
                    "imagem": image,
                    "faixas": faixas,
                    "generos": genres
                })

    return JSONResponse(content=results)
