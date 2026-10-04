#!/usr/bin/env python3
"""
YouTube video -> Claude ile Türkçe özet -> Google Docs'a native doküman.

Girdi: argümandan veya panodan (pbpaste) bir YouTube URL'si.
Çıktı: Google Docs'ta oluşturulan dokümanı tarayıcıda açar + bildirim gösterir.

Yapılandırma:
  - Anthropic API anahtarı: macOS Keychain, service = "yt-summary-anthropic"
  - Google OAuth istemcisi: ~/.config/yt-summary/credentials.json
  - Google token önbelleği:  ~/.config/yt-summary/token.json
"""

import os
import re
import sys
import json
import subprocess
import traceback
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "yt-summary"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
LOG_FILE = CONFIG_DIR / "last-run.log"
RESULT_FILE = CONFIG_DIR / "last-result.json"
KEYCHAIN_SERVICE = "yt-summary-anthropic"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
MODEL = os.environ.get("YT_SUMMARY_MODEL", "claude-sonnet-5")
MAX_TRANSCRIPT_CHARS = 200_000
# Eylem: "summary" (Claude özeti) veya "transcript" (ham transkript, özet yok).
ACTION = os.environ.get("YT_SUMMARY_ACTION", "summary").strip().lower()
if "--transcript" in sys.argv:
    ACTION = "transcript"
# Üyelere özel / yaş kısıtlı videolar için tarayıcı çerezleri (yt-dlp).
# Farklı profil kullanıyorsan: "chrome:Profile 1" gibi.
COOKIES_BROWSER = os.environ.get("YT_SUMMARY_COOKIES", "chrome")
# Dokümanın açılacağı tarayıcı uygulaması.
BROWSER_APP = os.environ.get("YT_SUMMARY_BROWSER", "Google Chrome")
# PO-token sağlayıcı (üyelere özel/yaş kısıtlı altyazılar için).
SCRIPT_DIR = Path(__file__).resolve().parent
BGUTIL_SERVER = str(SCRIPT_DIR / "bgutil-provider" / "server")
# Node ve brew araçlarının bulunması için PATH eki (Quick Action/host ortamı dar olabilir).
EXTRA_PATH = "/opt/homebrew/bin:/usr/local/bin"


def _ytdlp_env():
    env = os.environ.copy()
    env["PATH"] = EXTRA_PATH + ":" + env.get("PATH", "")
    return env


def _pot_args():
    return [
        "--ignore-no-formats-error",
        "--extractor-args", "youtube:player_client=web",
        "--extractor-args", "youtubepot-bgutilscript:server_home=" + BGUTIL_SERVER,
    ]


# ----------------------------- yardımcılar -----------------------------

