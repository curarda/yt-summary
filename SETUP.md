# YouTube Özetle — Kurulum

Sağ tık → **YouTube Özetle**: seçili bir YouTube linkini Claude ile Türkçe özetleyip
doğrudan Google Docs'a native doküman olarak yükler.

Kurulum bitti sayılır; geriye **2 elle adım** kaldı.

---

## 1) Claude API anahtarını Keychain'e koy

Anahtarın hiçbir dosyada düz metin durmaz; macOS Keychain'de saklanır.
Aşağıdaki komutta `sk-ant-...` yerine kendi anahtarını yazıp çalıştır:

```bash
security add-generic-password -a "$USER" -s "yt-summary-anthropic" -w 'sk-ant-BURAYA-ANAHTARIN' -U
```

Kontrol:

```bash
security find-generic-password -s "yt-summary-anthropic" -w | cut -c1-10
```

`sk-ant-...` görürsen tamamdır.

---

## 2) Google OAuth istemcisi oluştur (bir kerelik, ~5 dk)

Özetin **native Google Doc** olarak yüklenmesi için Google'a "bu uygulamaya izin
ver" demen gerekiyor. Tek seferlik:

1. https://console.cloud.google.com/ → üstten bir **proje oluştur** (veya var olanı seç).
2. **APIs & Services → Library** → "Google Drive API" ara → **Enable**.
3. **APIs & Services → OAuth consent screen**:
   - User type: **External** → Create
   - Uygulama adı: `YouTube Özetle`, destek e‑postası: kendi e‑postan
   - **Audience/Test users** bölümüne kendi Google hesabını **test user** olarak ekle
   - (Yayınlamana gerek yok, "Testing" modunda kalabilir.)
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Application type: **Desktop app** → Create
   - Oluşan istemci için **Download JSON**.
5. İndirdiğin dosyayı tam olarak şu yola koy:

```bash
mv ~/Downloads/client_secret_*.json "$HOME/.config/yt-summary/credentials.json"
```

İlk çalıştırmada tarayıcı açılıp "izin ver" diye soracak; onayladıktan sonra
token önbelleğe alınır (`~/.config/yt-summary/token.json`) ve bir daha sormaz.

---

## Kullanım

- Herhangi bir uygulamada bir YouTube linkini **seç → sağ tık → YouTube Özetle**.
  (İlk seferde çıkmazsa: Sistem Ayarları → Klavye → Klavye Kısayolları →
  Hizmetler / Services listesinde "YouTube Özetle"nin işaretli olduğundan emin ol.)
- Alternatif olarak linki kopyalayıp terminalden de çalıştırabilirsin:

```bash
"<proje-klasörü>/.venv/bin/python" "<proje-klasörü>/yt_summarize.py" "https://www.youtube.com/watch?v=VIDEO"
```

Argüman vermezsen panodaki (kopyaladığın) linki kullanır.

---

## Sorun giderme

- Her çalıştırmanın kaydı: `~/.config/yt-summary/last-run.log`
- Bildirim olarak hata görürsen bu log dosyasına bak.
- Model değiştirmek istersen: `YT_SUMMARY_MODEL` ortam değişkeni (varsayılan `claude-sonnet-5`).
