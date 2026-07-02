# PROSICHT — Endüstriyel Taşınma Ajanı

İnternetten endüstriyel taşınma sinyallerini otomatik olarak tespit eden, iş açısından önemini puanlayan ve web arayüzü ile e-posta bildirimleri aracılığıyla eyleme dönüştürülebilir istihbarat sunan otonom bir yapay zeka destekli haber tarama ajanı.

**Pro Sicht Yapay Zeka Yazılım Ar-Ge ve Proje Danışmanlık Sanayi ve Ticaret A.Ş** bünyesinde staj projesi kapsamında geliştirilmiştir.

---

## Ne Yapıyor?

Sistem, Avrupa'daki endüstriyel olayları — fabrika taşımaları, tesis kapanışları, yeni yatırımlar ve genişlemeler — tespit etmek amacıyla haber RSS beslemelerini sürekli olarak izler. Tespit edilen her olay için yapay zeka kullanılarak yapısal veri çıkarılır ve BIOS'un endüstriyel denetim ve makine görüşü hizmetleri açısından fırsatın ne kadar değerli olduğunu ölçen bir **BIOS-uygunluk skoru (0–100)** hesaplanır.

80 ve üzeri puan alan olaylar, abone olan kullanıcılara otomatik olarak e-posta bildirimi gönderir — bu sayede CRM'de potansiyel müşteri (lead) oluşturma süreci simüle edilmiş olur.

---

## Özellikler

- **Otomatik RSS izleme** — birden fazla yapılandırılabilir haber beslemesini eş zamanlı olarak tarar
- **Yapay zeka destekli veri çıkarımı** — ham makalelerden şirket, konum, sektör, yatırım tutarı ve istihdam verilerini çıkarmak için GPT-4o-mini kullanır
- **BIOS-uygunluk skorlaması** — her olayı 5 kriter üzerinden değerlendirir: Teknik Karmaşıklık, Taşınma Kesinliği, Coğrafi Uyum, Sektör Uyumu ve Zaman Penceresi
- **Avrupa coğrafi filtresi** — Avrupa dışındaki olayları otomatik olarak filtreler
- **Tekilleştirme (deduplication)** — URL tabanlı ve içerik tabanlı tekilleştirme ile mükerrer kayıtlar önlenir
- **İlk 10 sıralama** — her çalıştırmada en yüksek puanlı 10 fırsatı çıktı olarak verir
- **Streamlit arayüzü** — İngilizce/Türkçe çeviri desteği olan interaktif web arayüzü
- **RSS besleme yönetimi** — arayüzden doğrudan RSS beslemesi ekleme veya silme
- **E-posta CRM bildirimleri** — yüksek skorlu olaylar (80+) için otomatik e-posta bildirimleri
- **Makale özetleri** — her makale için yapay zeka tarafından oluşturulan 2–3 cümlelik özetler

> **Not — PostgreSQL Veritabanı:** Sistem, tüm olayları kalıcı olarak saklamak için isteğe bağlı bir PostgreSQL veritabanı entegrasyonuna sahiptir. Varsayılan olarak bu özellik kapalıdır. Etkinleştirmek için aşağıdaki kurulum adımlarını takip edin ve `src/news_fetch.py` dosyasındaki ilgili yorum satırlarını açın.

---

## Proje Yapısı

```
prosicht-agent/
│
├── src/                         # Tüm Python betikleri
│   ├── news_fetch.py            # Ana çekme, çıkarım ve puanlama betiği
│   ├── dashboard.py             # Streamlit web arayüzü
│   ├── database.py              # PostgreSQL bağlantısı ve kayıt mantığı (isteğe bağlı)
│   └── crm_alert.py             # Yüksek skorlu olaylar için e-posta bildirim sistemi
│
├── data/                        # Otomatik oluşturulan veri dosyaları
│   ├── top10_events.json        # En son çalıştırmadan ilk 10 sonuç
│   ├── industry_events.json     # En son çalıştırmadan tüm sonuçlar
│   ├── industry_events.csv      # CSV dışa aktarımı
│   ├── rss_feeds.json           # Kullanıcı tarafından yapılandırılan RSS besleme listesi
│   ├── alert_emails.json        # Abone olan e-posta adresleri
│   └── seen_urls.json           # Tekilleştirme önbelleği
│
├── docs/                        # Dokümantasyon
│   └── technical_report.docx   # Teknik proje raporu
│
├── requirements.txt             # Python bağımlılıkları
├── .env                         # API anahtarları ve kimlik bilgileri (git'e dahil edilmez)
├── .gitignore                   # Git'ten hariç tutulan dosyalar
└── README.md                    # Bu dosya
```

