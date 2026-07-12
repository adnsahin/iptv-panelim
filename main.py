from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import os
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== AYARLAR ====================
JSONBIN_ID  = "6a530100f5f4af5e2982c769"
JSONBIN_KEY = "$2a$10$mEKH6YEVi.0L4O2UFuU8LuP4e5MDauKOM/N09qQn.Wdfjb8NnOzhq"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"

# ==================== FONKSİYONLAR ====================
def veri_oku():
    try:
        url  = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest"
        resp = requests.get(
            url,
            headers={
                "X-Master-Key": JSONBIN_KEY,
                "X-Bin-Meta":   "false"
            },
            timeout=10
        )
        print(f"OKUMA STATUS: {resp.status_code}")
        print(f"OKUMA YANIT: {resp.text[:300]}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                if "record" in data:
                    return data["record"]
                if "playlists" in data:
                    return data
        return {"playlists": [], "m3u_url": ""}
    except Exception as e:
        print(f"OKUMA HATASI: {e}")
        return {"playlists": [], "m3u_url": ""}

def veri_kaydet(data):
    try:
        resp = requests.put(
            JSONBIN_URL,
            headers={
                "X-Master-Key": JSONBIN_KEY,
                "Content-Type": "application/json"
            },
            json=data,
            timeout=10
        )
        print(f"KAYIT SONUCU: {resp.status_code} - {resp.text[:200]}")
        return resp.status_code == 200
    except Exception as e:
        print(f"KAYIT HATASI: {e}")
        return False

def m3u_getir(url):
    try:
        r = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        return r.text
    except Exception as e:
        return f"#EXTM3U\n#EXTINF:-1,Hata: {str(e)}\nhttp://localhost"

# ==================== TV ENDPOİNTLERİ ====================
@app.get("/get", response_class=PlainTextResponse)
def playlist_getir():
    data    = veri_oku()
    m3u_url = data.get("m3u_url", "")
    if not m3u_url:
        return "#EXTM3U\n#EXTINF:-1,Henuz playlist eklenmedi\nhttp://localhost"
    return m3u_getir(m3u_url)

@app.get("/get/{index}", response_class=PlainTextResponse)
def playlist_getir_index(index: int):
    data      = veri_oku()
    playlists = data.get("playlists", [])
    if not playlists:
        return "#EXTM3U\n#EXTINF:-1,Henuz playlist eklenmedi\nhttp://localhost"
    if index < 0 or index >= len(playlists):
        return f"#EXTM3U\n#EXTINF:-1,Gecersiz index ({index})\nhttp://localhost"
    return m3u_getir(playlists[index]["url"])

# ==================== API ====================
@app.get("/api/data")
def api_veri():
    return veri_oku()

@app.get("/api/links")
def api_links():
    data      = veri_oku()
    playlists = data.get("playlists", [])
    base_url  = "https://iptv-panelim.onrender.com"
    linkler   = []
    for i, p in enumerate(playlists):
        linkler.append({
            "index":   i,
            "isim":    p["isim"],
            "tv_link": f"{base_url}/get/{i}",
            "tarih":   p.get("tarih", "")
        })
    return {
        "aktif_link": f"{base_url}/get",
        "linkler":    linkler
    }

@app.get("/api/debug")
def api_debug():
    sonuc = {
        "jsonbin_id":  JSONBIN_ID[:8] + "..." if JSONBIN_ID else "BOS",
        "jsonbin_key": JSONBIN_KEY[:8] + "..." if JSONBIN_KEY else "BOS",
    }
    try:
        url  = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest"
        resp = requests.get(
            url,
            headers={
                "X-Master-Key": JSONBIN_KEY,
                "X-Bin-Meta":   "false"
            },
            timeout=10
        )
        sonuc["jsonbin_status"] = resp.status_code
        sonuc["jsonbin_yanit"]  = resp.text[:300]
    except Exception as e:
        sonuc["jsonbin_hata"] = str(e)
    return sonuc

@app.post("/api/ekle")
def api_ekle(body: dict):
    isim = body.get("isim", "").strip()
    url  = body.get("url",  "").strip()
    if not url.startswith("http"):
        return JSONResponse({"hata": "Gecersiz link"}, status_code=400)
    if not isim:
        return JSONResponse({"hata": "Isim bos olamaz"}, status_code=400)
    data      = veri_oku()
    playlists = data.get("playlists", [])
    if len(playlists) >= 50:
        return JSONResponse({"hata": "Maksimum 50 playlist eklenebilir"}, status_code=400)
    playlists.append({
        "isim":  isim,
        "url":   url,
        "tarih": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    if not data.get("m3u_url"):
        data["m3u_url"] = url
    data["playlists"] = playlists
    basari = veri_kaydet(data)
    return {"durum": "ok" if basari else "hata"}

@app.post("/api/aktif/{index}")
def api_aktif(index: int):
    data      = veri_oku()
    playlists = data.get("playlists", [])
    if 0 <= index < len(playlists):
        data["m3u_url"] = playlists[index]["url"]
        veri_kaydet(data)
    return {"durum": "ok"}

@app.post("/api/sil/{index}")
def api_sil(index: int):
    data      = veri_oku()
    playlists = data.get("playlists", [])
    if 0 <= index < len(playlists):
        silinen = playlists.pop(index)
        if data.get("m3u_url") == silinen["url"]:
            data["m3u_url"] = playlists[0]["url"] if playlists else ""
        data["playlists"] = playlists
        veri_kaydet(data)
    return {"durum": "ok"}

@app.post("/api/duzenle/{index}")
def api_duzenle(index: int, body: dict):
    isim = body.get("isim", "").strip()
    url  = body.get("url",  "").strip()
    data      = veri_oku()
    playlists = data.get("playlists", [])
    if 0 <= index < len(playlists):
        if isim:
            playlists[index]["isim"] = isim
        if url.startswith("http"):
            eski_url = playlists[index]["url"]
            playlists[index]["url"] = url
            if data.get("m3u_url") == eski_url:
                data["m3u_url"] = url
        data["playlists"] = playlists
        veri_kaydet(data)
    return {"durum": "ok"}

# ==================== WEB PANELİ ====================
@app.get("/", response_class=HTMLResponse)
def panel():
    return r"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IPTV Panelim</title>
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }

            body {
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
                min-height: 100vh;
                color: #fff;
                padding: 20px;
            }

            .container { max-width: 800px; margin: 0 auto; }

            h1 {
                text-align: center;
                font-size: 2.2em;
                margin: 30px 0 10px;
                background: linear-gradient(90deg, #00d2ff, #3a7bd5);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .subtitle { text-align:center; color:#888; margin-bottom:30px; font-size:0.95em; }

            .durum {
                text-align: center;
                padding: 12px;
                border-radius: 10px;
                margin-bottom: 25px;
                font-weight: bold;
                border: 1px solid;
                background: rgba(0,0,0,0.2);
                font-size: 0.95em;
            }

            .card {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 16px;
                padding: 25px;
                margin-bottom: 20px;
                backdrop-filter: blur(10px);
            }

            .card h2 {
                color: #00d2ff;
                margin-bottom: 20px;
                font-size: 1.15em;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .form-row {
                display: flex;
                gap: 10px;
                margin-bottom: 12px;
            }

            .form-group { flex: 1; }

            label {
                display: block;
                color: #aaa;
                font-size: 0.85em;
                margin-bottom: 6px;
            }

            input[type=text] {
                width: 100%;
                padding: 12px 15px;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 10px;
                background: rgba(255,255,255,0.08);
                color: #fff;
                font-size: 0.95em;
                transition: border-color 0.3s;
            }

            input[type=text]:focus {
                outline: none;
                border-color: #00d2ff;
                background: rgba(255,255,255,0.12);
            }

            input[type=text]::placeholder { color: #555; }

            .btn-ekle {
                width: 100%;
                padding: 14px;
                border: none;
                border-radius: 10px;
                background: linear-gradient(90deg, #00d2ff, #3a7bd5);
                color: #fff;
                font-size: 1.05em;
                font-weight: bold;
                cursor: pointer;
                margin-top: 10px;
                transition: opacity 0.3s, transform 0.1s;
            }

            .btn-ekle:hover  { opacity: 0.85; }
            .btn-ekle:active { transform: scale(0.98); }

            /* Playlist listesi */
            .playlist-item {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 10px;
                transition: background 0.3s;
            }

            .playlist-item:hover { background: rgba(255,255,255,0.06); }

            .playlist-item.aktif-item {
                border-color: rgba(0,210,255,0.4);
                background: rgba(0,210,255,0.05);
            }

            .playlist-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 10px;
            }

            .playlist-info { flex: 1; }

            .playlist-isim {
                font-weight: bold;
                font-size: 1em;
                margin-bottom: 4px;
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }

            .aktif-badge {
                background: rgba(0,255,136,0.15);
                border: 1px solid #00ff88;
                color: #00ff88;
                font-size: 0.7em;
                padding: 2px 8px;
                border-radius: 20px;
                font-weight: normal;
            }

            .index-badge {
                background: rgba(0,210,255,0.15);
                border: 1px solid rgba(0,210,255,0.4);
                color: #00d2ff;
                font-size: 0.7em;
                padding: 2px 8px;
                border-radius: 20px;
                font-weight: normal;
            }

            .playlist-url {
                font-size: 0.78em;
                color: #555;
                word-break: break-all;
                margin-bottom: 4px;
            }

            .playlist-meta {
                font-size: 0.75em;
                color: #444;
            }

            .playlist-tv-link {
                font-size: 0.78em;
                color: #3a7bd5;
                word-break: break-all;
                margin-top: 6px;
                cursor: pointer;
                padding: 4px 8px;
                background: rgba(58,123,213,0.1);
                border-radius: 6px;
                display: inline-block;
            }

            .playlist-tv-link:hover { color: #00d2ff; }

            .playlist-actions {
                display: flex;
                flex-direction: column;
                gap: 6px;
                min-width: 80px;
            }

            .btn-aktif {
                padding: 7px 12px;
                border: 1px solid #00d2ff;
                border-radius: 8px;
                background: transparent;
                color: #00d2ff;
                cursor: pointer;
                font-size: 0.8em;
                transition: background 0.2s;
                white-space: nowrap;
            }

            .btn-aktif:hover { background: rgba(0,210,255,0.15); }

            .btn-duzenle {
                padding: 7px 12px;
                border: 1px solid #ffa502;
                border-radius: 8px;
                background: transparent;
                color: #ffa502;
                cursor: pointer;
                font-size: 0.8em;
                transition: background 0.2s;
            }

            .btn-duzenle:hover { background: rgba(255,165,2,0.15); }

            .btn-sil {
                padding: 7px 12px;
                border: 1px solid #ff4757;
                border-radius: 8px;
                background: transparent;
                color: #ff4757;
                cursor: pointer;
                font-size: 0.8em;
                transition: background 0.2s;
            }

            .btn-sil:hover { background: rgba(255,71,87,0.15); }

            /* Sayac */
            .playlist-sayac {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding: 10px 15px;
                background: rgba(0,0,0,0.2);
                border-radius: 10px;
                font-size: 0.85em;
                color: #888;
            }

            .sayac-numara {
                color: #00d2ff;
                font-weight: bold;
                font-size: 1.2em;
            }

            /* TV linkleri */
            .tv-box {
                background: rgba(0,210,255,0.05);
                border: 1px solid rgba(0,210,255,0.2);
                border-radius: 16px;
                padding: 25px;
                margin-top: 20px;
            }

            .tv-box h2 {
                color: #00d2ff;
                margin-bottom: 20px;
                font-size: 1.15em;
            }

            .tv-link-item {
                background: rgba(0,0,0,0.25);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 12px 15px;
                margin-bottom: 10px;
            }

            .tv-link-isim {
                font-size: 0.85em;
                color: #888;
                margin-bottom: 6px;
            }

            .tv-link-url {
                font-family: monospace;
                font-size: 0.9em;
                color: #00d2ff;
                word-break: break-all;
                cursor: pointer;
                padding: 8px 12px;
                background: rgba(0,210,255,0.08);
                border-radius: 8px;
                border: 1px dashed rgba(0,210,255,0.25);
                display: block;
                transition: background 0.2s;
            }

            .tv-link-url:hover { background: rgba(0,210,255,0.15); }

            .tv-link-aktif {
                border-color: rgba(0,255,136,0.3);
                background: rgba(0,255,136,0.05);
            }

            .tv-link-aktif .tv-link-url {
                color: #00ff88;
                background: rgba(0,255,136,0.08);
                border-color: rgba(0,255,136,0.25);
            }

            /* Duzenleme modali */
            .modal {
                display: none;
                position: fixed;
                top: 0; left: 0;
                width: 100%; height: 100%;
                background: rgba(0,0,0,0.7);
                z-index: 1000;
                justify-content: center;
                align-items: center;
            }

            .modal.aktif { display: flex; }

            .modal-icerik {
                background: #1a1a2e;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 16px;
                padding: 30px;
                width: 90%;
                max-width: 500px;
            }

            .modal-icerik h3 { color: #00d2ff; margin-bottom: 20px; }

            .modal-butonlar {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }

            .btn-kaydet {
                flex: 1;
                padding: 12px;
                border: none;
                border-radius: 10px;
                background: linear-gradient(90deg, #00d2ff, #3a7bd5);
                color: #fff;
                font-size: 1em;
                font-weight: bold;
                cursor: pointer;
            }

            .btn-iptal {
                flex: 1;
                padding: 12px;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 10px;
                background: transparent;
                color: #aaa;
                font-size: 1em;
                cursor: pointer;
            }

            /* Mesaj */
            #mesaj {
                display: none;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 15px;
                text-align: center;
                font-weight: bold;
                font-size: 0.95em;
            }

            .basari {
                background: rgba(0,255,136,0.1);
                border: 1px solid #00ff88;
                color: #00ff88;
            }

            .hata {
                background: rgba(255,71,87,0.1);
                border: 1px solid #ff4757;
                color: #ff4757;
            }

            .bos { color:#555; text-align:center; padding:30px; font-size:0.95em; }

            /* Arama */
            .arama-kutusu {
                width: 100%;
                padding: 10px 15px;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px;
                background: rgba(255,255,255,0.05);
                color: #fff;
                font-size: 0.9em;
                margin-bottom: 15px;
            }

            .arama-kutusu:focus { outline: none; border-color: #00d2ff; }

            @media(max-width: 600px) {
                h1 { font-size: 1.7em; }
                .form-row { flex-direction: column; }
                .playlist-header { flex-direction: column; }
                .playlist-actions {
                    flex-direction: row;
                    min-width: unset;
                    width: 100%;
                }
                .btn-aktif, .btn-duzenle, .btn-sil { flex: 1; text-align: center; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📺 IPTV Panelim</h1>
            <p class="subtitle">M3U listelerinizi webden yonetin, Android TV'den izleyin</p>

            <div id="durum" class="durum">⏳ Yukleniyor...</div>

            <!-- EKLEME FORMU -->
            <div class="card">
                <h2>➕ Yeni Playlist Ekle</h2>
                <div id="mesaj"></div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Playlist Adi</label>
                        <input type="text" id="isim" placeholder="Ornek: Turk Kanallari">
                    </div>
                </div>
                <div class="form-group">
                    <label>M3U Linki</label>
                    <input type="text" id="url" placeholder="http://ornek.com/playlist.m3u">
                </div>
                <button class="btn-ekle" onclick="ekle()">💾 Playlist Ekle</button>
            </div>

            <!-- PLAYLİST LİSTESİ -->
            <div class="card">
                <h2>📋 Kayitli Playlistler</h2>
                <input
                    type="text"
                    class="arama-kutusu"
                    id="arama"
                    placeholder="🔍 Playlist ara..."
                    oninput="aramaYap()"
                >
                <div class="playlist-sayac">
                    <span>Toplam Playlist</span>
                    <span class="sayac-numara" id="sayac">0</span>
                </div>
                <div id="liste-container">
                    <p class="bos">⏳ Yukleniyor...</p>
                </div>
            </div>

            <!-- TV LİNKLERİ -->
            <div class="tv-box">
                <h2>📺 Android TV Linkleri</h2>
                <p style="color:#888;font-size:0.85em;margin-bottom:15px;">
                    Her playlist icin ayri bir link olusturuldu.
                    Uzerine tiklayarak kopyalayabilirsiniz.
                </p>
                <div id="tv-linkler">
                    <p class="bos">⏳ Yukleniyor...</p>
                </div>
                <br>
                <div style="color:#666;font-size:0.82em;line-height:1.9;">
                    <strong style="color:#aaa;">Nasil Eklenir?</strong><br>
                    1. Televizo veya TiviMate'i acin<br>
                    2. Playlist Ekle > M3U Link secin<br>
                    3. Istediginiz linki kopyalayip yapistirin<br>
                    4. Kaydedin ve izlemeye baslayin!
                </div>
            </div>
        </div>

        <!-- DUZENLEME MODALi -->
        <div class="modal" id="modal">
            <div class="modal-icerik">
                <h3>✏️ Playlist Duzenle</h3>
                <input type="hidden" id="duzenle-index">
                <div class="form-group" style="margin-bottom:15px;">
                    <label>Playlist Adi</label>
                    <input type="text" id="duzenle-isim" placeholder="Playlist adi">
                </div>
                <div class="form-group">
                    <label>M3U Linki</label>
                    <input type="text" id="duzenle-url" placeholder="http://ornek.com/playlist.m3u">
                </div>
                <div class="modal-butonlar">
                    <button class="btn-kaydet" onclick="duzenleKaydet()">💾 Kaydet</button>
                    <button class="btn-iptal"  onclick="modalKapat()">İptal</button>
                </div>
            </div>
        </div>

        <script>
            var tumPlaylists = [];
            var aktifUrl     = '';

            document.addEventListener('DOMContentLoaded', function() {
                verileriYukle();
            });

            setTimeout(verileriYukle, 300);

            function verileriYukle() {
                fetch('/api/data')
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        tumPlaylists = data.playlists || [];
                        aktifUrl     = data.m3u_url   || '';
                        durumGuncelle(aktifUrl);
                        listeGuncelle(tumPlaylists, aktifUrl);
                        tvLinkleriGuncelle(tumPlaylists, aktifUrl);
                        document.getElementById('sayac').textContent = tumPlaylists.length;
                    })
                    .catch(function(e) {
                        document.getElementById('durum').textContent      = '❌ Baglanti hatasi';
                        document.getElementById('durum').style.color       = '#ff4757';
                        document.getElementById('durum').style.borderColor = '#ff4757';
                    });
            }

            function durumGuncelle(aktifUrl) {
                var el = document.getElementById('durum');
                if (aktifUrl && aktifUrl.length > 0) {
                    el.style.color       = '#00ff88';
                    el.style.borderColor = '#00ff88';
                    el.textContent       = '● AKTIF PLAYLIST MEVCUT — TV IZLEMEYE HAZIR';
                } else {
                    el.style.color       = '#ff4757';
                    el.style.borderColor = '#ff4757';
                    el.textContent       = '● PLAYLIST EKLENMEDI';
                }
            }

            function listeGuncelle(playlists, aktifUrl) {
                var el = document.getElementById('liste-container');
                if (!playlists || playlists.length === 0) {
                    el.innerHTML = '<p class="bos">Henuz playlist eklenmedi.<br>Yukaridan yeni playlist ekleyin.</p>';
                    return;
                }
                var html = '';
                for (var i = 0; i < playlists.length; i++) {
                    var p        = playlists[i];
                    var isAktif  = (p.url === aktifUrl);
                    var tvLink   = window.location.origin + '/get/' + i;

                    html += '<div class="playlist-item ' + (isAktif ? 'aktif-item' : '') + '" id="item-' + i + '">';
                    html += '  <div class="playlist-header">';
                    html += '    <div class="playlist-info">';
                    html += '      <div class="playlist-isim">';
                    html += '        <span class="index-badge">#' + (i + 1) + '</span>';
                    html += '        ' + guvenliyaz(p.isim);
                    if (isAktif) {
                        html += ' <span class="aktif-badge">✅ AKTİF</span>';
                    }
                    html += '      </div>';
                    html += '      <div class="playlist-url">' + guvenliyaz(p.url) + '</div>';
                    html += '      <div class="playlist-meta">Eklendi: ' + (p.tarih || '-') + '</div>';
                    html += '      <span class="playlist-tv-link" onclick="linkKopyala(\'' + tvLink + '\')" title="Kopyala">';
                    html += '        📺 ' + tvLink;
                    html += '      </span>';
                    html += '    </div>';
                    html += '    <div class="playlist-actions">';
                    if (!isAktif) {
                        html += '      <button class="btn-aktif"   onclick="aktifYap(' + i + ')">▶ Aktif</button>';
                    }
                    html += '      <button class="btn-duzenle" onclick="modalAc(' + i + ')">✏️ Duzenle</button>';
                    html += '      <button class="btn-sil"     onclick="sil(' + i + ')">🗑️ Sil</button>';
                    html += '    </div>';
                    html += '  </div>';
                    html += '</div>';
                }
                el.innerHTML = html;
            }

            function tvLinkleriGuncelle(playlists, aktifUrl) {
                var el   = document.getElementById('tv-linkler');
                var base = window.location.origin;

                if (!playlists || playlists.length === 0) {
                    el.innerHTML = '<p class="bos">Henuz playlist eklenmedi</p>';
                    return;
                }

                var html = '';

                // Aktif link
                html += '<div class="tv-link-item tv-link-aktif">';
                html += '  <div class="tv-link-isim">✅ Aktif Playlist (Her zaman aktif olani gosterir)</div>';
                html += '  <div class="tv-link-url" onclick="linkKopyala(\'' + base + '/get\')">' + base + '/get</div>';
                html += '</div>';

                // Her playlist icin
                for (var i = 0; i < playlists.length; i++) {
                    var p    = playlists[i];
                    var link = base + '/get/' + i;
                    html += '<div class="tv-link-item">';
                    html += '  <div class="tv-link-isim">#' + (i + 1) + ' — ' + guvenliyaz(p.isim) + '</div>';
                    html += '  <div class="tv-link-url" onclick="linkKopyala(\'' + link + '\')">' + link + '</div>';
                    html += '</div>';
                }

                el.innerHTML = html;
            }

            function aramaYap() {
                var aranan = document.getElementById('arama').value.toLowerCase();
                if (!aranan) {
                    listeGuncelle(tumPlaylists, aktifUrl);
                    return;
                }
                var filtrelendi = tumPlaylists.filter(function(p) {
                    return p.isim.toLowerCase().indexOf(aranan) !== -1 ||
                           p.url.toLowerCase().indexOf(aranan)  !== -1;
                });
                listeGuncelle(filtrelendi, aktifUrl);
            }

            function mesajGoster(metin, tip) {
                var el = document.getElementById('mesaj');
                el.textContent    = metin;
                el.className      = tip;
                el.style.display  = 'block';
                setTimeout(function() { el.style.display = 'none'; }, 3000);
            }

            function ekle() {
                var isim = document.getElementById('isim').value.trim();
                var url  = document.getElementById('url').value.trim();
                if (!isim) {
                    mesajGoster('❌ Playlist adi bos olamaz', 'hata');
                    return;
                }
                if (!url.startsWith('http')) {
                    mesajGoster('❌ Gecerli bir M3U linki girin', 'hata');
                    return;
                }
                fetch('/api/ekle', {
                    method:  'POST',
                    headers: {'Content-Type': 'application/json'},
                    body:    JSON.stringify({isim: isim, url: url})
                })
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    if (d.durum === 'ok') {
                        mesajGoster('✅ Playlist basariyla eklendi!', 'basari');
                        document.getElementById('isim').value = '';
                        document.getElementById('url').value  = '';
                        setTimeout(verileriYukle, 1000);
                    } else {
                        mesajGoster('❌ ' + (d.hata || 'Eklenemedi'), 'hata');
                    }
                })
                .catch(function(e) { mesajGoster('❌ Hata: ' + e, 'hata'); });
            }

            function aktifYap(index) {
                fetch('/api/aktif/' + index, {method: 'POST'})
                    .then(function() { setTimeout(verileriYukle, 1000); });
            }

            function sil(index) {
                var p = tumPlaylists[index];
                if (!p) return;
                if (confirm('"' + p.isim + '" silinsin mi?')) {
                    fetch('/api/sil/' + index, {method: 'POST'})
                        .then(function() { setTimeout(verileriYukle, 1000); });
                }
            }

            function modalAc(index) {
                var p = tumPlaylists[index];
                if (!p) return;
                document.getElementById('duzenle-index').value = index;
                document.getElementById('duzenle-isim').value  = p.isim;
                document.getElementById('duzenle-url').value   = p.url;
                document.getElementById('modal').classList.add('aktif');
            }

            function modalKapat() {
                document.getElementById('modal').classList.remove('aktif');
            }

            function duzenleKaydet() {
                var index = parseInt(document.getElementById('duzenle-index').value);
                var isim  = document.getElementById('duzenle-isim').value.trim();
                var url   = document.getElementById('duzenle-url').value.trim();
                fetch('/api/duzenle/' + index, {
                    method:  'POST',
                    headers: {'Content-Type': 'application/json'},
                    body:    JSON.stringify({isim: isim, url: url})
                })
                .then(function(r) { return r.json(); })
                .then(function() {
                    modalKapat();
                    setTimeout(verileriYukle, 1000);
                });
            }

            function linkKopyala(link) {
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(link)
                        .then(function() { alert('✅ Kopyalandi:\n' + link); })
                        .catch(function() { prompt('Linki kopyalayin:', link); });
                } else {
                    prompt('Linki kopyalayin:', link);
                }
            }

            function guvenliyaz(metin) {
                if (!metin) return '';
                return metin
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;');
            }

            // Modal disina tiklayinca kapat
            document.getElementById('modal').addEventListener('click', function(e) {
                if (e.target === this) modalKapat();
            });

            // Enter tusu ile ekle
            document.getElementById('url').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') ekle();
            });
        </script>
    </body>
    </html>
    """
