from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Avg
from django.db.models.functions import ExtractHour, TruncDate, TruncMonth, ExtractMonth, ExtractYear
from django.utils import timezone
from django.http import HttpResponse
from reportlab.lib import colors
from django.contrib import messages
from django.shortcuts import redirect
from reportlab.lib.pagesizes import letter


from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import json
import csv
from reportlab.platypus import SimpleDocTemplate, Table as PDFTable, TableStyle, Paragraph
import xlsxwriter
from io import BytesIO
from ..models import Order, Product, Table, Payment, OrderItem
from django.db.models import Sum, Count, F, Avg, Case, When, Value, CharField



@login_required
def reports(request):
    # Bilgisayarın güncel tarihini al
    current_date = timezone.localtime(timezone.now()).date()
    first_day_of_month = current_date.replace(day=1)
    first_day_of_year = current_date.replace(month=1, day=1)
    
    # Günlük satışlar
    today_orders = Order.objects.filter(
        created_at__date=current_date,
        status='completed'
    )
    today_sales = today_orders.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Aylık satışlar
    monthly_orders = Order.objects.filter(
        created_at__date__range=[first_day_of_month, current_date],
        status='completed'
    )
    monthly_sales = monthly_orders.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Yıllık satışlar
    yearly_orders = Order.objects.filter(
        created_at__date__range=[first_day_of_year, current_date],
        status='completed'
    )
    yearly_sales = yearly_orders.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Toplam satışlar
    total_orders = Order.objects.filter(status='completed')
    total_sales = total_orders.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Bugünkü ödeme istatistikleri
    payment_stats = Payment.objects.filter(
        created_at__date=current_date,
        status='completed'
    ).values(
        'payment_type'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).annotate(
        payment_type_display=Case(
            When(payment_type='cash', then=Value('Nakit')),
            When(payment_type='credit_card', then=Value('Kredi Kartı')),
            When(payment_type='debit_card', then=Value('Banka Kartı')),
            default=Value('Diğer'),
            output_field=CharField(),
        )
    )
    
    # Bugünkü personel satışları
    staff_sales = Order.objects.filter(
        created_at__date=current_date,
        status='completed'
    ).values(
        'staff__username',
        'staff__first_name'
    ).annotate(
        order_count=Count('id'),
        total_sales=Sum('total_amount')
    ).order_by('-total_sales')
    
    # Bugünkü ürün satışları
    product_stats = OrderItem.objects.filter(
        order__created_at__date=current_date,
        order__status='completed'
    ).values(
        'product__name',
        'product__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum(F('quantity') * F('unit_price'))
    ).order_by('-total_quantity')
    
    context = {
        'today_sales': today_sales['total'] or 0,
        'today_order_count': today_sales['count'] or 0,
        'monthly_sales': monthly_sales['total'] or 0,
        'monthly_order_count': monthly_sales['count'] or 0,
        'yearly_sales': yearly_sales['total'] or 0,
        'yearly_order_count': yearly_sales['count'] or 0,
        'total_sales': total_sales['total'] or 0,
        'total_order_count': total_sales['count'] or 0,
        'today_payment_stats': payment_stats,
        'staff_sales': staff_sales,
        'today_product_stats': product_stats,
        'cleanup_success': request.session.pop('cleanup_success', False),
        'cleanup_message': request.session.pop('cleanup_message', None),
    }
    return render(request, 'pos/reports.html', context)


