from fastapi import FastAPI, HTTPException, Query
import yt_dlp
import os

app = FastAPI(title="AiAudioPlayer Premium AI Backend")

@app.get("/api/search")
async def search_music(query: str = Query(..., description="Aranacak müzik veya AI promptu")):
    """
    Kullanıcının girdiği promptu alır, arkada YouTube üzerinden
    en uygun sonuçları tarar ve Android uygulamasının doğrudan oynatabileceği 
    akış (stream) linkleriyle birlikte temiz bir JSON döner.
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Arama sorgusu boş olamaz.")

    # COOKIE KONTROLÜ: Projenin ana dizininde cookies.txt var mı kontrol et
    cookie_path = "cookies.txt"
    
    # yt-dlp temel konfigürasyon ayarları
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'extract_flat': False,
        # YouTube'un imza çözme (signature deciphering) işlemlerini hızlandırmak ve uyumluluğu artırmak için:
        'nocheckcertificate': True,
        'ignoreerrors': True, 
    }

    # Eğer cookies.txt dosyası sunucuda mevcutsa ayarlara enjekte et
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
        print("--> SUCCESS: cookies.txt bulundu ve yt-dlp sistemine entegre edildi.")
    else:
        print("--> WARNING: cookies.txt bulunamadı! İstekler anonim (IP tabanlı) gönderiliyor.")

    results = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Kullanıcının arama sorgusunun başına 'ytsearch3:' koyarak aratıyoruz
            search_results = ydl.extract_info(f"ytsearch3:{query}", download=False)
            
            if search_results and 'entries' in search_results:
                for entry in search_results['entries']:
                    if not entry:
                        continue
                    
                    # yt-dlp bazen doğrudan akış (stream) url'ini vermezse orijinal video linkini fallback yapalım
                    stream_url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                        
                    results.append({
                        "id": entry.get("id", ""),
                        "title": entry.get("title", "Bilinmeyen Şarkı"),
                        "artist": entry.get("uploader", "AI Artist"),
                        "sourcePlatform": "YouTube/AI Cloud",
                        "downloadUrl": stream_url, 
                        "coverUrl": f"https://img.youtube.com/vi/{entry.get('id')}/hqdefault.jpg",
                        "isDownloading": False
                    })
                    
        return {"status": "success", "count": len(results), "data": results}

    except Exception as e:
        # Sunucu tamamen çökmesin (HTTP 500 vermesin), en azından boş liste veya anlamlı bir log dönsün
        print(f"yt-dlp tarama hatası: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"YouTube bot filtresine takıldı veya kaynak tükenmesi oluştu. Lütfen çerezleri güncelleyin. Hata: {str(e)}"
        )