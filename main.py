from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI(title="AiAudioPlayer Premium AI Backend")

@app.get("/api/search")
async def search_music(query: str = Query(..., description="Aranacak müzik veya AI promptu")):
    """
    Kullanıcının girdiği promptu alır, arkada YouTube/SoundCloud üzerinden
    en uygun sonuçları tarar ve Android uygulamasının doğrudan oynatabileceği 
    akış (stream) linkleriyle birlikte temiz bir JSON döner.
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Arama sorgusu boş olamaz.")

    # yt-dlp ayarları: Sadece ses linklerini ayıkla, hızlı tara
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'extract_flat': False,
    }

    results = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Kullanıcının promptunun başına 'ytsearch3:' ekleyerek en popüler 3 sonucu aratıyoruz
            search_results = ydl.extract_info(f"ytsearch3:{query}", download=False)
            
            if 'entries' in search_results:
                for entry in search_results['entries']:
                    if not entry:
                        continue
                        
                    # Android uygulamasının beklediği SearchResultModel yapısına birebir uyumlu şema
                    results.append({
                        "id": entry.get("id", ""),
                        "title": entry.get("title", "Bilinmeyen Şarkı"),
                        "artist": entry.get("uploader", "AI Artist"),
                        "sourcePlatform": "YouTube/AI Cloud",
                        "downloadUrl": entry.get("url", ""), # Doğrudan ExoPlayer'ın oynatacağı ses akış linki
                        "coverUrl": f"https://img.youtube.com/vi/{entry.get('id')}/hqdefault.jpg", # Dinamik albüm kapağı
                        "isDownloading": False
                    })
                    
        return {"status": "success", "count": len(results), "data": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI kaynakları taranırken hata oluştu: {str(e)}")

# Sunucuyu yerelde test etmek için terminalden: uvicorn main:app --reload