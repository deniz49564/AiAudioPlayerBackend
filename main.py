import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

app = FastAPI(title="AiAudioPlayer Backend - OAuth Sürümü")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 OAuth için token dosyasının kaydedileceği güvenli yol
TOKEN_FILE = os.path.join(os.getcwd(), "youtube_oauth_cache.json")

def get_yt_options(is_search=False):
    opts = {
        'format': 'bestaudio/best',
        'quiet': False,  # Logları görebilmek için True yerine False yapıyoruz
        'no_warnings': False,
        # 🌟 OAUTH ENTEGRASYONU: YouTube'a resmi bir TV/Cihaz gibi giriş yapmayı zorlar
        'compat_opts': {'youtube-target-client': 'tv'},
        'extractor_args': {
            'youtube': {
                'oauth': True,
                'cache_file': TOKEN_FILE
            }
        }
    }
    if is_search:
        opts['extract_flat'] = True
    return opts


@app.get("/")
async def root():
    return {"status": "success", "message": "OAuth Sunucusu Aktif!"}


@app.get("/api/search")
async def search_music(query: str = Query(...)):
    try:
        search_url = f"ytsearch15:{query}"
        with YoutubeDL(get_yt_options(is_search=True)) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get('entries', [])
            
            formatted_data = []
            for item in entries:
                v_id = item.get('id')
                if v_id:
                    formatted_data.append({
                        "id": v_id,
                        "title": item.get("title", "Bilinmeyen Şarkı"),
                        "artist": item.get("channel", "Yapay Zeka Sanatçısı"),
                        "sourcePlatform": "YouTube OAuth",
                        "downloadUrl": f"/api/stream?video_id={v_id}",
                        "coverUrl": f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
                        "isDownloading": False
                    })
            return {"status": "success", "count": len(formatted_data), "data": formatted_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arama Hatası: {str(e)}")


@app.get("/api/stream")
async def get_stream_url(video_id: str = Query(...)):
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with YoutubeDL(get_yt_options(is_search=False)) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get('url')
            if not stream_url:
                raise HTTPException(status_code=404, detail="Ses bağlantısı bulunamadı.")
            return {"status": "success", "stream_url": stream_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Akış Hatası: {str(e)}")