def _as_str(s: str) -> str:
    """AppleScript metin literali için güvenli kaçış (UTF-8 korunur)."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def notify(title: str, message: str):
    """macOS bildirimi göster."""
    try:
        script = f"display notification {_as_str(message)} with title {_as_str(title)}"
        subprocess.run(["osascript", "-e", script], check=False,
                       capture_output=True)
    except Exception:
        pass


def log(msg: str):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(msg + "\n")
    print(msg, file=sys.stderr)


def write_result(data: dict):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_FILE.write_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


def die(user_msg: str, detail: str = ""):
    log("HATA: " + user_msg + ("\n" + detail if detail else ""))
    write_result({"ok": False, "error": user_msg})
    notify("YouTube Özetle — Hata", user_msg)
    sys.exit(1)


def extract_video_id(text: str) -> str:
    """Metin içinden ilk YouTube video kimliğini çıkar."""
    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)
    # Çıplak 11 karakterlik kimlik verilmişse
    m = re.fullmatch(r"[A-Za-z0-9_-]{11}", text.strip())
    if m:
        return text.strip()
    return ""


def get_input_url() -> str:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and args[0].strip():
        return " ".join(args).strip()
    # Pano
    try:
        out = subprocess.run(["pbpaste"], capture_output=True, text=True)
        return out.stdout.strip()
    except Exception:
        return ""


def get_video_meta(video_id: str) -> dict:
    """oEmbed ile başlık ve kanal adı (anahtar gerektirmez)."""
    import urllib.request
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode())
        return {"title": data.get("title", ""), "author": data.get("author_name", "")}
    except Exception:
        return {"title": "", "author": ""}


# ----------------------------- transcript -----------------------------

def fetch_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()

    def join(fetched):
        return " ".join(seg.text for seg in fetched if seg.text and seg.text.strip())

    # 1) Doğrudan tercih dillerinde dene
    try:
        fetched = api.fetch(video_id, languages=["tr", "en", "en-US", "en-GB"])
        text = join(fetched)
        if text.strip():
            return text
    except Exception:
        pass

    # 2) Mevcutları listele, en iyisini seç, gerekiyorsa Türkçeye çevir
    try:
        tlist = api.list(video_id)
    except Exception as e:
        return _yt_dlp_transcript(video_id) or die_no_transcript(e)

    # Öncelik: elle yazılmış tr/en -> otomatik tr/en -> herhangi biri (çeviri)
    candidates = []
    try:
        candidates.append(tlist.find_manually_created_transcript(["tr", "en"]))
    except Exception:
        pass
    try:
        candidates.append(tlist.find_generated_transcript(["tr", "en"]))
    except Exception:
        pass
    if not candidates:
        for t in tlist:
            candidates.append(t)
            break

    for t in candidates:
        try:
            fetched = t.fetch()
            text = join(fetched)
            if text.strip():
                return text
        except Exception:
            continue
        # çevrilebiliyorsa Türkçe dene
        try:
            if getattr(t, "is_translatable", False):
                fetched = t.translate("tr").fetch()
                text = join(fetched)
                if text.strip():
                    return text
        except Exception:
            continue

    # 3) yt-dlp yedeği
    fallback = _yt_dlp_transcript(video_id)
    if fallback:
        return fallback
    die("Bu videoda altyazı/transcript bulunamadı.",
        "Ne youtube-transcript-api ne de yt-dlp altyazı döndürdü.")


def die_no_transcript(e):
    die("Bu videoda altyazı/transcript bulunamadı.", str(e))


def _ytdlp_bin() -> str:
    ytdlp = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
    return ytdlp if os.path.exists(ytdlp) else "yt-dlp"


def _json3_to_text(path: str) -> str:
    """YouTube json3 altyazı dosyasını düz metne çevir."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return ""
    parts = []
    for ev in data.get("events", []):
        for s in ev.get("segs", []) or []:
            t = s.get("utf8", "")
            if t and t.strip():
                parts.append(t)
    return " ".join(" ".join(parts).split())


def _yt_dlp_transcript(video_id: str) -> str:
    """yt-dlp + çerez + PO-token ile altyazıyı çek (üyelere özel/yaş kısıtlı dahil)."""
    import tempfile
    import glob
    ytdlp = _ytdlp_bin()
    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "sub")
        cmd = [
            ytdlp, "--skip-download",
            "--write-auto-subs", "--write-subs",
            "--sub-langs", "tr,en.*,en",
            "--sub-format", "json3",
            "--cookies-from-browser", COOKIES_BROWSER,
            "-o", out, url,
        ] + _pot_args()
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=240, env=_ytdlp_env())
        except Exception:
            return ""
        files = glob.glob(os.path.join(td, "*.json3"))
        # Türkçe altyazıyı öne al
        files.sort(key=lambda p: (0 if ".tr" in os.path.basename(p) else 1, p))
        for f in files:
            t = _json3_to_text(f)
            if t.strip():
                return t
        # json3 olmadıysa vtt dene
        for v in glob.glob(os.path.join(td, "*.vtt")):
            t = _vtt_to_text(v)
            if t.strip():
                return t
    return ""


def _yt_dlp_title(video_id: str) -> dict:
    """oEmbed başarısızsa (örn. üyelere özel) başlığı yt-dlp + çerez + PO-token ile al."""
    ytdlp = _ytdlp_bin()
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [ytdlp, "--skip-download", "--no-warnings",
           "--print", "%(title)s\n%(channel)s",
           "--cookies-from-browser", COOKIES_BROWSER] + _pot_args() + [url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90, env=_ytdlp_env())
        lines = [l for l in out.stdout.strip().splitlines() if l.strip()]
        if lines:
            return {"title": lines[0], "author": lines[1] if len(lines) > 1 else ""}
    except Exception:
        pass
    return {"title": "", "author": ""}


