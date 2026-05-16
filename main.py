import requests
from fastapi import HTTPException, APIRouter

router = APIRouter()

# 🌍 Güvenilir ve yüksek performanslı ana Piped API adresi
PIPED_API_URL = "https://pipedapi.kavin.rocks"

@router.get("/api/stream")
async def get_stream_url(video_id: str):
    try:
        # 1. Piped API'sine video detayları için istek atıyoruz
        response = requests.get(f"{PIPED_API_URL}/streams/{video_id}", timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=502, 
                detail="Piped API sunucusu şu an yanıt vermiyor, alternatif aranıyor."
            )
            
        data = response.json()
        audio_streams = data.get("audioStreams", [])
        
        if not audio_streams:
            raise HTTPException(
                status_code=404, 
                detail="Bu video için uygun bir ses akışı bulunamadı."
            )
            
        # 2. En yüksek ses kalitesine (bitrate) sahip akışı seçiyoruz
        best_audio = max(audio_streams, key=lambda x: x.get("bitrate", 0))
        
        # 3. ExoPlayer'ın doğrudan oynatabileceği ham URL (.m4a / .webm formatında)
        stream_url = best_audio.get("url")
        
        return {
            "status": "success",
            "stream_url": stream_url
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Piped API istek zaman aşımına uğradı.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backend Hatası: {str(e)}")