from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
from .views import tenant_views
from .views.auth_views import logout_view

app_name = 'pos'

urlpatterns = [
    # Kimlik Doğrulama
    path('logout/', logout_view, name='logout'),
    path('register/', tenant_views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('select-tenant/', views.select_tenant, name='select_tenant'),

    # İşletme Yönetimi
    path('isletme/', tenant_views.tenant_detail, name='tenant_detail'),
    path('isletme/yeni/', tenant_views.tenant_create, name='tenant_create'),
    path('isletme/duzenle/', tenant_views.tenant_edit, name='tenant_edit'),
    path('isletme/sil/', tenant_views.tenant_delete, name='tenant_delete'),
    
    # Ana Sayfa
    path('', views.index, name='index'),
    
    # Kullanıcı Yönetimi
    path('kullanicilar/', views.user_list, name='user_list'),
    path('kullanici/yeni/', views.user_create, name='user_create'),
    path('kullanici/<int:user_id>/duzenle/', views.user_edit, name='user_edit'),
    path('kullanici/<int:user_id>/sil/', views.user_delete, name='user_delete'),
    
    # Masa İşlemleri
    path('masalar/', views.table_list, name='table_list'),
    path('masa/yeni/', views.table_create, name='table_create'),
    path('masa/<int:table_id>/', views.table_detail, name='table_detail'),
    path('masa/<int:table_id>/ac/', views.table_open, name='table_open'),
    path('masalar/yonetim/', views.table_management, name='table_management'),
    # path('masalar/<int:table_id>/duzenle/', views.table_edit, name='table_edit'),  # Masa düzenleme devre dışı bırakıldı
    path('masalar/<int:table_id>/sil/', views.table_delete, name='table_delete'),
    path('masalar/tasi/', views.table_transfer, name='table_transfer'),
    
    # Sipariş İşlemleri
    path('siparisler/', views.order_list, name='order_list'),
    path('paket-siparisler/', views.takeaway_orders, name='takeaway_orders'),
    path('siparis/yeni/', views.order_create, name='order_create'),
    path('siparis/<int:order_id>/', views.order_detail, name='order_detail'),
    path('siparis/<int:order_id>/sil/', views.order_delete, name='order_delete'),
    path('siparis/<int:order_id>/iptal/', views.order_cancel, name='order_cancel'),
    path('siparis/urun/sil/', views.order_item_delete, name='order_item_delete'),
    path('api/siparisler/<int:order_id>/durum/', views.order_status_update, name='order_status_update'),
    
    # Müşteri İşlemleri
    path('musteriler/', views.customer_list, name='customer_list'),
    path('musteri/yeni/', views.customer_create, name='customer_create'),
    path('musteri/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('musteri/<int:customer_id>/duzenle/', views.customer_edit, name='customer_edit'),
    path('musteri/<int:customer_id>/sil/', views.customer_delete, name='customer_delete'),
    
    # Ürün İşlemleri
    path('urunler/', views.product_list, name='product_list'),
    path('urun/yeni/', views.product_create, name='product_create'),
    path('urun/<int:product_id>/', views.product_detail, name='product_detail'),
    path('urun/<int:product_id>/duzenle/', views.product_edit, name='product_edit'),
    path('urun/<int:product_id>/sil/', views.product_delete, name='product_delete'),
    path('urun/<int:pk>/durum/', views.product_toggle_availability, name='product_toggle_availability'),
    
    # Kategori İşlemleri
    path('kategoriler/', views.category_list, name='category_list'),
    path('kategori/yeni/', views.category_create, name='category_create'),
    path('kategori/<int:category_id>/duzenle/', views.category_edit, name='category_edit'),
    path('kategori/<int:category_id>/sil/', views.category_delete, name='category_delete'),
    
    # Ödeme İşlemleri
    path('odeme/<int:order_id>/', views.payment_create, name='payment_create'),
    path('odeme/<int:payment_id>/detay/', views.payment_detail, name='payment_detail'),
    path('odeme/<int:payment_id>/iade/', views.payment_refund, name='payment_refund'),
    path('odeme/<int:payment_id>/pdf/', views.payment_pdf, name='payment_pdf'),
    
    # Raporlar
    path('raporlar/', views.reports, name='reports'),
    path('raporlar/temizle/', views.database_cleanup, name='database_cleanup'),
    path('raporlar/gunluk/', views.daily_report, name='daily_report'),
    path('raporlar/aylik/', views.monthly_report, name='monthly_report'),
    path('raporlar/yillik/', views.yearly_report, name='yearly_report'),
    path('raporlar/urunler/', views.product_report, name='product_report'),
    path('raporlar/masalar/', views.table_report, name='table_report'),
    path('raporlar/excel/', views.export_excel, name='export_excel'),
    path('raporlar/pdf/', views.export_pdf, name='export_pdf'),
    path('reports/staff-sales/', views.staff_sales_report, name='staff_sales_report'),
    
    # Mutfak Ekranı
    path('mutfak/', views.kitchen_display, name='kitchen_display'),
    
    # API Endpoints
    path('api/masalar/', views.table_list_api, name='table_list_api'),
    path('api/siparisler/', views.order_list_api, name='order_list_api'),
    path('api/urunler/', views.product_list_api, name='product_list_api'),
    path('api/musteriler/', views.customer_list_api, name='customer_list_api'),
    
    # QR Kod ve Menü URL'leri
    path('menu/qr/', views.generate_menu_qr, name='generate_menu_qr'),
    path('menu/', views.public_menu, name='public_menu'),
] 