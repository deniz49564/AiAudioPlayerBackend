import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

app = FastAPI(title="AiAudioPlayer Backend - SoundCloud Stable Sürümü")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_sc_options(is_search=False):
    """SoundCloud için en hafif ve kararlı yt-dlp konfigürasyonu."""
    opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    if is_search:
        # Arama esnasında ham veriyi hızlıca çekmek için flat kullanıyoruz
        opts['extract_flat'] = True
    return opts

@app.get("/")
async def root():
    return {"status": "success", "message": "SoundCloud Stabil Backend Aktif!"}

@app.get("/api/search")
async def search_music(query: str = Query(...)):
    """🎵 SoundCloud web arayüzü üzerinden kararlı arama yapar."""
    # Arama teriminin sonundaki boşlukları ve enter karakterlerini temizliyoruz
    clean_query = query.strip()
    search_url = f"scsearch15:{clean_query}" 
    
    try:
        with YoutubeDL(get_sc_options(is_search=True)) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get('entries', [])
            
            formatted_data = []
            for item in entries:
                # 🚀 KRİTİK DÜZELTME: api.soundcloud.com yerine doğrudan web url'ini alıyoruz
                # Eğer uploader_url varsa o da geçerli bir web url'idir, yoksa url alanını deniyoruz
                web_url = item.get('webpage_url') or item.get('url')
                v_id = item.get('id')
                
                # Eğer dönen url hala api.soundcloud.com ise, onu yt-dlp'nin çözebileceği standart formata zorlayabiliriz
                if web_url and "api.soundcloud.com" in web_url and v_id:
                    # En garanti web link formatına dönüştürme
                    web_url = f"https://soundcloud.com/tracks/{v_id}"
                
                if web_url:
                    formatted_data.append({
                        "id": web_url,  # Akış ucu artık bu web url'ini doğrudan çözecek
                        "title": item.get("title", "Bilinmeyen Şarkı"),
                        "artist": item.get("uploader", "SoundCloud Sanatçısı"),
                        "sourcePlatform": "SoundCloud Premium",
                        "downloadUrl": f"/api/stream?video_id={web_url}", # Android tarafı etkilenmesin diye parametre adı aynı
                        "coverUrl": "https://picsum.photos/400/400?random=3", 
                        "isDownloading": False
                    })
            return {"status": "success", "count": len(formatted_data), "data": formatted_data}
    except Exception as e:
        print(f"Arama Hatası: {str(e)}")
        raise HTTPException(status_code=500, detail="Müzik araması şu an gerçekleştirilemedi.")

@app.get("/api/stream")
async def get_stream_url(video_id: str = Query(...)):
    """🔊 Web URL'ini alıp ExoPlayer için doğrudan çalınabilir .mp3/.hls linkine dönüştürür."""
    try:
        # Gelen url'i temizle
        target_url = video_id.strip()
        
        with YoutubeDL(get_yt_options_for_stream()) as ydl:
            info = ydl.extract_info(target_url, download=False)
            stream_url = info.get('url')
            
            if not stream_url:
                raise HTTPException(status_code=404, detail="Ses bağlantısı ayrıştırılamadı.")
                
            return {
                "status": "success",
                "stream_url": stream_url
            }
    except Exception as e:
        print(f"Akış Çözme Hatası: {str(e)}")
        raise HTTPException(status_code=500, detail="Müzik akış linki oluşturulamadı.")

def get_yt_options_for_stream():
    return {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        # SoundCloud web linklerini çözerken bota takılmamak için standart tarayıcı taklidi yapıyoruz
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }