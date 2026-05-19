import asyncio
import os
import uuid
import glob
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
from urllib.parse import unquote

app = FastAPI(title="AiAudioPlayer Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/search")
async def search_music(query: str = Query(..., description="Arama sorgusu")):
    search_query = unquote(query).strip()
    if not search_query:
        return {"status": "error", "message": "Sorgu bos olamaz.", "data": []}

    ydl_url = f"scsearch5:{search_query}" if not search_query.startswith("http") else search_query

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
        entries = result.get('entries', [result]) if result else []

        for entry in entries:
            if not entry: continue
            track_url = entry.get('webpage_url') or entry.get('url')
            if not track_url: continue

            tracks.append({
                "id": entry.get('id', ''),
                "title": entry.get('title', 'Bilinmeyen Sarki'),
                "artist": entry.get('uploader', 'Bilinmeyen Sanatci'),
                "duration": int(entry.get('duration', 0)) if entry.get('duration') else 0,
                "coverUrl": entry.get('thumbnail', ''),
                "downloadUrl": f"/api/stream?video_id={track_url}"
            })
        return {"status": "success", "data": tracks}
    except Exception as e:
        return {"status": "error", "message": str(e), "data": []}

@app.get("/api/stream")
async def get_stream(video_id: str = Query(...)):
    url = unquote(video_id).strip()
    unique_id = str(uuid.uuid4())
    
    # 🚀 FFmpeg gerektiren postprocessor'ları sildik. 
    # Dosya hangi uzantıyla iniyorsa (.m4a, .webm vb.) öyle kaydedilecek.
    output_template = os.path.join("/tmp", f"music_{unique_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }

    try:
        def download_track():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_track)

        # 🚀 Sunucuya inen dosyanın gerçek uzantısını ve yolunu buluyoruz
        search_pattern = os.path.join("/tmp", f"music_{unique_id}.*")
        found_files = glob.glob(search_pattern)

        if not found_files:
            raise HTTPException(status_code=500, detail="Dosya sunucu diskine indirilemedi.")
        
        # İnen gerçek dosyanın tam yolu (Örn: /tmp/music_xyz.m4a)
        actual_file_path = found_files[0]

        # Dosya boş mu kontrolü
        if os.path.getsize(actual_file_path) == 0:
            if os.path.exists(actual_file_path): os.remove(actual_file_path)
            raise HTTPException(status_code=500, detail="İndirilen dosya bos (0 byte).")

        # Gönderim bittikten sonra diski temizleme görevi
        def cleanup():
            if os.path.exists(actual_file_path):
                os.remove(actual_file_path)

        # Android cihazın dosyayı müzik olarak tanıması için uygun MIME tipini ayarlıyoruz
        # M4A veya MP3 olabileceği için genel 'audio/mpeg' veya 'audio/mp4' yerine ses olduğunu belirtmek yeterli
        return FileResponse(
            path=actual_file_path,
            media_type="audio/any",
            filename=f"music{os.path.splitext(actual_file_path)[1]}", # Orijinal uzantısıyla gönderir (.m4a gibi)
            background=asyncio.create_task(asyncio.to_thread(cleanup))
        )

    except Exception as e:
        # Hata durumunda kalan çöp dosyaları temizle
        search_pattern = os.path.join("/tmp", f"music_{unique_id}.*")
        for f in glob.glob(search_pattern):
            try: os.remove(f)
            except: pass
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)