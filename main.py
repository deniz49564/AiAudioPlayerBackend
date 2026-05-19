import asyncio
import os
import uuid
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
    # 🚀 Kritik Değişiklik: Dosyayı önce ham formatta indirip sonra MP3'e çevireceğiz
    output_path_template = os.path.join("/tmp", f"music_{unique_id}.%(ext)s")
    final_mp3_path = os.path.join("/tmp", f"music_{unique_id}.mp3")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path_template,
        'quiet': True,
        'no_warnings': True,
        # 🚀 SESİ STANDART MP3'E DÖNÜŞTÜRME (Fix for length issue)
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        def download_and_convert():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_and_convert)

        if not os.path.exists(final_mp3_path):
            raise HTTPException(status_code=500, detail="MP3 donusturulemedi.")

        def cleanup():
            if os.path.exists(final_mp3_path):
                os.remove(final_mp3_path)

        return FileResponse(
            path=final_mp3_path,
            media_type="audio/mpeg",
            filename="music.mp3",
            background=asyncio.create_task(asyncio.to_thread(cleanup))
        )

    except Exception as e:
        if os.path.exists(final_mp3_path): os.remove(final_mp3_path)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)