import os
import uuid
import subprocess
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

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
    """
    YouTube'da şarkı ara ve sonuçları döndür
    """
    if not query.strip():
        return {"status": "error", "message": "Sorgu boş olamaz.", "data": []}
    
    try:
        # yt-dlp ile JSON formatında arama yap
        cmd = [
            "yt-dlp",
            f"ytsearch10:{query}",
            "--dump-json",
            "--skip-download",
            "--no-warnings"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        tracks = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            import json
            try:
                data = json.loads(line)
                tracks.append({
                    "id": data.get('id', ''),
                    "title": data.get('title', 'Bilinmeyen Şarkı'),
                    "artist": data.get('uploader', 'Bilinmeyen Sanatçı'),
                    "duration": data.get('duration', 0),
                    "coverUrl": data.get('thumbnail', ''),
                    "downloadUrl": f"/api/stream?video_id={data.get('id', '')}",
                    "sourcePlatform": "youtube"
                })
            except:
                continue
        
        return {"status": "success", "count": len(tracks), "data": tracks}
    
    except subprocess.CalledProcessError as e:
        print(f"Arama hatası: {e.stderr}")
        return {"status": "error", "message": str(e.stderr), "data": []}

@app.get("/api/stream")
async def get_stream(video_id: str = Query(..., description="YouTube video ID'si")):
    """
    YouTube videosunu MP3'e dönüştür ve dosya olarak gönder
    """
    unique_id = str(uuid.uuid4())
    output_path = f"/tmp/music_{unique_id}.mp3"
    
    try:
        # yt-dlp ile MP3 indir
        cmd = [
            "yt-dlp",
            "-x",  # Ses çıkart
            "--audio-format", "mp3",
            "--audio-quality", "2",
            "-o", output_path,
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise HTTPException(status_code=500, detail="Dosya oluşturulamadı.")
        
        # Dosyayı gönder ve işlem sonrası silinmesini planla
        response = FileResponse(
            path=output_path,
            media_type="audio/mpeg",
            filename=f"music_{video_id}.mp3"
        )
        
        # Dosyayı gönderdikten sonra sil
        def cleanup():
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except:
                pass
        
        response.background = cleanup
        return response
    
    except subprocess.CalledProcessError as e:
        print(f"Stream hatası: {e.stderr}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=str(e.stderr))

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)