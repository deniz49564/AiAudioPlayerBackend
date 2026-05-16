import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

app = FastAPI(title="AiAudioPlayer Backend - Kararlı Sürüm")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "success", "message": "Premium Müzik Sunucusu Aktif!"}


@app.get("/api/search")
async def search_music(query: str = Query(...)):
    """
    🎵 yt-dlp'nin YouTube Android istemci simülasyonunu kullanarak 
    çerezsiz ve engelsiz arama yapar.
    """
    # 🚀 En kritik ayar: İstekleri android uygulaması üzerinden maskeliyoruz
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,  # Arama yaparken ham veriyi hızlıca çekmek için
        'extractor_args': {
            'youtube': {
                'clients': ['android', 'ios']  # Bot engelini aşan mobil istemciler
            }
        }
    }
    
    try:
        search_url = f"ytsearch15:{query}" # En alakalı 15 sonucu getirir
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get('entries', [])
            
            formatted_data = []
            for item in entries:
                v_id = item.get('id')
                if v_id:
                    formatted_data.append({
                        "id": v_id,
                        "title": item.get("title", "Bilinmeyen Şarkı"),
                        "artist": item.get("channel", "Yyapay Zeka Sanatçısı"),
                        "sourcePlatform": "YouTube Premium",
                        "downloadUrl": f"/api/stream?video_id={v_id}",
                        "coverUrl": f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg", # Kararlı kapak görseli
                        "isDownloading": False
                    })
                    
            return {
                "status": "success",
                "count": len(formatted_data),
                "data": formatted_data
            }
            
    except Exception as e:
        print(f"Arama Hatası: {str(e)}")
        raise HTTPException(status_code=500, detail="Arama işlemi şu an gerçekleştirilemedi.")


@app.get("/api/stream")
async def get_stream_url(video_id: str = Query(...)):
    """
    🔊 ExoPlayer için engelsiz ham ses URL'ini doğrudan çıkartır.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'clients': ['android', 'ios']  # Akış linkini de mobil istemci üzerinden alıyoruz
            }
        }
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get('url')
            
            if not stream_url:
                raise HTTPException(status_code=404, detail="Ses bağlantısı bulunamadı.")
                
            return {
                "status": "success",
                "stream_url": stream_url
            }
            
    except Exception as e:
        print(f"Akış Hatası: {str(e)}")
        raise HTTPException(status_code=500, detail="Müzik bağlantısı çıkartılamadı.")