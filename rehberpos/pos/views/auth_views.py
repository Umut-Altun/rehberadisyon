from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages

def logout_view(request):
    """
    Kullanıcı çıkışını sağlar ve session'ı temizler.
    """
    # Session'dan tenant ID ve rol bilgisini temizle
    if 'current_tenant_id' in request.session:
        del request.session['current_tenant_id']
    if 'user_role' in request.session:
        del request.session['user_role']
        
    # Çıkış yap
    logout(request)
    messages.success(request, 'Başarıyla çıkış yaptınız.')
    return redirect('pos:login') 