@login_required
def daily_report(request):
    today = timezone.now().date()
    
    # Saatlik satış analizi
    hourly_sales = Order.objects.filter(
        created_at__date=today,
        status='completed'
    ).annotate(
        hour=ExtractHour('created_at')
    ).values('hour').annotate(
        total_sales=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('hour')
    
    # En çok satan ürünler
    top_products = Order.objects.filter(
        created_at__date=today,
        status='completed'
    ).values(
        'items__product__name'
    ).annotate(
        total_quantity=Sum('items__quantity'),
        total_sales=Sum(F('items__quantity') * F('items__unit_price'))
    ).order_by('-total_quantity')[:10]
    
    context = {
        'date': today,
        'hourly_sales': hourly_sales,
        'top_products': top_products
    }
    return render(request, 'pos/daily_report.html', context)

@login_required
def monthly_report(request):
    # Bilgisayarın güncel tarihini al
    current_date = timezone.localtime(timezone.now()).date()
    first_day = current_date.replace(day=1)  # Ayın ilk günü
    
    # Türkçe ay isimleri
    turkish_months = {
        1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan',
        5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos',
        9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
    }
    
    # Aylık siparişleri al
    orders = Order.objects.filter(
        created_at__date__range=[first_day, current_date],
        status='completed'
    ).select_related('table', 'customer')

    # Toplam satış ve sipariş sayısı
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    order_count = orders.count()
    
    # Günlük satışlar
    daily_sales = orders.annotate(
        day=TruncDate('created_at')
    ).values('day').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('day')

    # Kategori bazlı satışlar
    category_sales = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'product__category__name'
    ).annotate(
        total=Sum(F('quantity') * F('unit_price')),
        count=Sum('quantity')
    ).order_by('-total')

    # Türkçe ay ve yıl formatı
    current_month = turkish_months[current_date.month]
    formatted_date = f"{current_month} {current_date.year}"
    
    context = {
        'orders': orders,
        'total_sales': total_sales,
        'order_count': order_count,
        'daily_sales': daily_sales,
        'category_sales': category_sales,
        'current_date': current_date,
        'first_day': first_day,
        'month': formatted_date
    }
    return render(request, 'pos/monthly_report.html', context)

@login_required
def yearly_report(request):
    # Bilgisayarın güncel tarihini al
    current_date = timezone.localtime(timezone.now()).date()
    first_day = current_date.replace(month=1, day=1)  # Yılın ilk günü
    
    # Türkçe ay isimleri
    turkish_months = {
        1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan',
        5: 'Mayıs', 6: 'Haziran', 7: 'Temmuz', 8: 'Ağustos',
        9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
    }
    
    # Yıllık siparişleri al
    orders = Order.objects.filter(
        created_at__date__range=[first_day, current_date],
        status='completed'
    ).select_related('table', 'customer')
    
    # Toplam satış ve sipariş sayısı
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    order_count = orders.count()
    
    # Aylık satışlar
    monthly_sales = orders.annotate(
        month=ExtractMonth('created_at')
    ).values('month').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('month')

    # Ay isimlerini Türkçe'ye çevir ve listeye dönüştür
    monthly_sales_list = []
    for sale in monthly_sales:
        sale['month_name'] = turkish_months[sale['month']]
        monthly_sales_list.append(sale)
    
    # Kategori bazlı satışlar
    category_sales = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'product__category__name'
    ).annotate(
        total=Sum(F('quantity') * F('unit_price')),
        count=Sum('quantity')
    ).order_by('-total')

    
    context = {
        'orders': orders,
        'total_sales': total_sales,
        'order_count': order_count,
        'monthly_sales': monthly_sales_list,  # Türkçe ay isimleri eklenmiş liste
        'category_sales': category_sales,
        'current_date': current_date,
        'first_day': first_day,
        'year': current_date.year
    }
    return render(request, 'pos/yearly_report.html', context)

@login_required
def export_excel(request):
    # Excel dosyası oluştur
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Başlık stilleri
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'bg_color': '#F7F7F7'
    })
    
    # Başlıklar
    headers = ['Tarih', 'Sipariş No', 'Masa', 'Müşteri', 'Toplam', 'Durum']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # Verileri yaz
    orders = Order.objects.all().select_related('customer', 'table')
    for row, order in enumerate(orders, start=1):
        worksheet.write(row, 0, order.created_at.strftime('%d/%m/%Y %H:%M'))
        worksheet.write(row, 1, order.id)
        worksheet.write(row, 2, f"Masa {order.table.number}" if order.table else "Paket")
        worksheet.write(row, 3, order.customer.name if order.customer else "-")
        worksheet.write(row, 4, float(order.total_amount))
        worksheet.write(row, 5, dict(Order.STATUS_CHOICES)[order.status])
    
    workbook.close()
    
    # Excel dosyasını response olarak gönder
    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=orders.xlsx'
    
    return response

