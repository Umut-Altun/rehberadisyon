from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from ..models import Payment, Order
from django.contrib import messages

@login_required
def payment_create(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        payment_type = request.POST.get('payment_type')
        
        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    order=order,
                    payment_type=payment_type,
                    amount=order.total_amount,  # Direkt sipariş tutarını kullan
                    status='completed'
                )
                
                # Siparişi tamamlandı olarak işaretle
                order.status = 'completed'
                order.save()
                
                # Masayı boşalt
                if order.table:
                    order.table.is_occupied = False
                    order.table.save()
                    return redirect('pos:table_list')  # Masalar sayfasına yönlendir
                
                return redirect('pos:order_list')  # Paket siparişler için sipariş listesine yönlendir
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    context = {
        'order': order,
        'payment_types': Payment.PAYMENT_TYPE_CHOICES
    }
    return render(request, 'pos/payment_create.html', context)

@login_required
def payment_detail(request, payment_id):
    payment = get_object_or_404(Payment.objects.select_related('order'), id=payment_id)
    return render(request, 'pos/payment_detail.html', {'payment': payment})

@login_required
def payment_refund(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment.status = 'refunded'
                payment.save()
                
                # Siparişi iptal edildi olarak işaretle
                payment.order.status = 'cancelled'
                payment.order.save()
                
                return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return render(request, 'pos/payment_refund.html', {'payment': payment})

@login_required
def payment_pdf(request, payment_id):
    payment = get_object_or_404(Payment.objects.select_related('order'), id=payment_id)
    
    # PDF oluştur
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Stil tanımlamaları
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    
    # Başlık
    elements.append(Paragraph(f"Ödeme Makbuzu #{payment.id}", title_style))
    
    # Ödeme bilgileri
    data = [
        ["Ödeme No:", str(payment.id)],
        ["Tarih:", payment.created_at.strftime("%d/%m/%Y %H:%M")],
        ["Sipariş No:", str(payment.order.id)],
        ["Ödeme Türü:", dict(Payment.PAYMENT_TYPE_CHOICES)[payment.payment_type]],
        ["Tutar:", f"₺{payment.amount}"],
        ["Durum:", dict(Payment.STATUS_CHOICES)[payment.status]]
    ]
    
    # Tablo stili
    table = Table(data)
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
    ]))
    
    elements.append(table)
    
    # PDF oluştur
    doc.build(elements)
    
    # PDF'i response olarak gönder
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payment_{payment.id}.pdf"'
    
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
