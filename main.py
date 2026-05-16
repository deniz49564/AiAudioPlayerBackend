from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os

app = FastAPI(title="AiAudioPlayer Premium AI Backend")

# İndirilen MP3'lerin tutulacağı klasör
MEDIA_DIR = "downloads"
os.makedirs(MEDIA_DIR, exist_ok=True)

# Sunucuda biriken eski çerez dosyasını temizle
if os.path.exists("cookies.txt"):
    try: os.remove("cookies.txt")
    except: pass

YT_COOKIE = (
    "_Secure-BUCKET=CLMB; VISITOR_INFO1_LIVE=8yWHsmdcEao; VISITOR_PRIVACY_METADATA=CgJUUhIEGgAgQg%3D%3D; "
    "__Secure-3PAPISID=SLzgrhVDJ4IJoWw_/A4rMC3ddomwxvMfhY; "
    "__Secure-3PSID=g.a0009Ag40I8M2ZXnDU1ERRsznH_7ZXM0ODUAS8dHf9TNkPYTZcECJiCWcFIp6wJ5DzyXuamhwgACgYKAaYSARYSFQHGX2MiDr1NG5EVktncB_z_laPzrxoVAUF8yKrTwwy_wwVF7N1rcb_AN_P00076; "
    "LOGIN_INFO=AFmmF2swRAIgEv2p2_qZlZnfFlKqQGD1JAy3NlQ4ROFwjxkvBt3r7uQCIB_sQqVh7MqVwPmAhKBv0FnZ8lI4HHZyNltmV78y-l34:QUQ3MjNmd0R6VDEzaTVXWVZnYUhxYzRybWg5M0VsVl9kbFJHRnJhaHdWSVdEOG5MckZ6eVJNY3NnOURvcTBXaWpKeDRHZ3JnRUwwV29WRF80eGVIbk01dnVLQ3N2a2V5THdoQ0VuRFhFUlFzN1czUkEzdFZxaFNJSjJWV3hMcHd3VWx4TWZYcEpLWWdvSTQ4RDA4eGJVbWdyNG9LbDd3ZGNR; "
    "PREF=f4=4000000&tz=Europe.Istanbul; "
    "YSC=7u42lJAxJ-g; __Secure-ROLLOUT_TOKEN=CLm9-8GM7qOT6QEQjY6_6Pb0kwMY6oPnm9W-lAM%3D;"
)
YT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

@app.get("/api/search")
async def search_music(query: str = Query(..., description="Aranacak müzik sorgusu")):
    clean_query = query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Arama sorgusu boş olamaz.")

    # Arama esnasında hata almamak için imza çözmeyen ultra hızlı moda geçiyoruz
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'http_headers': {
            'User-Agent': YT_USER_AGENT,
            'Cookie': YT_COOKIE
        }
    }

    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch3:{clean_query}", download=False)
            
            if search_results and 'entries' in search_results:
                for entry in search_results['entries']:
                    if not entry: continue
                    video_id = entry.get("id")
                    if not video_id: continue
                    
                    # 🚀 KRİTİK DEĞİŞİKLİK: Download ve akış linkini doğrudan kendi sunucumuza bağlıyoruz!
                    # Render URL'niz neyse Android buraya istek atacak, sunucu arka planda MP3 basacak.
                    local_stream_url = f"/api/stream?video_id={video_id}"
                    
                    results.append({
                        "id": video_id,
                        "title": entry.get("title") or "Bilinmeyen Şarkı",
                        "artist": entry.get("uploader") or "AI Artist",
                        "sourcePlatform": "YouTube/AI Cloud",
                        "downloadUrl": local_stream_url, 
                        "coverUrl": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                        "isDownloading": False
                    })
                    
        return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stream")
async def stream_or_download(video_id: str = Query(..., description="YouTube Video ID")):
    """
    Hem ExoPlayer hem indirme yöneticisi bu uca tetik atar. 
    Sunucu dosyayı indirir, FFmpeg ile saf MP3 yapar ve temiz dosya teslim eder.
    """
    mp3_file_path = os.path.join(MEDIA_DIR, f"{video_id}.mp3")
    
    # Eğer bu şarkı sunucuda daha önce dönüştürüldüyse saniyeler içinde doğrudan teslim et (Önbellek)
    if os.path.exists(mp3_file_path):
        return FileResponse(path=mp3_file_path, media_type='audio/mpeg', filename=f"{video_id}.mp3")
    
    # Yoksa YouTube'dan çek ve FFmpeg ile MP3'e çevir
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(MEDIA_DIR, f"{video_id}.%(ext)s"),
        'quiet': True,
        'nocheckcertificate': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'http_headers': {
            'User-Agent': YT_USER_AGENT,
            'Cookie': YT_COOKIE
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            
        if os.path.exists(mp3_file_path):
            return FileResponse(path=mp3_file_path, media_type='audio/mpeg', filename=f"{video_id}.mp3")
        else:
            raise HTTPException(status_code=500, detail="Dönüşüm başarısız oldu.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sunucu hatası: {str(e)}")