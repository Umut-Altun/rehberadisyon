from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.core.paginator import Paginator
from ..models import Customer, Order
from django.http import JsonResponse
import json
from django.urls import reverse


# Müşteri İşlemleri
@login_required
def customer_list(request):
    page = request.GET.get('page', 1)
    customers = Customer.objects.all().order_by('name')
    
    paginator = Paginator(customers, 15)
    try:
        customers = paginator.page(page)
    except:
        customers = paginator.page(1)
    
    return render(request, 'pos/customer_list.html', {'customers': customers})

@login_required
def customer_create(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            
            # Telefon numarası kontrolü
            if Customer.objects.filter(phone=phone).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bu telefon numarası zaten kullanılmaktadır.'
                })
            
            customer = Customer.objects.create(
                name=name,
                phone=phone,
                address=address
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Müşteri başarıyla eklendi.',
                'redirect_url': reverse('pos:customer_list')
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Bir hata oluştu: ' + str(e)
            })
    return redirect('pos:customer_list')

@login_required
def customer_detail(request, customer_id):
    customer = get_object_or_404(Customer.objects.prefetch_related('orders'), id=customer_id)
    # Son 5 siparişi al
    recent_orders = customer.orders.all().order_by('-created_at')[:5]
    return render(request, 'pos/customer_detail.html', {
        'customer': customer,
        'recent_orders': recent_orders
    })

@login_required
def customer_edit(request, customer_id):
    if request.method == 'POST':
        try:
            customer = get_object_or_404(Customer, id=customer_id)
            customer.name = request.POST.get('name')
            customer.phone = request.POST.get('phone')
            customer.address = request.POST.get('address')
            customer.save()
            return redirect('pos:customer_list')
        except:
            return redirect('pos:customer_list')
    return redirect('pos:customer_list')

@login_required
def customer_delete(request, customer_id):
    if request.method == 'POST':
        try:
            customer = get_object_or_404(Customer, id=customer_id)
            customer.delete()
            return redirect('pos:customer_list')
        except:
            return redirect('pos:customer_list')
    return redirect('pos:customer_list')


@login_required
def customer_list_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer = Customer.objects.create(
                name=data['name'],
                phone=data.get('phone', ''),
                address=data.get('address', '')
            )
            return JsonResponse({
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'address': customer.address
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    customers = Customer.objects.all()
    data = []
    for customer in customers:
        customer_data = {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'address': customer.address
        }
        data.append(customer_data)
    return JsonResponse({'customers': data})
