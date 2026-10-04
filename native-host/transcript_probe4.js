/* TRANSKRİPT OKUMA TESTİ #4 — panel ELLE AÇIKKEN
   ÖNCE: videonun altında "...daha fazla" → "Transkripti göster"e tıkla,
   sağda transkript listesi görünsün. SONRA bu kodu Console'a yapıştır.
   "SONUC4:" satırını bana gönder. */
(() => {
  const r = {};
  const segs = document.querySelectorAll("ytd-transcript-segment-renderer");
  r.segmentSayisi = segs.length;
  if (segs.length) {
    const text = [...segs]
      .map((s) => {
        const el = s.querySelector('.segment-text, yt-formatted-string.segment-text, [class*="segment-text"]');
        return (el ? el.textContent : s.innerText || "").replace(/\s+/g, " ").trim();
      })
      .filter(Boolean)
      .join(" ");
    r.uzunluk = text.length;
    r.ornek = text.slice(0, 150);
  } else {
    // panel açık ama farklı yapıda olabilir — teşhis
    r.paneller = [...document.querySelectorAll("ytd-engagement-panel-section-list-renderer")].map(
      (p) => (p.getAttribute("target-id") || "?") + ":" + (p.getAttribute("visibility") || "?")
    );
    const panel = [...document.querySelectorAll("ytd-engagement-panel-section-list-renderer")].find(
      (p) => /transcript/.test(p.getAttribute("target-id") || "") && /EXPANDED/.test(p.getAttribute("visibility") || "")
    );
    r.acikPanelMetinUzunlugu = panel ? (panel.innerText || "").length : -1;
    r.acikPanelOrnek = panel ? (panel.innerText || "").replace(/\s+/g, " ").slice(0, 200) : "";
  }
  console.log("SONUC4:", JSON.stringify(r));
  return r;
})();
