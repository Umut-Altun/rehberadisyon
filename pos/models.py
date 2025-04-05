from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .managers import TenantManager

class Tenant(models.Model):
    """İşletmeleri temsil eden model"""
    name = models.CharField(max_length=200, verbose_name='İşletme Adı')
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owned_tenant', verbose_name='İşletme Sahibi')
    address = models.TextField(blank=True, null=True, verbose_name='Adres')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Telefon')
    logo = models.ImageField(upload_to='tenant_logos/', blank=True, null=True, verbose_name='Logo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Kullanıcılar ile many-to-many ilişki
    users = models.ManyToManyField(User, through='TenantUser', related_name='tenants')
    
    # Tenant modeli TenantManager kullanmamalı, yoksa döngüsel bağımlılık oluşur
    objects = models.Manager()
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'İşletme'
        verbose_name_plural = 'İşletmeler'
        ordering = ['name']

class TenantUser(models.Model):
    """Kullanıcı-İşletme ilişkisi modeli"""
    USER_ROLE_CHOICES = [
        ('owner', 'İşletme Sahibi - Tam yönetim yetkisi'),
        ('manager', 'Yönetici - Raporlama ve personel yönetimi yapabilir'),
        ('waiter', 'Garson - Sipariş alma ve masa yönetimi yapabilir'),
        ('cashier', 'Kasiyer - Ödeme alma ve sipariş takibi yapabilir'),
        ('kitchen', 'Mutfak - Sipariş hazırlama ve takibi yapabilir'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_memberships')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='user_memberships')
    role = models.CharField(max_length=20, choices=USER_ROLE_CHOICES, default='waiter', verbose_name='Rol')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'İşletme Kullanıcısı'
        verbose_name_plural = 'İşletme Kullanıcıları'
        unique_together = ('user', 'tenant')  # Bir kullanıcı bir işletmeye sadece bir kez eklenebilir
        
    def __str__(self):
        return f"{self.user.username} - {self.tenant.name} ({self.get_role_display()})"

class BaseModel(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='%(class)ss', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Managers
    objects = TenantManager()  # Otomatik tenant filtreleme yapan manager
    all_objects = models.Manager()  # Tüm objelere erişim için (admin kullanımı için)

    class Meta:
        abstract = True

class Table(BaseModel):
    number = models.IntegerField()
    capacity = models.IntegerField(default=4)
    floor = models.IntegerField(default=1, verbose_name='Kat')
    is_occupied = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['floor', 'number']
        indexes = [
            models.Index(fields=['floor', 'is_occupied']),
        ]
        unique_together = ['tenant', 'number']  # Masa numarası tenant bazında unique olmalı
    
    def __str__(self):
        return f"Masa {self.number} (Kat {self.floor})"

    def has_ready_orders(self):
        """Masada hazır bekleyen sipariş var mı kontrol eder"""
        return self.order_set.filter(status='ready').exists()

class Category(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'pos_categories'
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategoriler'
        ordering = ['name']
        unique_together = ['tenant', 'name']  # Kategori adı tenant bazında unique olmalı

class Product(BaseModel):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'pos_products'
        verbose_name = 'Ürün'
        verbose_name_plural = 'Ürünler'
        ordering = ['name']

class Customer(BaseModel):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def total_orders(self):
        """Toplam sipariş sayısı"""
        return self.orders.count()
    
    @property
    def total_spent(self):
        """Toplam harcama tutarı"""
        return self.orders.aggregate(total=models.Sum('total_amount'))['total'] or 0
    
    @property
    def average_order_amount(self):
        """Ortalama sipariş tutarı"""
        if self.total_orders > 0:
            return self.total_spent / self.total_orders
        return 0
    
    @property
    def last_order(self):
        """Son sipariş"""
        return self.orders.first()  # Meta'da ordering ['-created_at'] olduğu için first() en son siparişi getirir

class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('preparing', 'Hazırlanıyor'),
        ('ready', 'Hazır'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
    ]
    ORDER_TYPE_CHOICES = [
        ('table', 'Masa Siparişi'),
        ('takeaway', 'Paket Sipariş'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Personel')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='table', db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'order_type']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['table', 'status']),
            models.Index(fields=['staff', 'created_at']),
        ]

class OrderItem(BaseModel):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['order', 'product']),
            models.Index(fields=['product', 'created_at']),
        ]

class Payment(BaseModel):
    PAYMENT_TYPE_CHOICES = [
        ('cash', 'Nakit'),
        ('credit_card', 'Kredi Kartı'),
        ('debit_card', 'Banka Kartı'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('completed', 'Tamamlandı'),
        ('refunded', 'İade Edildi'),
        ('failed', 'Başarısız'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['payment_type', 'status']),
        ]