@login_required
def staff_sales_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Personel bazlı satış analizi
    staff_sales = Order.objects.filter(
        status='completed'
    )
    
    if start_date:
        staff_sales = staff_sales.filter(created_at__date__gte=start_date)
    if end_date:
        staff_sales = staff_sales.filter(created_at__date__lte=end_date)
    
    staff_sales = staff_sales.values(
        'staff__username'
    ).annotate(
        total_sales=Sum('total_amount'),
        order_count=Count('id'),
        average_order=Avg('total_amount')
    ).order_by('-total_sales')
    
    context = {
        'staff_sales': staff_sales,
        'start_date': start_date,
        'end_date': end_date
    }
    return render(request, 'pos/staff_sales_report.html', context) 

@login_required
def daily_report(request):
    # Bilgisayarın güncel tarihini al
    current_date = timezone.localtime(timezone.now()).date()
    
    # Günlük siparişleri al
    orders = Order.objects.filter(
        created_at__date=current_date,
        status='completed'
    ).select_related('table', 'customer')

    # Toplam satış ve ortalama hesapla
    total_sales = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    order_count = orders.count()
    avg_order_amount = total_sales / order_count if order_count > 0 else 0

    # Saat bazlı satışlar
    hourly_sales = orders.annotate(
        hour=ExtractHour('created_at')
    ).values('hour').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('hour')

    # Ödeme tiplerine göre satışlar
    payment_stats = Payment.objects.filter(
        created_at__date=current_date,
        status='completed'
    ).values(
        'payment_type'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).annotate(
        payment_type_display=Case(
            When(payment_type='cash', then=Value('Nakit')),
            When(payment_type='credit_card', then=Value('Kredi Kartı')),
            When(payment_type='debit_card', then=Value('Banka Kartı')),
            default=Value('Diğer'),
            output_field=CharField(),
        )
    )

    # Kategori bazlı satışlar
    category_sales = OrderItem.objects.filter(
        order__in=orders
    ).values(
        'product__category__name'
    ).annotate(
        total=Sum(F('quantity') * F('unit_price')),
        count=Sum('quantity')
    ).order_by('-total')

    context = {
        'orders': orders,
        'total_sales': total_sales,
        'hourly_sales': hourly_sales,
        'payment_stats': payment_stats,
        'category_sales': category_sales,
        'date': current_date,
        'order_count': order_count,
        'avg_order_amount': avg_order_amount
    }
    return render(request, 'pos/daily_report.html', context)

