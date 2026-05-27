import asyncio
import os
import uuid
import glob
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
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

def cleanup_file(file_path: str):
    """Dosya istemciye tamamen iletildikten sonra çalışacak güvenli temizlik mekanizması"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Geçici dosya başarıyla temizlendi: {file_path}")
    except Exception as e:
        print(f"Temizlik sırasında hata oluştu: {str(e)}")

@app.get("/api/search")
async def search_music(query: str = Query(..., description="Arama sorgusu")):
    search_query = unquote(query).strip()
    if not search_query:
        return {"status": "error", "message": "Sorgu bos olamaz.", "data": []}

    # ✅ DÜZELTİLDİ: SADECE YouTube kullan (SoundCloud yok!)
    ydl_url = f"ytsearch10:{search_query}"

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
            if not entry: 
                continue
            
            track_url = entry.get('webpage_url') or entry.get('url')
            if not track_url:
                continue

            tracks.append({
                "id": entry.get('id', ''),
                "title": entry.get('title', 'Bilinmeyen Sarki'),
                "artist": entry.get('uploader', 'YouTube Music'),
                "duration": int(entry.get('duration', 0)) if entry.get('duration') else 0,
                "coverUrl": entry.get('thumbnail', ''),
                "downloadUrl": f"/api/stream?video_id={track_url}",
                "sourcePlatform": "youtube"
            })
        
        return {"status": "success", "count": len(tracks), "data": tracks}
    
    except Exception as e:
        print(f"Arama hatası: {e}")
        return {"status": "error", "message": str(e), "data": []}

@app.get("/api/stream")
async def get_stream(video_id: str, background_tasks: BackgroundTasks):
    """
    YouTube'dan müzik indir ve gönder
    """
    url = unquote(video_id).strip()
    unique_id = str(uuid.uuid4())
    output_template = os.path.join("/tmp", f"music_{unique_id}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extract_audio': True,
        'audio_format': 'mp3',
        'audio_quality': '192',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        def download_track():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_track)

        # İnen dosyanın tam yolunu tespit ediyoruz
        search_pattern = os.path.join("/tmp", f"music_{unique_id}.*")
        found_files = glob.glob(search_pattern)

        if not found_files:
            raise HTTPException(status_code=500, detail="Dosya indirilemedi.")
        
        actual_file_path = found_files[0]

        if os.path.getsize(actual_file_path) == 0:
            if os.path.exists(actual_file_path): 
                os.remove(actual_file_path)
            raise HTTPException(status_code=500, detail="İndirilen dosya bos.")

        background_tasks.add_task(cleanup_file, actual_file_path)

        # Dosya uzantısını al
        ext = os.path.splitext(actual_file_path)[1]
        if ext == '.webm':
            ext = '.mp3'
        
        return FileResponse(
            path=actual_file_path,
            media_type="audio/mpeg",
            filename=f"music{ext}"
        )

    except Exception as e:
        # Hata durumunda kalan artıkları temizle
        search_pattern = os.path.join("/tmp", f"music_{unique_id}.*")
        for f in glob.glob(search_pattern):
            try: 
                os.remove(f)
            except: 
                pass
        print(f"Stream hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)