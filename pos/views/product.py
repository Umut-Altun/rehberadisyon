from django.contrib.auth.decorators import login_required
from ..models import Product, Category, OrderItem
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from ..forms import ProductForm
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, F
import xlsxwriter
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from django.db.models.deletion import transaction
import qrcode
import qrcode.image.svg
from django.urls import reverse
from django.contrib import messages

@login_required
def generate_menu_qr(request):
    """QR kod oluşturma görünümü"""
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
    
    # Menü URL'sini al - tenant ID'sini ekle
    menu_url = request.build_absolute_uri(
        f"{reverse('pos:public_menu')}?tenant={tenant.id}"
    )
    
    # QR kod oluştur
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(menu_url)
    qr.make(fit=True)

    # QR kodu PNG formatında oluştur
    img = qr.make_image(fill_color="black", back_color="white")
    
    # BytesIO buffer'ına kaydet
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # HTTP response olarak gönder
    response = HttpResponse(buffer, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{tenant.name}_menu_qr.png"'
    return response



def public_menu(request):
    """Halka açık menü görünümü"""
    # URL'den işletme ID'si alınmalı
    tenant_id = request.GET.get('tenant')
    
    if not tenant_id:
        return render(request, 'pos/public_menu.html', {
            'error': 'İşletme bilgisi eksik',
            'message': 'Bu QR kod geçersiz veya eksik. Lütfen işletmeden yeni bir QR kod alın.'
        })
    
    try:
        from ..models import Tenant
        tenant = Tenant.objects.get(id=tenant_id)
        
        # Aktif ürünleri kategorilerine göre grupla
        categories = Category.objects.filter(tenant=tenant)
        products = Product.objects.filter(
            is_available=True, 
            tenant=tenant,
            category__isnull=False  # Kategorisi olmayan ürünleri hariç tut
        ).select_related('category')
        
        # Ürünleri kategorilere göre grupla
        products_by_category = {}
        for category in categories:
            category_products = products.filter(category=category)
            if category_products.exists():
                products_by_category[category] = category_products
        
        context = {
            'business': tenant,  # Template'de business olarak kullanıyoruz
            'categories': categories,
            'products_by_category': products_by_category,
        }
        return render(request, 'pos/public_menu.html', context)
        
    except Tenant.DoesNotExist:
        return render(request, 'pos/public_menu.html', {
            'error': 'İşletme Bulunamadı',
            'message': 'Belirtilen işletme bulunamadı. Lütfen işletmeden yeni bir QR kod alın.'
        })
    except Exception as e:
        return render(request, 'pos/public_menu.html', {
            'error': 'Sistem Hatası',
            'message': 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.'
        })

# Ürün İşlemleri
@login_required
def product_list(request):
    """Ürün listesi görünümü"""
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
        
    # Filtreleme parametrelerini al
    category_id = request.GET.get('category')
    search_query = request.GET.get('search', '').strip()
    
    # Temel sorgu - tenant'a göre filtrele
    products = Product.objects.select_related('category').filter(tenant=tenant)
    
    # Kategori filtresi
    if category_id and category_id != 'all':
        products = products.filter(category_id=category_id)
    
    # Arama filtresi
    if search_query and search_query.lower() != 'none':
        products = products.filter(name__icontains=search_query)
    
    # Kategorileri al - tenant'a göre filtrele
    categories = Category.objects.filter(tenant=tenant)
    
    # Ürünleri kategorilerine göre grupla
    products_by_category = {}
    if category_id and category_id != 'all':
        # Sadece seçili kategorideki ürünleri göster
        try:
            selected_category = Category.objects.get(id=category_id, tenant=tenant)
            products_by_category[selected_category] = products
        except Category.DoesNotExist:
            pass
    else:
        # Tüm kategorilerdeki ürünleri göster
        for category in categories:
            category_products = products.filter(category=category)
            if category_products.exists():
                products_by_category[category] = category_products
    
    context = {
        'categories': categories,
        'products_by_category': products_by_category,
        'selected_category': category_id,
        'search_query': search_query if search_query.lower() != 'none' else ''
    }
    return render(request, 'pos/product_list.html', context)

@login_required
def product_create(request):
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
        
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, tenant=tenant)
        if form.is_valid():
            product = form.save(commit=False)
            product.tenant = tenant
            product.save()
            messages.success(request, "Ürün başarıyla oluşturuldu.")
            return redirect('pos:product_list')
    else:
        form = ProductForm(tenant=tenant)
    
    return render(request, 'pos/product_create.html', {'form': form})

@login_required
def product_detail(request, product_id):
    """Ürün detay görünümü"""
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
    
    # Ürün tenant kontrolü
    product = get_object_or_404(Product.objects.select_related('category'), pk=product_id, tenant=tenant)
    
    # Sipariş geçmişi
    order_items = OrderItem.objects.filter(product=product, order__tenant=tenant).select_related('order', 'order__customer')

    # İstatistikler
    total_ordered = order_items.aggregate(total=Sum('quantity'))['total'] or 0
    total_revenue = order_items.aggregate(
        total=Sum(F('quantity') * F('unit_price'))
    )['total'] or 0
    
    context = {
        'product': product,
        'order_items': order_items,
        'total_ordered': total_ordered,
        'total_revenue': total_revenue
    }
    return render(request, 'pos/product_detail.html', context)



