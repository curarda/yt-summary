/* ÜYELİK VİDEOSU TRANSKRİPT TESTİ
   Kullanım: üyelik videosunu aç → F12 → Console sekmesi → bu kodun TAMAMINI
   yapıştır → Enter. Çıkan "SONUC:" satırını kopyalayıp bana gönder. */
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const qa = (s, root) => [...(root || document).querySelectorAll(s)];
  const segNodes = () => document.querySelectorAll("ytd-transcript-segment-renderer");
  const label = (el) => (el.getAttribute("aria-label") || el.textContent || "").replace(/\s+/g, " ").trim();
  const collect = () =>
    [...segNodes()]
      .map((s) => {
        const el = s.querySelector('.segment-text, yt-formatted-string.segment-text, [class*="segment-text"]');
        return (el ? el.textContent : s.innerText || "").replace(/\s+/g, " ").trim();
      })
      .filter(Boolean)
      .join(" ");

  if (!segNodes().length) {
    const exp = document.querySelector("#description-inline-expander #expand, tp-yt-paper-button#expand, #expand");
    if (exp) { exp.click(); await sleep(700); }
    const cands = qa('button, tp-yt-paper-button, [role="button"], ytd-button-renderer, yt-button-shape button');
    const b =
      cands.find((x) => /^(show transcript|transkripti göster)$/i.test(label(x))) ||
      cands.find((x) => /\btranscript\b|transkript/i.test(label(x))) ||
      document.querySelector("ytd-video-description-transcript-section-renderer button");
    if (b) { b.scrollIntoView({ block: "center" }); b.click(); }
    for (let i = 0; i < 35 && segNodes().length === 0; i++) {
      await sleep(400);
      const panel = qa("ytd-engagement-panel-section-list-renderer").find(
        (p) => /searchable-transcript/.test(p.getAttribute("target-id") || "") && /EXPANDED/.test(p.getAttribute("visibility") || "")
      );
      if (panel && segNodes().length === 0) {
        const tab = qa('button, [role="tab"], [role="button"], yt-chip-cloud-chip-renderer, tp-yt-paper-tab, a', panel)
          .find((c) => /^(transcript|transkript)$/i.test(label(c)));
        if (tab) tab.click();
      }
    }
  }

  let out;
  if (segNodes().length) {
    const t = collect();
    out = { ok: true, uzunluk: t.length, ornek: t.slice(0, 120) };
  } else {
    out = {
      ok: false,
      paneller: qa("ytd-engagement-panel-section-list-renderer").map(
        (p) => (p.getAttribute("target-id") || "?") + ":" + (p.getAttribute("visibility") || "?")
      ),
      transcriptButonlari: qa('button, [role="button"], ytd-button-renderer').map(label).filter((t) => /transcript|transkript/i.test(t)).slice(0, 8),
    };
  }
  console.log("SONUC:", JSON.stringify(out));
  return out;
})();
