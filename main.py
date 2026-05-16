from fastapi import FastAPI, HTTPException, Query
import yt_dlp
import os

app = FastAPI(title="AiAudioPlayer Premium AI Backend")

# EMNİYET KİLİDİ: Eğer Render sunucusunda eski 'cookies.txt' kalmışsa zorla temizle
if os.path.exists("cookies.txt"):
    try:
        os.remove("cookies.txt")
        print("--> SYSTEM: Eski bozuk cookies.txt dosyası diskten tamamen silindi.")
    except Exception as e:
        print(f"--> SYSTEM: cookies.txt silinirken hata: {e}")

# Tarayıcıdan getirdiğin çerez havuzu
YT_COOKIE = (
    "_Secure-BUCKET=CLMB; VISITOR_INFO1_LIVE=8yWHsmdcEao; VISITOR_PRIVACY_METADATA=CgJUUhIEGgAgQg%3D%3D; "
    "__Secure-3PAPISID=SLzgrhVDJ4IJoWw_/A4rMC3ddomwxvMfhY; "
    "__Secure-3PSID=g.a0009Ag40I8M2ZXnDU1ERRsznH_7ZXM0ODUAS8dHf9TNkPYTZcECJiCWcFIp6wJ5DzyXuamhwgACgYKAaYSARYSFQHGX2MiDr1NG5EVktncB_z_laPzrxoVAUF8yKrTwwy_wwVF7N1rcb_AN_P00076; "
    "LOGIN_INFO=AFmmF2swRAIgEv2p2_qZlZnfFlKqQGD1JAy3NlQ4ROFwjxkvBt3r7uQCIB_sQqVh7MqVwPmAhKBv0FnZ8lI4HHZyNltmV78y-l34:QUQ3MjNmd0R6VDEzaTVXWVZnYUhxYzRybWg5M0VsVl9kbFJHRnJhaHdWSVdEOG5MckZ6eVJNY3NnOURvcTBXaWpKeDRHZ3JnRUwwV29WRF80eGVIbk01dnVLQ3N2a2V5THdoQ0VuRFhFUlFzN1czUkEzdFZxaFNJSjJWV3hMcHd3VWx4TWZYcEpLWWdvSTQ4RDA4eGJVbWdyNG9LbDd3ZGNR; "
    "PREF=f4=4000000&tz=Europe.Istanbul; "
    "__Secure-YNID=18.YT=ifhEjKvJEm2ZyuSN-6eL9r8Amde4PsFzBFv2wNcPvvt7jbF5O7Xjxoqx_q-vW-am6uRGW-NDfqTI0RTHeymy-f8wX2XYor2H5As8H51Y_dhrBzmtuLxq4grPQ1h_bYB6hfG3ZsRSBEm3jjBRfq7eIERXthX6i6ci4DRtuPmuAXbagtZXOvO3j3l0zoI7KMiDfa_MDcJRN3VF4l4EmxkxFR__PuWM4_8Hw2Kzq6MR3wmf7F2u8HX-emAvQunTX2nqL9k_DAw-8PN3P2tPHBQbdSrTBMqRMsh5owl1GpR6jBzpMRz4R5wgYIv56jUIUlSeBkwegvWj4B_PJa2hEsObdA; "
    "YSC=7u42lJAxJ-g; __Secure-ROLLOUT_TOKEN=CLm9-8GM7qOT6QEQjY6_6Pb0kwMY6oPnm9W-lAM%3D; "
    "__Secure-1PSIDTS=sidts-CjUBhkeRd7_62jHdgOTNRbCaUbicC8wskOP3uvvyVw0rrBYJytQALra3fk78-lh7RlgEYboTSxAA; "
    "__Secure-3PSIDTS=sidts-CjUBhkeRd7_62jHdgOTNRbCaUbicC8wskOP3uvvyVw0rrBYJytQALra3fk78-lh7RlgEYboTSxAA; "
    "__Secure-3PSIDCC=AKEyXzXaWeNW3RmKmPSmQfchWrhvdobw6z2Jx3X4mwxshmKGhjCtkm4Rkei81mgA4w_uTJS586c"
)

YT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

@app.get("/api/search")
async def search_music(query: str = Query(..., description="Aranacak müzik veya AI promptu")):
    # URL'den gelebilecek olası boşluk ve satır başı karakterlerini temizle
    clean_query = query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Arama sorgusu boş olamaz.")

    # İmza (Signature) hatalarını aşmak için 'extract_flat': True moduna geçiyoruz
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': True,  # KRİTİK: Videonun içine girmeden listeden veriyi hızlıca çeker, imza hatası vermez.
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'http_headers': {
            'User-Agent': YT_USER_AGENT,
            'Cookie': YT_COOKIE,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8',
        }
    }

    results = []
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"--> INFO: '{clean_query}' araması hafifletilmiş düz tarama modu ile tetikleniyor...")
            search_results = ydl.extract_info(f"ytsearch3:{clean_query}", download=False)
            
            if search_results and 'entries' in search_results:
                for entry in search_results['entries']:
                    if not entry:
                        continue
                    
                    video_id = entry.get("id") or entry.get("url")
                    if not video_id:
                        continue
                        
                    # YouTube standart izleme veya doğrudan video linki kurgusu
                    fallback_url = f"https://www.youtube.com/watch?v={video_id}" if not str(video_id).startswith("http") else video_id
                    
                    results.append({
                        "id": video_id,
                        "title": entry.get("title") or entry.get("name") or "Bilinmeyen Şarkı",
                        "artist": entry.get("uploader") or entry.get("channel") or "AI Artist",
                        "sourcePlatform": "YouTube/AI Cloud",
                        "downloadUrl": fallback_url, 
                        "coverUrl": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                        "isDownloading": False
                    })
                    
        print(f"--> SUCCESS: Hafif tarama moduyla {len(results)} sonuç başarıyla paketlendi.")
        return {"status": "success", "count": len(results), "data": results}

    except Exception as e:
        print(f"--> CRITICAL: Tarama esnasında hata: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Müzik kaynakları taranırken hata oluştu. Hata: {str(e)}"
        )