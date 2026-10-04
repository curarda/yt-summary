/* ÜYELİK VİDEOSU ALTYAZI TESTİ #3 — güncel oynatıcı yanıtından
   Kullanım: üyelik videosunu aç → F12 → Console → bu kodun TAMAMINI yapıştır →
   Enter. Çıkan "SONUC3:" satırını kopyalayıp bana gönder. */
(async () => {
  const r = {};
  function getPR() {
    const mp = document.getElementById("movie_player") || document.querySelector(".html5-video-player");
    if (mp && mp.getPlayerResponse) { try { return mp.getPlayerResponse(); } catch (e) {} }
    try { return window.ytInitialPlayerResponse; } catch (e) {}
    return null;
  }
  const pr = getPR();
  r.oynaticiYanit = !!pr;
  const tracks =
    (pr && pr.captions && pr.captions.playerCaptionsTracklistRenderer &&
     pr.captions.playerCaptionsTracklistRenderer.captionTracks) || [];
  r.altyaziSayisi = tracks.length;
  r.diller = tracks.map((t) => (t.languageCode || "?") + (t.kind === "asr" ? "(oto)" : "")).slice(0, 8);

  if (tracks.length) {
    const base = tracks[0].baseUrl;
    for (const fmt of ["&fmt=json3", ""]) {
      const key = "cek" + (fmt ? "_json3" : "_ham");
      try {
        const resp = await fetch(base + fmt, { credentials: "include" });
        const txt = await resp.text();
        r[key] = { durum: resp.status, uzunluk: txt.length, ilk: txt.slice(0, 50) };
      } catch (e) {
        r[key] = "HATA " + e.message;
      }
    }
  }
  console.log("SONUC3:", JSON.stringify(r));
  return r;
})();
