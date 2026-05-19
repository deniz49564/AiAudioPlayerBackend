import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import httpx
from urllib.parse import unquote

app = FastAPI(title="AiAudioPlayer Backend")

# Android simülatörden veya gerçek cihazdan erişim için CORS izinlerini esnek tutuyoruz
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/search")
async def search_music(query: str = Query(..., description="Arama sorgusu veya SoundCloud URL'i")):
    """
    Kullanıcının yazdığı kelimeye göre SoundCloud üzerinde arama yapar ve sonuç listesini döner.
    """
    search_query = unquote(query).strip()
    if not search_query:
        return {"status": "error", "message": "Sorgu boş olamaz.", "data": []}

    # Eğer gelen girdi doğrudan bir link değilse SoundCloud'da ara
    if not search_query.startswith("http"):
        ydl_url = f"scsearch5:{search_query}"
    else:
        ydl_url = search_query

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',  # Arama işlemini hızlandırmak için flat tutuyoruz
    }

    try:
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(ydl_url, download=False)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, extract)

        tracks = []
        if 'entries' in result:
            entries = result['entries']
        else:
            entries = [result]

        for entry in entries:
            if not entry:
                continue
            
            # downloadUrl alanına Android'in tekrar istek atabilmesi için web url'ini veya id'sini gömüyoruz
            track_url = entry.get('webpage_url') or entry.get('url')
            if not track_url:
                continue

            tracks.append({
                "id": entry.get('id', ''),
                "title": entry.get('title', 'Bilinmeyen Şarkı'),
                "artist": entry.get('uploader', 'Bilinmeyen Sanatçı'),
                "duration": int(entry.get('duration', 0)) if entry.get('duration') else 0,
                "coverUrl": entry.get('thumbnail', ''),
                "downloadUrl": f"/api/stream?video_id={track_url}"
            })

        return {"status": "success", "data": tracks}

    except Exception as e:
        return {"status": "error", "message": f"Arama hatası: {str(e)}", "data": []}


@app.get("/api/stream")
async def get_stream(video_id: str = Query(..., description="Çözülecek parçanın tam URL'i veya ID'si")):
    """
    🚀 KESİN ÇÖZÜM: SoundCloud akış linkini yakalar, veriyi sunucu üzerinden proxy yaparak 
    Android'e ham ve saf bir MP3 dosyası akışı olarak fırlatır.
    """
    url = unquote(video_id).strip()
    
    # Eğer parametre tam URL değilse, API linki olma ihtimaline karşı güvenliğe alıyoruz
    if not url.startswith("http"):
        # Eğer sistemine sadece ID paslıyorsan burayı kendi formatına göre uyarlayabilirsin
        url = f"https://soundcloud.com/{url}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        # Render sunucusunun tıkanmaması için yt-dlp ağ operasyonunu asenkron çalıştırıyoruz
        def run_ytdl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('url')

        loop = asyncio.get_event_loop()
        real_stream_url = await loop.run_in_executor(None, run_ytdl)

        if not real_stream_url:
            raise HTTPException(status_code=400, detail="Müzik akış adresi ayrıştırılamadı.")

        # SoundCloud'un bot korumalarını aşmak için kullanılan HTTP başlıkları
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        # Şarkının byte'larını parçalar halinde okuyup Android'e canlı pompalayan jeneratör
        async def music_stream_generator():
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("GET", real_stream_url, headers=headers) as response:
                    if response.status_code != 200:
                        yield b""
                        return
                    async remove_chunk in response.aiter_bytes(chunk_size=16384): # 16KB parçalarla hızlı aktarım
                        yield remove_chunk

        # Android tarafına doğrudan dosya indiriyormuş hissi veren StreamingResponse yapısı
        return StreamingResponse(
            music_stream_generator(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=music.mp3",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    except Exception as e:
        print(f"Akış Hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Akış Çözme Hatası: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Render varsayılan olarak 10000 portunu bağlar
    uvicorn.run(app, host="0.0.0.0", port=10000)