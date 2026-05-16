import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AiAudioPlayer Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 PREMIUM YEDEKLİ SİSTEM: Ana sunucu yanıt vermezse arka arkaya diğerlerini dener.
PIPED_MIRRORS = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.projectsegfaut.space",
    "https://piped-api.garudalinux.org",
    "https://pipedapi.tokhmi.xyz"
]

def safe_get_request(endpoint_path: str):
    """Listede aktif olan ilk çalışan Piped sunucusundan veriyi çeker."""
    for base_url in PIPED_MIRRORS:
        try:
            url = f"{base_url}{endpoint_path}"
            # Render'ı yormamak için timeout süresini 4 saniye tutuyoruz
            response = requests.get(url, timeout=4) 
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Sunucu hatası ({base_url}): {str(e)} - Sonraki deneniyor...")
            continue
    return None


@app.get("/")
async def root():
    return {"status": "success", "message": "Backend Aktif!"}


@app.get("/api/search")
async def search_music(query: str = Query(...)):
    """Yedekli sunucu havuzunu kullanarak arama yapar."""
    try:
        # Sunucu havuzundan güvenli şekilde veriyi talep ediyoruz
        data = safe_get_request(f"/search?q={query}&filter=videos")
        
        if not data:
            raise HTTPException(
                status_code=502, 
                detail="Şu an tüm Piped servisleri yoğun. Lütfen birkaç saniye sonra tekrar deneyin."
            )
            
        results = data.get("items", [])
        formatted_data = []
        
        for item in results:
            if item.get("type") == "stream":
                v_id = item.get("url", "").split("=")[-1]
                if not v_id and "streams/" in item.get("url", ""):
                    v_id = item.get("url", "").split("/")[-1]
                    
                if v_id:
                    formatted_data.append({
                        "id": v_id,
                        "title": item.get("title", "Bilinmeyen Şarkı"),
                        "artist": item.get("uploaderName", "Yapay Zeka Sanatçısı"),
                        "sourcePlatform": "YouTube (via Piped)",
                        "downloadUrl": f"/api/stream?video_id={v_id}",
                        "coverUrl": item.get("thumbnail", "https://picsum.photos/400/400?random=1"),
                        "isDownloading": False
                    })
                
        return {
            "status": "success",
            "count": len(formatted_data),
            "data": formatted_data
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arama Sistem Hatası: {str(e)}")


@app.get("/api/stream")
async def get_stream_url(video_id: str = Query(...)):
    """Yedekli sunucu havuzunu kullanarak ham ses linkini çözer."""
    try:
        data = safe_get_request(f"/streams/{video_id}")
        
        if not data:
            raise HTTPException(
                status_code=502, 
                detail="Müzik bağlantısı şu an çözülemedi, lütfen tekrar deneyin."
            )
            
        audio_streams = data.get("audioStreams", [])
        if not audio_streams:
            raise HTTPException(status_code=404, detail="Ses akışı bulunamadı.")
            
        best_audio = max(audio_streams, key=lambda x: x.get("bitrate", 0))
        
        return {
            "status": "success",
            "stream_url": best_audio.get("url")
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Akış Sistem Hatası: {str(e)}")