---

## Teknoloji Yığını

| Bileşen | Teknoloji |
|---|---|
| Programlama Dili | Python 3.10+ |
| Yapay Zeka / LLM | OpenAI GPT-4o-mini |
| RSS Ayrıştırma | feedparser |
| Web Çekme | requests + BeautifulSoup4 |
| Arayüz | Streamlit |
| Veritabanı (isteğe bağlı) | PostgreSQL + psycopg2 |
| E-posta Bildirimleri | smtplib (Gmail SMTP) |
| Ortam Değişkenleri | python-dotenv |

---

## Kurulum

### 1. Depoyu klonlayın

```bash
git clone https://github.com/elaa001/prosicht-agent.git
cd prosicht-agent
```

### 2. Bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
```

### 3. Ortam değişkenlerini ayarlayın

Proje kök dizininde bir `.env` dosyası oluşturun:

```env
OPENAI_API_KEY=openai_api_anahtariniz

# E-posta bildirimleri için
ALERT_EMAIL=eposta@gmail.com
ALERT_EMAIL_PASSWORD=gmail_uygulama_sifreniz

# Veritabanı (isteğe bağlı)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=prosicht
DB_USER=postgres
DB_PASSWORD=postgresql_sifreniz
```

### 4. PostgreSQL kurulumu (isteğe bağlı)

Veritabanı özelliğini kullanmak istiyorsanız:

- https://www.postgresql.org/download/ adresinden PostgreSQL'i indirin ve kurun
- pgAdmin'i açın ve `prosicht` adında yeni bir veritabanı oluşturun
- Sistem ilk çalıştırmada `events` tablosunu otomatik olarak oluşturacaktır

Ardından `src/news_fetch.py` dosyasında şu adımları uygulayın:

**Dosyanın en üstüne şu import satırını ekleyin:**
```python
from database import create_table, save_event
```

**`run_fetch()` fonksiyonunun başındaki yorum satırını açın:**
```python
# KAPALI (varsayılan):
# create_table()

# AÇIK (veritabanı etkin):
create_table()
```

**`events.append(event)` satırının hemen altındaki yorum satırını açın:**
```python
# KAPALI (varsayılan):
# save_event(event)

# AÇIK (veritabanı etkin):
save_event(event)
```

### 5. Gmail Uygulama Şifresi ayarlayın

E-posta bildirimlerinin çalışması için:
1. myaccount.google.com → Güvenlik → 2 Adımlı Doğrulama'yı etkinleştirin
2. myaccount.google.com/apppasswords adresine gidin
3. "PROSICHT" adında yeni bir uygulama şifresi oluşturun
4. Oluşturulan 16 karakterli şifreyi `.env` dosyasına `ALERT_EMAIL_PASSWORD` olarak ekleyin

---

## Kullanım

> **Önemli:** Tüm komutlar her zaman proje kök dizininden (`prosicht-agent/`) çalıştırılmalıdır.

### Arayüzü başlatın

```bash
streamlit run src/dashboard.py
```

`http://localhost:8501` adresinde açılır

### Çekme betiğini doğrudan çalıştırın

```bash
python src/news_fetch.py
```

### Arayüz butonları

| Buton | Ne Yapar? |
|---|---|
| **Run fetch now** | Yalnızca daha önce görülmemiş yeni makaleleri çeker (hızlı, günlük kullanım için) |
| **Clear cache & refetch all** | Görülen URL önbelleğini siler ve her şeyi sıfırdan yeniden işler |
| **Reset to default feeds** | Orijinal 5 varsayılan RSS beslemesini geri yükler |

---

## BIOS-Uygunluk Skoru Nasıl Çalışır?

Her olay 5 kriter üzerinden değerlendirilir; her kriter 0–20 puan değerindedir (toplam 0–100):