def _vtt_to_text(path: str) -> str:
    lines = []
    seen = set()
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or "-->" in line or line.startswith("WEBVTT") \
               or line.isdigit() or line.startswith(("Kind:", "Language:")):
                continue
            line = re.sub(r"<[^>]+>", "", line)  # zaman etiketlerini temizle
            if line and line not in seen:
                seen.add(line)
                lines.append(line)
    return " ".join(lines)


# ----------------------------- Claude özet -----------------------------

def get_anthropic_key() -> str:
    env = os.environ.get("ANTHROPIC_API_KEY")
    if env:
        return env
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True,
        )
        key = out.stdout.strip()
        if key:
            return key
    except Exception:
        pass
    die("Anthropic API anahtarı bulunamadı.",
        f"Keychain service '{KEYCHAIN_SERVICE}' boş ve ANTHROPIC_API_KEY tanımlı değil.")


def summarize(transcript: str, meta: dict) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=get_anthropic_key())

    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n\n[transcript kısaltıldı]"

    baslik = meta.get("title") or "YouTube videosu"
    kanal = meta.get("author") or "bilinmiyor"

    system = (
        "Sen deneyimli bir içerik editörüsün. Türkçe, yüksek bilgi yoğunluklu, "
        "yalın özetler yazarsın. Dolgu cümle, tekrar ve gereksiz giriş/kapanış "
        "kullanmazsın. Çıktıyı SADECE Markdown olarak verirsin."
    )
    prompt = f"""Aşağıda "{baslik}" ({kanal}) başlıklı YouTube videosunun transkripti var.

Şu Markdown yapısında, öz ve doğrudan yaz:

# {baslik}

**Kanal:** {kanal}

## Özet (TL;DR)
2-3 cümle.

## Ana Noktalar
- En önemli fikirler, madde madde (6-10 madde). Her madde tek satır, öz.

## Detaylı Anlatım
Videonun akışını takip eden, alt başlıklara (###) bölünmüş açıklama. Uzun paragraflardan
kaçın; her alt başlık altında 2-4 kısa cümle yeter. Önemli terimleri **kalın** yaz.

## Çıkarımlar
- Uygulanabilir somut çıkarımlar (3-6 madde).

Kurallar:
- Türkçe yaz, öz ve net ol; kelime şişirme.
- Transkriptte olmayan bilgi uydurma.
- Sayısal veriler, isimler ve örnekleri koru.

Transkript:
\"\"\"
{transcript}
\"\"\"
"""
    md_parts = []
    with client.messages.stream(
        model=MODEL,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            md_parts.append(text)
    md = "".join(md_parts).strip()
    if not md:
        die("Claude boş özet döndürdü.")
    return md


# ----------------------------- Google Docs -----------------------------

def get_google_creds():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    if not CREDENTIALS_FILE.exists():
        die("Google OAuth istemci dosyası yok.",
            f"{CREDENTIALS_FILE} bulunamadı. Kurulum adımlarını izle.")

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GOOGLE_SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), GOOGLE_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        os.chmod(TOKEN_FILE, 0o600)
    return creds


def md_to_html(md_text: str, title: str) -> str:
    import markdown
    body = markdown.markdown(md_text, extensions=["extra", "sane_lists", "nl2br"])
    return f"<html><head><meta charset='utf-8'><title>{title}</title></head><body>{body}</body></html>"


def transcript_to_html(text: str, title: str) -> str:
    """Ham transkripti okunabilir paragraflara bölerek HTML üret (özet yok)."""
    import html as _html
    sentences = re.split(r"(?<=[.!?…])\s+", text.strip())
    paras, cur = [], []
    for s in sentences:
        cur.append(s)
        if len(cur) >= 4:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    if not paras:
        paras = [text]
    body = "".join("<p>" + _html.escape(p) + "</p>" for p in paras if p.strip())
    return (f"<html><head><meta charset='utf-8'><title>{_html.escape(title)}</title></head>"
            f"<body><h1>{_html.escape(title)}</h1>{body}</body></html>")


