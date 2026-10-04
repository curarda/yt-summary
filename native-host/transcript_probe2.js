/* ÜYELİK VİDEOSU ALTYAZI TESTİ #2 (kesin)
   Kullanım: üyelik videosunu aç → F12 → Console → bu kodun TAMAMINI yapıştır →
   Enter. Çıkan "SONUC2:" satırını kopyalayıp bana gönder. */
(async () => {
  const r = {};
  // 1) Sayfadaki oynatıcı yanıtından altyazı listesini al
  let pr = null;
  try { pr = window.ytInitialPlayerResponse || ytInitialPlayerResponse; } catch (e) {}
  const tracks =
    (pr && pr.captions && pr.captions.playerCaptionsTracklistRenderer &&
     pr.captions.playerCaptionsTracklistRenderer.captionTracks) || [];
  r.altyaziSayisi = tracks.length;
  r.diller = tracks.map((t) => (t.languageCode || "?") + (t.kind === "asr" ? "(oto)" : "")).slice(0, 8);

  // 2) Altyazı adresini sayfa bağlamında (senin oturumun) çekmeyi dene
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
  console.log("SONUC2:", JSON.stringify(r));
  return r;
})();
