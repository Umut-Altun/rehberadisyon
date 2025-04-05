from django.contrib import admin
from .models import Category, Product, Table, Customer, Order, OrderItem, Payment

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'category__name')

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'floor', 'capacity', 'is_occupied', 'created_at']
    list_filter = ['floor', 'is_occupied']
    search_fields = ['number']
    ordering = ['floor', 'number']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'phone', 'email')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'table', 'status', 'order_type', 'total_amount', 'created_at')
    list_filter = ('status', 'order_type')
    search_fields = ('id', 'customer__name', 'table__number')
    date_hierarchy = 'created_at'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'unit_price', 'get_total_price')
    list_filter = ('order__status',)
    search_fields = ('order__id', 'product__name')
    
    def get_total_price(self, obj):
        return obj.quantity * obj.unit_price
    get_total_price.short_description = 'Toplam Fiyat'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'payment_type', 'amount', 'status', 'created_at')
    list_filter = ('payment_type', 'status')
    search_fields = ('order__id',)
    date_hierarchy = 'created_at'