@login_required
def table_report(request):
    """Masa bazlı rapor"""
    # Filtreleri al
    table_id = request.GET.get('table')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export_format = request.GET.get('export')
    
    # Temel sorgu
    orders = Order.objects.filter(
        status='completed',
        table__isnull=False
    ).select_related('table')
    
    # Filtreleri uygula
    if table_id:
        orders = orders.filter(table_id=table_id)
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    
    # Masa bazlı satış istatistikleri
    table_stats = orders.values(
        'table__number'
    ).annotate(
        total_orders=Count('id'),
        total_amount=Sum('total_amount')
    ).annotate(
        avg_amount=F('total_amount') / F('total_orders')
    ).order_by('-total_amount')
    
    if export_format == 'pdf':
        # PDF raporu oluştur
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Başlık
        styles = getSampleStyleSheet()
        title = Paragraph("Masa Satış Raporu", styles['Heading1'])
        elements.append(title)
        
        # Filtre bilgileri
        if start_date and end_date:
            date_range = Paragraph(
                f"Tarih Aralığı: {start_date} - {end_date}",
                styles['Normal']
            )
            elements.append(date_range)
        
        # Tablo verileri
        data = [['Masa No', 'Sipariş Sayısı', 'Toplam Tutar', 'Ortalama Sipariş']]
        for stat in table_stats:
            data.append([
                f"Masa {stat['table__number']}",
                str(stat['total_orders']),
                f"{stat['total_amount']} ₺",
                f"{stat['avg_amount']:.2f} ₺"
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
        filename = f"masa_raporu_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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
        headers = ['Masa No', 'Sipariş Sayısı', 'Toplam Tutar', 'Ortalama Sipariş']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Veriler
        for row, stat in enumerate(table_stats, start=1):
            worksheet.write(row, 0, f"Masa {stat['table__number']}")
            worksheet.write(row, 1, stat['total_orders'])
            worksheet.write(row, 2, f"{stat['total_amount']} ₺")
            worksheet.write(row, 3, f"{stat['avg_amount']:.2f} ₺")
        
        # Sütun genişliklerini ayarla
        worksheet.set_column(0, 0, 15)  # Masa no
        worksheet.set_column(1, 1, 15)  # Sipariş sayısı
        worksheet.set_column(2, 2, 15)  # Toplam tutar
        worksheet.set_column(3, 3, 15)  # Ortalama sipariş
        
        workbook.close()
        buffer.seek(0)
        
        # Excel'i indir
        response = HttpResponse(buffer, content_type='application/vnd.ms-excel')
        filename = f"masa_raporu_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    # Normal sayfa görüntüleme
    context = {
        'table_stats': table_stats,
        'tables': Table.objects.all(),
        'selected_table': table_id,
        'start_date': start_date,
        'end_date': end_date
    }
    return render(request, 'pos/table_report.html', context)

@login_required
def export_pdf(request):
    # PDF oluşturma
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Başlık stili
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    
    # Başlık
    title = Paragraph("Sipariş Raporu", title_style)
    elements.append(title)
    
    # Sipariş verileri
    data = [['Sipariş No', 'Tarih', 'Müşteri', 'Masa', 'Tutar', 'Durum']]
    orders = Order.objects.all().order_by('-created_at')
    
    for order in orders:
        data.append([
            f"#{order.id}",
            order.created_at.strftime("%d.%m.%Y %H:%M"),
            order.customer.name if order.customer else '-',
            f"Masa {order.table.number}" if order.table else 'Paket',
            f"{order.total_amount} ₺",
            order.get_status_display()
        ])
    
    # Tablo stili
    table = PDFTable(data)
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ]))
    elements.append(table)
    
    # PDF oluştur
    doc.build(elements)
    
    # PDF'i response olarak gönder
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="siparis_raporu_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response

@login_required
def database_cleanup(request):
    """Veritabanı temizleme işlemi"""
    if request.method == 'POST':
        try:
            # Sadece superuser'lar bu işlemi yapabilir
            if not request.user.is_superuser:
                messages.error(request, 'Bu işlemi yapmaya yetkiniz yok!')
                return redirect('pos:reports')
            
            # Onay metni kontrolü
            confirm_text = request.POST.get('confirm_text', '').lower()
            if confirm_text != 'onaylıyorum':
                messages.error(request, 'Silme işlemi için "onaylıyorum" yazmanız gerekmektedir!')
                return redirect('pos:reports')
            
            from django.db import transaction
            
            with transaction.atomic():  # Tüm silme işlemlerini tek bir transaction içinde yap
                # Önce ödemeleri sil
                payment_count = Payment.objects.all().count()
                Payment.objects.all().delete()
                
                # Sonra siparişleri ve ilgili detayları sil
                order_count = Order.objects.all().count()
                Order.objects.all().delete()  # Bu işlem OrderItem'ları da CASCADE ile silecek
                
                # Masaları boş duruma getir
                table_count = Table.objects.filter(is_occupied=True).count()
                Table.objects.all().update(is_occupied=False)
                
                # Başarı mesajını session'a kaydet
                request.session['cleanup_success'] = True
                request.session['cleanup_message'] = (
                    f'{order_count} sipariş, {payment_count} ödeme silindi ve '
                    f'{table_count} masa boşaltıldı.'
                )
            
        except Exception as e:
            messages.error(request, f'Veritabanı temizlenirken bir hata oluştu: {str(e)}')
        
        return redirect('pos:reports')
    
    return redirect('pos:reports')
