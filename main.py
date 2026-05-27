import os
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import unquote

app = FastAPI(title="AiAudioPlayer Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jamendo API anahtarı (Render'da Environment Variable olarak ayarla)
JAMENDO_CLIENT_ID = os.environ.get("JAMENDO_CLIENT_ID", "")

# Jamendo API base URL
JAMENDO_API_URL = "https://api.jamendo.com/v3.0"

@app.get("/api/search")
async def search_music(query: str = Query(..., description="Arama sorgusu")):
    search_query = unquote(query).strip()
    if not search_query:
        return {"status": "error", "message": "Sorgu boş olamaz.", "data": []}
    
    if not JAMENDO_CLIENT_ID:
        return {"status": "error", "message": "API anahtarı eksik. Lütfen JAMENDO_CLIENT_ID ayarlayın.", "data": []}
    
    try:
        # Jamendo API ile şarkı ara
        # Dökümantasyon: https://developer.jamendo.com/v3.0/tracks
        params = {
            'client_id': JAMENDO_CLIENT_ID,
            'format': 'json',
            'search': search_query,
            'limit': 15,  # Maksimum 15 sonuç
            'order': 'popularity_total',  # Popülerliğe göre sırala
            'include_album_image': 'true'
        }
        
        response = requests.get(f"{JAMENDO_API_URL}/tracks", params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        tracks = []
        for track in data.get('results', []):
            # Jamendo'dan gelen audio linki DOĞRUDAN MP3!
            # 'audio' = stream url, 'audiodownload' = download url
            audio_url = track.get('audio', '')
            download_url = track.get('audiodownload', '')
            
            tracks.append({
                "id": track.get('id', ''),
                "title": track.get('name', 'Bilinmeyen Şarkı'),
                "artist": track.get('artist_name', 'Bilinmeyen Sanatçı'),
                "duration": track.get('duration', 0),
                "coverUrl": track.get('album_image', ''),
                # İKİ SEÇENEK: Dinlemek için audio, indirmek için audiodownload
                "audioUrl": audio_url,  # Dinleme linki
                "downloadUrl": download_url,  # İNDİRME LINKI (MP3!)
                "sourcePlatform": "jamendo"
            })
        
        return {
            "status": "success",
            "count": len(tracks),
            "data": tracks,
            "platform": "jamendo"
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Jamendo API hatası: {e}")
        return {"status": "error", "message": str(e), "data": []}

@app.get("/api/stream")
async def get_stream(track_id: str):
    """
    Jamendo'dan şarkı çalmak için direkt audio URL'sini döndürür
    """
    if not JAMENDO_CLIENT_ID:
        return {"status": "error", "message": "API anahtarı eksik"}, 500
    
    try:
        params = {
            'client_id': JAMENDO_CLIENT_ID,
            'format': 'json',
            'id': track_id
        }
        
        response = requests.get(f"{JAMENDO_API_URL}/tracks", params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('results'):
            track = data['results'][0]
            audio_url = track.get('audio', '')
            if audio_url:
                return {"status": "success", "stream_url": audio_url, "source": "jamendo"}
            else:
                return {"status": "error", "message": "Bu şarkı için ses linki bulunamadı"}, 404
        else:
            return {"status": "error", "message": "Şarkı bulunamadı"}, 404
            
    except Exception as e:
        print(f"Stream hatası: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "api_configured": bool(JAMENDO_CLIENT_ID)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)