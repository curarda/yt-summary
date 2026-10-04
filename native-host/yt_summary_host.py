#!/usr/bin/env python3
"""
Chrome Native Messaging host'u.
Chrome eklentisinden {"url": "..."} mesajı alır, yt_summarize.py'yi çalıştırır,
sonucu {"ok": true, "title":..., "url":...} olarak geri döner.

stdout SADECE çerçevelenmiş (4 byte uzunluk + JSON) yanıt için kullanılır;
başka hiçbir şey stdout'a yazılmamalı.
"""
import sys
import json
import struct
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # proje klasörü (native-host/ bir üstü)
PYTHON = BASE / ".venv" / "bin" / "python"
SCRIPT = BASE / "yt_summarize.py"
RESULT_FILE = Path.home() / ".config" / "yt-summary" / "last-result.json"
HOST_LOG = Path.home() / ".config" / "yt-summary" / "native-host.log"


def hlog(msg):
    try:
        with open(HOST_LOG, "a") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


def read_message():
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) < 4:
        return None
    msg_len = struct.unpack("=I", raw_len)[0]
    data = sys.stdin.buffer.read(msg_len).decode("utf-8")
    return json.loads(data)


def send_message(obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def main():
    try:
        msg = read_message()
    except Exception as e:
        hlog("read hatası: " + str(e))
        send_message({"ok": False, "error": "Mesaj okunamadı: " + str(e)})
        return

    if not msg or "url" not in msg:
        send_message({"ok": False, "error": "URL yok."})
        return

    url = msg["url"]
    transcript = msg.get("transcript")
    title = msg.get("title")
    mode = (msg.get("mode") or "summary").strip().lower()
    action = "transcript" if mode == "transcript" else "summary"
    hlog("İstek [%s]: %s%s" % (action, url,
         (" [transkript: %d krktr]" % len(transcript)) if transcript else ""))

    import os, tempfile
    env = os.environ.copy()
    env["YT_SUMMARY_ACTION"] = action
    tf_path = None
    if transcript:
        tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        tf.write(transcript)
        tf.close()
        tf_path = tf.name
        env["YT_SUMMARY_TRANSCRIPT_FILE"] = tf_path
    if title:
        env["YT_SUMMARY_TITLE"] = title

    try:
        proc = subprocess.run(
            [str(PYTHON), str(SCRIPT), url],
            capture_output=True, text=True, timeout=600, env=env,
        )
        hlog("exit=%s stderr=%s" % (proc.returncode, proc.stderr[-500:]))
    except Exception as e:
        hlog("çalıştırma hatası: " + str(e))
        send_message({"ok": False, "error": "Script çalıştırılamadı: " + str(e)})
        return

    if tf_path:
        try:
            os.unlink(tf_path)
        except Exception:
            pass

    # Sonucu makine-okunur dosyadan al
    try:
        result = json.loads(RESULT_FILE.read_text())
    except Exception:
        result = {"ok": proc.returncode == 0,
                  "error": "Sonuç okunamadı (script çıkışı %s)" % proc.returncode}
    send_message(result)


if __name__ == "__main__":
    main()