@login_required
def product_edit(request, product_id):
    """Ürün düzenleme görünümü"""
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
    
    # Ürün tenant kontrolü
    product = get_object_or_404(Product, pk=product_id, tenant=tenant)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, tenant=tenant)
        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                messages.success(request, "Ürün başarıyla güncellendi.")
                return redirect('pos:product_list')
            except Exception as e:
                messages.error(request, f"Ürün güncellenemedi: {str(e)}")
                return redirect('pos:product_list')
    else:
        form = ProductForm(instance=product, tenant=tenant)
    
    context = {
        'form': form,
        'product': product
    }
    return render(request, 'pos/product_edit.html', context)


@login_required
def product_delete(request, product_id):
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
    
    # Ürün tenant kontrolü
    product = get_object_or_404(Product, id=product_id, tenant=tenant)
    
    if request.method == 'POST':
        try:
            product.delete()
            messages.success(request, "Ürün başarıyla silindi.")
            return redirect('pos:product_list')
        except Exception as e:
            messages.error(request, f"Ürün silinemedi: {str(e)}")
            return redirect('pos:product_list')
    
    return render(request, 'pos/product_confirm_delete.html', {'product': product})

@login_required
def product_toggle_availability(request, pk):
    if request.method == 'POST':
        try:
            product = Product.objects.get(pk=pk)
            product.is_available = not product.is_available
            product.save()
            return JsonResponse({
                'status': 'success',
                'is_available': product.is_available
            })
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found'
            })
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }) 

@login_required
def product_report(request):
    """Ürün bazlı rapor"""
    # Filtreleri al
    category_id = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export_format = request.GET.get('export')
    
    # Temel sorgu
    order_items = OrderItem.objects.filter(
        order__status='completed'
    ).select_related(
        'product', 'product__category', 'order'
    )
    
    # Filtreleri uygula
    if category_id:
        order_items = order_items.filter(product__category_id=category_id)
    if start_date:
        order_items = order_items.filter(order__created_at__date__gte=start_date)
    if end_date:
        order_items = order_items.filter(order__created_at__date__lte=end_date)
    
    # Ürün bazlı satış istatistikleri
    product_stats = order_items.values(
        'product__name',
        'product__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum(F('quantity') * F('unit_price'))
    ).order_by('-total_amount')
    
    # Toplam değerleri hesapla
    totals = order_items.aggregate(
        total_quantity_sum=Sum('quantity'),
        total_amount_sum=Sum(F('quantity') * F('unit_price'))
    )
    
    if export_format == 'pdf':
        # PDF raporu oluştur
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Başlık
        styles = getSampleStyleSheet()
        title = Paragraph("Ürün Satış Raporu", styles['Heading1'])
        elements.append(title)
        
        # Filtre bilgileri
        if start_date and end_date:
            date_range = Paragraph(
                f"Tarih Aralığı: {start_date} - {end_date}",
                styles['Normal']
            )
            elements.append(date_range)
        
        # Tablo verileri
        data = [['Ürün', 'Kategori', 'Satış Adedi', 'Toplam Tutar']]
        for stat in product_stats:
            data.append([
                stat['product__name'],
                stat['product__category__name'],
                str(stat['total_quantity']),
                f"{stat['total_amount']} ₺"
            ])
        
        # Tablo stili
        table = PDFTable(data)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(table)
        
        # PDF oluştur
        doc.build(elements)
        buffer.seek(0)
        
        # PDF'i indir
        response = HttpResponse(buffer, content_type='application/pdf')
        filename = f"urun_raporu_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    elif export_format == 'excel':
        # Excel raporu oluştur
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        worksheet = workbook.add_worksheet()
        
        # Başlık formatı
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#F0F0F0',
            'border': 1
        })
        
        # Başlıklar
        headers = ['Ürün', 'Kategori', 'Satış Adedi', 'Toplam Tutar']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Veriler
        for row, stat in enumerate(product_stats, start=1):
            worksheet.write(row, 0, stat['product__name'])
            worksheet.write(row, 1, stat['product__category__name'])
            worksheet.write(row, 2, stat['total_quantity'])
            worksheet.write(row, 3, f"{stat['total_amount']} ₺")
        
        # Sütun genişliklerini ayarla
        worksheet.set_column(0, 0, 30)  # Ürün adı
        worksheet.set_column(1, 1, 20)  # Kategori
        worksheet.set_column(2, 2, 15)  # Satış adedi
        worksheet.set_column(3, 3, 15)  # Toplam tutar
        
        workbook.close()
        buffer.seek(0)
        
        # Excel'i indir
        response = HttpResponse(buffer, content_type='application/vnd.ms-excel')
        filename = f"urun_raporu_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    # Normal sayfa görüntüleme
    context = {
        'product_stats': product_stats,
        'categories': Category.objects.all(),
        'selected_category': category_id,
        'start_date': start_date,
        'end_date': end_date,
        'totals': totals,
    }
    return render(request, 'pos/product_report.html', context)
