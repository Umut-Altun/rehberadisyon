# RehberPOS - İşletme Yönetim Sistemi

RehberPOS, restoran ve işletmeler için çok kiracılı (multi-tenant) bir yönetim sistemidir. Sipariş takibi, stok yönetimi, müşteri ilişkileri ve raporlama özelliklerini tek bir platformda sunar.

## Özellikler

- **Çok Kiracılı Mimari**: Tek bir kurulumda birden fazla işletme yönetimi
- **Rol Tabanlı Erişim Kontrolü**: Farklı kullanıcı rolleri (işletme sahibi, yönetici, garson, kasiyer, mutfak)
- **Sipariş Yönetimi**: Masalara ve paket siparişlere göre takip
- **Ürün ve Kategori Yönetimi**: Menü oluşturma ve düzenleme
- **Müşteri Yönetimi**: Müşteri bilgilerini saklama ve sipariş geçmişi
- **Raporlama**: Günlük, aylık ve yıllık satış raporları
- **Mutfak Ekranı**: Sipariş hazırlama süreci takibi

## Kurulum

### Gereksinimler

- Python 3.9 veya üstü
- PostgreSQL 12 veya üstü
- pip ve virtualenv

### Yerel Geliştirme Ortamı

1. Repo'yu klonlayın ve proje dizinine girin:
   ```
   git clone https://github.com/username/RehberPOS.git
   cd RehberPOS
   ```

2. Sanal ortam oluşturun ve etkinleştirin:
   ```
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

3. Bağımlılıkları yükleyin:
   ```
   pip install -r requirements.txt
   ```

4. Örnek .env dosyasını kopyalayın ve düzenleyin:
   ```
   cp .env.example .env
   # .env dosyasını düzenleyin
   ```

5. Veritabanı migration'larını uygulayın:
   ```
   python manage.py migrate
   ```

6. Statik dosyaları toplayın:
   ```
   python manage.py collectstatic
   ```

7. Geliştirme sunucusunu başlatın:
   ```
   python manage.py runserver
   ```

### Üretim Ortamı Kurulumu

1. Tüm bağımlılıkları production modunda yükleyin:
   ```
   pip install -r requirements.txt
   ```

2. `.env` dosyasını üretim ortamı için yapılandırın:
   - `DEBUG=False` olarak ayarlayın
   - Güçlü bir `SECRET_KEY` belirleyin
   - `ALLOWED_HOSTS` içine domain adınızı ekleyin
   - PostgreSQL için `DATABASE_URL` veya bağlantı parametrelerini ayarlayın

3. Veritabanı migration'larını uygulayın:
   ```
   python manage.py migrate
   ```

4. Statik dosyaları toplayın:
   ```
   python manage.py collectstatic --no-input
   ```

5. WSGI sunucusunu (gunicorn) başlatın:
   ```
   gunicorn restaurant_management.wsgi:application --bind 0.0.0.0:8000
   ```

6. Nginx veya benzer bir reverse proxy kullanın.

## Sistem Mimarisi

RehberPOS, Django web çatısı üzerine inşa edilmiş ve PostgreSQL veritabanı kullanan bir uygulamadır:

- **Multi-Tenant Yapı**: Her işletme izole bir şekilde kendi verilerine erişebilir
- **WSGI + Whitenoise**: Statik dosya sunumu için optimize edilmiş yapı
- **PostgreSQL**: Güçlü ve ölçeklenebilir veri depolama
- **Rol Tabanlı Erişim**: İşletme içinde farklı rol ve izinler

## Katkı Sağlama

Katkıda bulunmak için lütfen:

1. Repo'yu fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add some amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## Lisans

Bu proje MIT lisansı ile lisanslanmıştır. 