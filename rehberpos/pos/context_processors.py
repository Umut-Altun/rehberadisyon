def add_request_to_user(request):
    """
    Request nesnesini user objesine ekler, böylece template'lerde 
    kullanıcının request nesnesine (ve session'a) erişimi olur
    """
    if hasattr(request, 'user'):
        request.user.request = request
        
    return {}

def menu_permissions(request):
    """
    Kullanıcının erişebileceği menü öğelerini hesaplar ve bir sözlük olarak döndürür.
    Bu, template'lerde rol bazlı izinleri veritabanı sorgusu yapmadan kontrol etmemizi sağlar.
    """
    # Varsayılan olarak tüm izinleri false olarak başlat
    permissions = {
        'can_view_tables': False,
        'can_view_takeaway': False,
        'can_view_orders': False,
        'can_view_kitchen': False,
        'can_view_customers': False,
        'can_view_table_management': False,
        'can_view_users': False,
        'can_view_products': False,
        'can_view_reports': False,
        'can_view_tenant_detail': False,
        'can_view_index': False,
    }
    
    # Kullanıcı giriş yapmamışsa veya istek nesnesi yoksa izinleri döndür
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'menu_permissions': permissions}
    
    # Kullanıcı superadmin ise tüm izinleri true yap
    if request.user.is_superuser:
        for key in permissions:
            permissions[key] = True
        return {'menu_permissions': permissions}
    
    # Kullanıcı rolünü al
    user_role = getattr(request, 'user_role', None) or request.session.get('user_role')
    
    # Rol yoksa izinleri döndür
    if not user_role:
        return {'menu_permissions': permissions}
    
    # Rol bazlı erişim izinlerini ayarla
    if user_role == 'owner' or user_role == 'manager':
        # Sahip ve yöneticiler her şeye erişebilir
        for key in permissions:
            permissions[key] = True
    elif user_role == 'waiter':
        # Garson
        permissions['can_view_tables'] = True
    elif user_role == 'cashier':
        # Kasiyer
        permissions['can_view_tables'] = True
        permissions['can_view_takeaway'] = True
        permissions['can_view_orders'] = True
        permissions['can_view_customers'] = True
    elif user_role == 'kitchen':
        # Mutfak
        permissions['can_view_kitchen'] = True
    
    return {'menu_permissions': permissions} 