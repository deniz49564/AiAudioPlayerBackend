import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL

app = FastAPI(
    title="AiAudioPlayer Backend - Premium OAuth Edition",
    description="YouTube Bot Engeline Karşı OAuth2 Korumalı Müzik Sunucusu"
)

# 🌐 Android uygulamanın sunucuya güvenle bağlanabilmesi için CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🚀 OAuth için token dosyasının kaydedileceği güvenli yol (Render diskinde saklanır)
TOKEN_FILE = os.path.join(os.getcwd(), "youtube_oauth_cache.json")

def get_yt_options(is_search=False):
    """yt-dlp kütüphanesini Akıllı TV gibi maskeleyen ve OAuth zorlayan konfigürasyon."""
    opts = {
        'format': 'bestaudio/best',
        'quiet': False,        # Render loglarında doğrulama kodunu görebilmek için False olmalı
        'no_warnings': False,
        'interactive': False,  # Arka planda kilitlenmeyi önler, kodu loga basıp işleme devam eder
        
        # 🌟 OAUTH VE TV İSTEMCİSİ ZORLAMASI
        'compat_opts': {
            'youtube-target-client': 'tv'
        },
        'extractor_args': {
            'youtube': {
                'oauth': True,       # OAuth mekanizmasını aktif et
                'cache_file': TOKEN_FILE
            }
        }
    }
    if is_search:
        opts['extract_flat'] = True
    return opts


@app.get("/")
async def root():
    """Sunucu durumunu kontrol etmek için ana ucumuz."""
    oauth_status = "Aktif (Token Mevcut)" if os.path.exists(TOKEN_FILE) else "Beklemede (İlk istekte kod üretecek)"
    return {
        "status": "success", 
        "message": "AiAudioPlayer Backend Aktif!",
        "oauth_integration": oauth_status
    }


@app.get("/api/search")
async def search_music(query: str = Query(..., description="Aranacak şarkı adı")):
    """
    🎵 Kararlı Arama Ucu. 
    YouTube TV API'sini kullanarak çerezsiz arama sonuçlarını listeler.
    """
    search_url = f"ytsearch15:{query}" # En alakalı 15 sonucu getirir
    
    try:
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
                        "sourcePlatform": "YouTube Premium (OAuth)",
                        "downloadUrl": f"/api/stream?video_id={v_id}",
                        "coverUrl": f"https://img.youtube.com/vi/{v_id}/hqdefault.jpg",
                        "isDownloading": False
                    })
                    
            return {
                "status": "success",
                "count": len(formatted_data),
                "data": formatted_data
            }
            
    except Exception as e:
        print(f"Arama Sistem Hatası: {str(e)}")
        raise HTTPException(status_code=500, detail="Arama işlem şu an gerçekleştirilemedi.")


@app.get("/api/stream")
async def get_stream_url(video_id: str = Query(..., description="YouTube Video ID değeri")):
    """
    🔊 Kararlı Akış Ucu. 
    ExoPlayer için bot engeline takılmayan ham ses linkini çıkartır.
    """
    # 🚀 %100 ÇÖZÜM: Hem urllib'in hem de yt-dlp'nin resmi olarak tanıdığı mobil kısa link yapısı
    video_url = f"https://youtu.be/{video_id}"
    
    try:
        with YoutubeDL(get_yt_options(is_search=False)) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info.get('url')
            
            if not stream_url:
                raise HTTPException(status_code=404, detail="Ses bağlantısı bulunamadı.")
                
            return {
                "status": "success",
                "stream_url": stream_url
            }
            
    except Exception as e:
        print(f"Akış Sistem Hatası: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Müzik bağlantısı çıkartılamadı. Render loglarından cihaz onayını kontrol edin."
        )