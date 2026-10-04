const HOST = "com.curaarda.ytsummary";
const YT_RE = /(youtube\.com\/(watch|shorts|live|embed)|youtu\.be\/)/i;

function isYouTube(url) {
  return !!url && YT_RE.test(url);
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "yt-ozetle",
    title: "YouTube Özetle",
    contexts: ["link", "page", "video"],
    documentUrlPatterns: ["*://*.youtube.com/*", "*://youtu.be/*"],
    targetUrlPatterns: ["*://*.youtube.com/*", "*://youtu.be/*"]
  });
  chrome.contextMenus.create({
    id: "yt-transcript",
    title: "Full Transkript",
    contexts: ["link", "page", "video"],
    documentUrlPatterns: ["*://*.youtube.com/*", "*://youtu.be/*"],
    targetUrlPatterns: ["*://*.youtube.com/*", "*://youtu.be/*"]
  });
});

function notify(title, message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl:
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
    title: title,
    message: message
  });
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const mode = info.menuItemId === "yt-transcript" ? "transcript" : "summary";
  if (info.menuItemId !== "yt-ozetle" && info.menuItemId !== "yt-transcript") return;
  const etiket = mode === "transcript" ? "Full Transkript" : "YouTube Özetle";

  let url = info.linkUrl || info.srcUrl || info.pageUrl || (tab && tab.url) || "";
  if (!isYouTube(url) && tab && isYouTube(tab.url)) url = tab.url;
  if (!isYouTube(url)) {
    notify(etiket, "Geçerli bir YouTube linki bulunamadı.");
    return;
  }

  notify(etiket, "Başladı: transcript çekiliyor…");
  chrome.runtime.sendNativeMessage(HOST, { url: url, mode: mode }, (resp) => {
    if (chrome.runtime.lastError) {
      notify(etiket + " — Hata", "Yerel bağlantı kurulamadı: " + chrome.runtime.lastError.message);
      return;
    }
    if (resp && resp.ok) {
      notify(etiket + " — Hazır ✅", resp.title || "Doküman oluşturuldu.");
    } else {
      notify(etiket + " — Hata", (resp && resp.error) || "Bilinmeyen hata.");
    }
  });
});
