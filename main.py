import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

app = FastAPI(title="AiAudioPlayer Backend - SoundCloud Sürümü")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_sc_options(is_search=False):
    opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    if is_search:
        opts['extract_flat'] = True
    return opts

@app.get("/")
async def root():
    return {"status": "success", "message": "SoundCloud Destekli Backend Aktif!"}

@app.get("/api/search")
async def search_music(query: str = Query(...)):
    """🎵 SoundCloud üzerinden telifsiz/engelsiz arama yapar."""
    # scsearchb: SoundCloud arama şemasıdır
    search_url = f"scsearch15:{query}" 
    try:
        with YoutubeDL(get_sc_options(is_search=True)) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get('entries', [])
            
            formatted_data = []
            for item in entries:
                # SoundCloud url'ini id olarak kullanıyoruz veya temizliyoruz
                sc_url = item.get('url')
                if sc_url:
                    formatted_data.append({
                        "id": sc_url, # Akış için doğrudan URL'i saklıyoruz
                        "title": item.get("title", "Bilinmeyen Şarkı"),
                        "artist": item.get("uploader", "SoundCloud Sanatçısı"),
                        "sourcePlatform": "SoundCloud",
                        "downloadUrl": f"/api/stream?video_id={sc_url}", # Android tarafı bozulmasın diye parametre adını koruduk
                        "coverUrl": "https://picsum.photos/400/400?random=2", # SoundCloud kapak şeması
                        "isDownloading": False
                    })
            return {"status": "success", "count": len(formatted_data), "data": formatted_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arama Hatası: {str(e)}")

@app.get("/api/stream")
async def get_stream_url(video_id: str = Query(...)):
    """🔊 ExoPlayer için ham SoundCloud ses linkini çıkartır (Bot engeli yoktur)."""
    try:
        with YoutubeDL(get_sc_options(is_search=False)) as ydl:
            info = ydl.extract_info(video_id, download=False)
            stream_url = info.get('url')
            if not stream_url:
                raise HTTPException(status_code=404, detail="Ses bağlantısı bulunamadı.")
            return {"status": "success", "stream_url": stream_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Akış Hatası: {str(e)}")