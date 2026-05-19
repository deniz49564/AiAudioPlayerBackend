import asyncio
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
from urllib.parse import unquote

app = FastAPI(title="AiAudioPlayer Backend")

# Android cihazlardan ve emülatörlerden erişim için CORS ayarları
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

    if not search_query.startswith("http"):
        ydl_url = f"scsearch5:{search_query}"
    else:
        ydl_url = search_query

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
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
    SoundCloud'un parça parça gönderdiği ses dosyalarını (HLS) sunucu üzerinde 
    birleştirir ve istemciye tek bir ham ses dosyası akışı olarak tüneller.
    """
    url = unquote(video_id).strip()
    
    if not url.startswith("http"):
        url = f"https://soundcloud.com/{url}"

    try:
        # İndirilen byte'ları sunucu diskine yazmadan doğrudan standart çıktıdan (stdout) okuyan jeneratör
        async def stream_from_ytdl():
            # -o - parametresi veriyi doğrudan stdout'a basmasını söyler
            cmd = ["yt-dlp", "-o", "-", "-f", "bestaudio/best", url]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )

            # 64KB'lık tampon bellek blokları halinde veriyi okuyup istemciye gönderiyoruz
            while True:
                chunk = await process.stdout.read(65536)
                if not chunk:
                    break
                yield chunk

            await process.wait()

        # Yanıtı doğrudan ses dosyası formatında maskeleyerek StreamingResponse ile dönüyoruz
        return StreamingResponse(
            stream_from_ytdl(),
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
    uvicorn.run(app, host="0.0.0.0", port=10000)