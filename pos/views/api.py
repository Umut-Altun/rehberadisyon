from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.serializers import serialize
from django.forms.models import model_to_dict
from ..models import Table, Order, Product, Customer

@login_required
def table_list_api(request):
    tables = Table.objects.all().order_by('floor', 'number')
    data = [model_to_dict(table) for table in tables]
    return JsonResponse({'tables': data})

@login_required
def order_list_api(request):
    orders = Order.objects.all().select_related('customer', 'table').order_by('-created_at')
    data = []
    for order in orders:
        order_dict = model_to_dict(order)
        order_dict['customer_name'] = order.customer.name if order.customer else None
        order_dict['table_number'] = order.table.number if order.table else None
        data.append(order_dict)
    return JsonResponse({'orders': data})

@login_required
def product_list_api(request):
    products = Product.objects.filter(is_available=True).select_related('category')
    data = []
    for product in products:
        product_dict = model_to_dict(product)
        product_dict['category_name'] = product.category.name
        data.append(product_dict)
    return JsonResponse({'products': data})

@login_required
def customer_list_api(request):
    search = request.GET.get('search', '')
    customers = Customer.objects.all()
    
    if search:
        customers = customers.filter(name__icontains=search)
    
    data = [model_to_dict(customer) for customer in customers]
    return JsonResponse({'customers': data})