def _upload_html(html_str: str, doc_name: str) -> str:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload

    creds = get_google_creds()
    service = build("drive", "v3", credentials=creds)
    media = MediaInMemoryUpload(html_str.encode("utf-8"), mimetype="text/html", resumable=False)
    file = service.files().create(
        body={"name": (doc_name or "YouTube")[:200],
              "mimeType": "application/vnd.google-apps.document"},
        media_body=media,
        fields="id, webViewLink",
    ).execute()
    return file.get("webViewLink") or f"https://docs.google.com/document/d/{file['id']}/edit"


def upload_to_docs(md_text: str, title: str) -> str:
    return _upload_html(md_to_html(md_text, title), title or "YouTube Özeti")


# ----------------------------- ana akış -----------------------------

def main():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # her çalıştırmada logu ve sonucu sıfırla
    try:
        LOG_FILE.write_text("")
        if RESULT_FILE.exists():
            RESULT_FILE.unlink()
    except Exception:
        pass

    raw = get_input_url()
    if not raw:
        die("Girdi yok.", "Argüman ya da panoda YouTube URL'si bulunamadı.")

    video_id = extract_video_id(raw)
    if not video_id:
        die("Geçerli bir YouTube linki bulunamadı.", f"Girdi: {raw[:200]}")

    # Eklenti sayfadan transkript gönderdiyse (üyelere özel videolar dahil) onu kullan.
    tf = os.environ.get("YT_SUMMARY_TRANSCRIPT_FILE")
    provided = None
    if tf and os.path.exists(tf):
        try:
            provided = Path(tf).read_text(encoding="utf-8").strip()
        except Exception:
            provided = None

    if provided:
        transcript = provided
        env_title = os.environ.get("YT_SUMMARY_TITLE", "").strip()
        meta = {"title": env_title, "author": ""}
        if not meta["title"]:
            meta = get_video_meta(video_id) or meta
        log(f"Transcript (sayfadan): {len(transcript)} karakter")
    else:
        notify("Full Transkript" if ACTION == "transcript" else "YouTube Özetle",
               "Transcript çekiliyor…")
        # Başlık (oEmbed) ve transcript'i paralel çek.
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_meta = ex.submit(get_video_meta, video_id)
            f_tr = ex.submit(fetch_transcript, video_id)
            meta = f_meta.result()
            transcript = f_tr.result()
        # oEmbed başlık veremediyse (üyelere özel vb.) yt-dlp ile dene.
        if not meta.get("title"):
            meta = _yt_dlp_title(video_id) or meta
        log(f"Transcript uzunluğu: {len(transcript)} karakter")

    base_title = meta.get("title") or f"YouTube ({video_id})"

    if ACTION == "transcript":
        # Özet YOK — ham transkripti olduğu gibi Google Docs'a yükle.
        etiket = "Full Transkript"
        notify(etiket, "Google Docs'a yükleniyor…")
        doc_title = base_title + " — Full Transkript"
        url = _upload_html(transcript_to_html(transcript, base_title), doc_title)
    else:
        etiket = "YouTube Özetle"
        notify(etiket, "Claude özetliyor…")
        md = summarize(transcript, meta)
        notify(etiket, "Google Docs'a yükleniyor…")
        doc_title = base_title
        url = _upload_html(md_to_html(md, base_title), doc_title)

    log("Doküman: " + url)
    write_result({"ok": True, "title": doc_title, "url": url})
    # Dokümanı Chrome'da (açık penceredeki yeni sekmede) aç.
    r = subprocess.run(["open", "-a", BROWSER_APP, url], capture_output=True, text=True)
    if r.returncode != 0:
        subprocess.run(["open", url], check=False)  # Chrome yoksa varsayılan tarayıcı
    notify(etiket + " — Hazır ✅", doc_title[:120])


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        die("Beklenmeyen hata: " + str(e), traceback.format_exc())
