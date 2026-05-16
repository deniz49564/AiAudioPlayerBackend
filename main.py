import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# 🚀 KRİTİK: Uvicorn'un bulabilmesi için değişken ismi kesinlikle 'app' olmalı
app = FastAPI(
    title="AiAudioPlayer Backend",
    description="Piped API Entegrasyonlu Premium Müzik Akış Sunucusu"
)

# 🌐 Android uygulamanın sunucuya güvenle bağlanabilmesi için CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme aşamasında tüm kökenlere izin veriyoruz
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🌍 Güvenilir ve yüksek performanslı ana Piped API adresi
PIPED_API_URL = "https://pipedapi.kavin.rocks"

@app.get("/")
async def root():
    """Sunucunun canlı olup olmadığını kontrol etmek için ana ucumuz."""
    return {"status": "success", "message": "AiAudioPlayer Backend tıkır tıkır çalışıyor!"}


@app.get("/api/search")
async def search_music(query: str = Query(..., description="Aranacak şarkı veya sanatçı adı")):
    """
    🎵 AI destekli arama ucu. Piped API üzerinden YouTube sonuçlarını getirir.
    Android tarafındaki 'BackendResponse' şeması ile tam uyumludur.
    """
    try:
        # Piped arama ucuna istek atıyoruz (Sadece müzik/video sonuçları için filtre ekledik)
        search_url = f"{PIPED_API_URL}/search?q={query}&filter=videos"
        response = requests.get(search_url, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Arama servisine şu an erişilemiyor.")
            
        results = response.json().get("items", [])
        formatted_data = []
        
        for item in results:
            # Sadece video tipindeki içerikleri Android'in anlayacağı şemaya dönüştürüyoruz
            if item.get("type") == "stream":
                formatted_data.append({
                    "id": item.get("url", "").split("=")[-1] or item.get("title", "").replace(" ", "_"),
                    "title": item.get("title", "Bilinmeyen Şarkı"),
                    "artist": item.get("uploaderName", "Yapay Zeka Sanatçısı"),
                    "sourcePlatform": "YouTube (via Piped)",
                    # Android tarafındaki 'toAudioModel' extension fonksiyonumuz için 
                    # stream linkini tetikleyecek backend ucunu gömüyoruz
                    "downloadUrl": f"/api/stream?video_id={item.get('url', '').split('=')[-1]}",
                    "coverUrl": item.get("thumbnail", "https://picsum.photos/400/400?random=1"),
                    "isDownloading": False
                })
                
        return {
            "status": "success",
            "count": len(formatted_data),
            "data": formatted_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arama Hatası: {str(e)}")


@app.get("/api/stream")
async def get_stream_url(video_id: str = Query(..., description="YouTube Video ID değeri")):
    """
    🔊 ExoPlayer için ham ses akış (.m4a/.webm) URL'i üreten kritik ucumuz.
    YouTube bot engeline takılmayan Piped altyapısını kullanır.
    """
    try:
        # Piped API'sinden ilgili videonun ham medya linklerini talep ediyoruz
        stream_url = f"{PIPED_API_URL}/streams/{video_id}"
        response = requests.get(stream_url, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Medya sunucusundan yanıt alınamadı.")
            
        data = response.json()
        audio_streams = data.get("audioStreams", [])
        
        if not audio_streams:
            raise HTTPException(status_code=404, detail="Bu video için uygun bir ses akışı bulunamadı.")
            
        # 🌟 ExoPlayer'ın en akıcı çalabileceği en yüksek bitrate'li ses kanalını seçiyoruz
        best_audio = max(audio_streams, key=lambda x: x.get("bitrate", 0))
        
        return {
            "status": "success",
            "stream_url": best_audio.get("url")
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="YouTube veri çekme işlemi zaman aşımına uğradı.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Akış Hatası: {str(e)}")