| Kriter | Açıklama | Maks. Puan |
|---|---|---|
| **T** — Teknik Karmaşıklık | Üretim süreci ne kadar karmaşık? Yarı iletken ve otomotiv en yüksek puanı alır | 20 |
| **R** — Taşınma Kesinliği | Olay doğrulanmış mı yoksa sadece söylenti mi? | 20 |
| **G** — Coğrafi Uyum | Hedef konum Avrupa'da mı? | 20 |
| **S** — Sektör Uyumu | BIOS bu sektöre hizmet veriyor mu? Otomotiv ve endüstriyel makineler en yüksek puanı alır | 20 |
| **U** — Zaman Penceresi | Fırsat ne kadar acil? Yakın vadeli olaylar en yüksek puanı alır | 20 |

### Skor eşikleri

| Skor | Aksiyon | Anlamı |
|---|---|---|
| 80–100 | `reach_out` | Yüksek öncelik — şirketle hemen iletişime geçin |
| 50–79 | `monitor` | Orta öncelik — gelişmeleri takip edin |
| 0–49 | `tender_watch` | Düşük öncelik — ihale fırsatlarını izleyin |

---

## Tespit Edilen Olay Tipleri

| Tip | Açıklama |
|---|---|
| `relocation` | Üretimin bir konumdan diğerine taşınması |
| `closure` | Fabrika veya tesisin kalıcı olarak kapatılması |
| `expansion` | Mevcut bir tesisin büyütülmesi |
| `greenfield` | Sıfırdan inşa edilen yeni bir tesis |
| `brownfield` | Mevcut bir tesisin yenilenmesi veya yeniden kullanılması |
| `production_transfer` | Belirli bir üretim hattının başka bir tesise taşınması |
| `fdi_announcement` | Yabancı doğrudan yatırım duyurusu |
| `supply_chain` | Tedarik zinciri yeniden yapılandırması |

---

## Varsayılan Veri Kaynakları

Sistem varsayılan olarak Avrupa endüstriyel haberlerini hedef alan Google News RSS beslemelerini kullanır:

- Avrupa'da fabrika taşıması
- Avrupa'da tesis kapanışı
- Avrupa'da üretim yatırımı
- Almanya, Fransa, Polonya, İtalya'da fabrika genişlemesi
- Avrupa'da otomotiv tesisi kapanışı

Kullanıcılar arayüz kenar çubuğu üzerinden herhangi bir geçerli RSS besleme URL'si ekleyebilir.

---

## Çıktı Dosyaları

### `data/top10_events.json`
En son çalıştırmadan en yüksek puanlı 10 olay. Arayüz tarafından kullanılır.

### `data/industry_events.json`
En son çalıştırmada tespit edilen tüm olaylar, tam çıkarılan verilerle birlikte.

### `data/industry_events.csv`
Raporlama için tüm olayların elektronik tablo dışa aktarımı.

### PostgreSQL `events` tablosu (isteğe bağlı)
Tespit edilen tüm olayların kalıcı tarihsel kaydı. Hiçbir zaman üzerine yazılmaz — tüm çalıştırmalarda zaman içinde büyür.

---

## .gitignore Önerisi

```
.env
__pycache__/
*.pyc
data/seen_urls.json
data/industry_events.json
data/industry_events.csv
data/top10_events.json
data/alert_emails.json
```

> `data/rss_feeds.json` git'e dahil edilmelidir — varsayılan besleme listesini içerir.

---

## Geliştirme Yol Haritası

- [x] Adım 1 — Manuel araştırma ve olay tespiti
- [x] Adım 2 — RSS çekme ve HTML normalleştirme
- [x] Adım 3 — Yapay zeka destekli yapısal veri çıkarımı
- [x] Adım 4 — BIOS-uygunluk fırsat skorlaması
- [x] Adım 5 — Otomasyon döngüsü, tekilleştirme, CSV/JSON dışa aktarım
- [x] Adım 6 — PostgreSQL veritabanı (isteğe bağlı), CRM e-posta bildirimleri, Streamlit arayüzü

---

## Lisans

Bu proje, Pro Sicht Yapay Zeka Yazılım Ar-Ge ve Proje Danışmanlık Sanayi ve Ticaret A.Ş bünyesinde staj projesi kapsamında geliştirilmiştir. Tüm hakları saklıdır.

---

## Geliştirici

PROSICHT stajyeri tarafından geliştirilmiştir — 2026
