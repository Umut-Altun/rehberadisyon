from django import forms
from .models import Product, Category, Customer, Order, OrderItem, Payment, Tenant, TenantUser
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm

class ProductForm(forms.ModelForm):
    """Ürün formu"""
    def __init__(self, *args, **kwargs):
        # Tenant'ı kwargs'ten al ve kaldır
        tenant = kwargs.pop('tenant', None)
        super(ProductForm, self).__init__(*args, **kwargs)
        
        # Tenant filtreleme
        if tenant:
            self.fields['category'].queryset = Category.objects.filter(tenant=tenant)
    
    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'description', 'image', 'is_available']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Ürün adı',
                'class': 'form-control'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'price': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Ürün açıklaması',
                'rows': 3,
                'class': 'form-control'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': 'Ürün Adı',
            'category': 'Kategori',
            'price': 'Fiyat',
            'description': 'Açıklama',
            'image': 'Ürün Görseli',
            'is_available': 'Ürün Aktif'
        }
        help_texts = {
            'name': 'Ürünün adını girin.',
            'category': 'Ürünün kategorisini seçin.',
            'price': 'Ürünün fiyatını girin.',
            'description': 'Ürün hakkında açıklama girin.',
            'image': 'Ürün için bir görsel seçin.',
            'is_available': 'Ürünün satışa açık olup olmadığını belirtin.'
        }
        error_messages = {
            'name': {
                'required': 'Ürün adı zorunludur.',
                'max_length': 'Ürün adı en fazla %(limit_value)d karakter olabilir.'
            },
            'category': {
                'required': 'Kategori seçimi zorunludur.'
            },
            'price': {
                'required': 'Fiyat alanı zorunludur.',
                'invalid': 'Geçerli bir fiyat girin.',
                'min_value': 'Fiyat 0\'dan büyük olmalıdır.'
            }
        }

    def clean_price(self):
        """Fiyat alanı için özel doğrulama"""
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('Fiyat 0\'dan büyük olmalıdır.')
        return price

    def clean_image(self):
        """Görsel alanı için özel doğrulama"""
        image = self.cleaned_data.get('image')
        if image:
            # Dosya boyutu kontrolü (5MB)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Görsel boyutu 5MB\'dan büyük olamaz.')
            
            # Dosya uzantısı kontrolü
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            ext = str(image.name).lower()[-4:]
            if not any(ext.endswith(x) for x in allowed_extensions):
                raise forms.ValidationError('Sadece JPG, JPEG, PNG ve GIF dosyaları yüklenebilir.')
        return image

class CategoryForm(forms.ModelForm):
    """Kategori formu"""
    def __init__(self, *args, **kwargs):
        # Tenant'ı kwargs'ten al ve kaldır
        self.tenant = kwargs.pop('tenant', None)
        super(CategoryForm, self).__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super(CategoryForm, self).save(commit=False)
        if self.tenant and not instance.tenant_id:
            instance.tenant = self.tenant
        if commit:
            instance.save()
        return instance
        
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Kategori adı',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Kategori açıklaması',
                'rows': 3,
                'class': 'form-control'
            })
        }
        labels = {
            'name': 'Kategori Adı',
            'description': 'Açıklama'
        }
        error_messages = {
            'name': {
                'required': 'Kategori adı zorunludur.',
                'max_length': 'Kategori adı en fazla %(limit_value)d karakter olabilir.',
                'unique': 'Bu isimde bir kategori zaten mevcut.'
            }
        }

class UserEditForm(forms.ModelForm):
    """Kullanıcı düzenleme formu"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kullanıcı adı'}),
        label='Kullanıcı Adı',
        help_text='Giriş yaparken kullanılacak kullanıcı adı.'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text='Şifreyi değiştirmek için doldurun, boş bırakırsanız mevcut şifre korunacaktır.'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        label='Şifre (Tekrar)'
    )
    
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label='Roller'
    )
    
    # TenantUser için rol seçimi
    tenant_role = forms.ChoiceField(
        choices=TenantUser.USER_ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='İşletme Rolü',
        required=True,
        initial='waiter'
    )
    
    def __init__(self, *args, **kwargs):
        # Tenant parametresini al ve kaldır
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        # Eğer yeni kullanıcı oluşturuluyorsa (instance None ise)
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['password_confirm'].required = True
            self.fields['password'].help_text = 'Kullanıcı için bir şifre belirleyin.'
        else:
            # Mevcut kullanıcı için kullanıcı adını salt okunur yap
            self.fields['username'].widget.attrs['readonly'] = True
            
        # Eğer tenant belirtilmişse ve kullanıcı zaten bu tenant'a bağlıysa, mevcut rolü seç
        if self.tenant and self.instance.pk:
            try:
                tenant_user = TenantUser.objects.get(tenant=self.tenant, user=self.instance)
                self.fields['tenant_role'].initial = tenant_user.role
            except TenantUser.DoesNotExist:
                pass
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'groups', 'is_superuser']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kullanıcı adı'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ad'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Soyad'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'E-posta'
            }),
            'is_superuser': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'first_name': 'Ad',
            'last_name': 'Soyad',
            'email': 'E-posta',
            'is_superuser': 'Yönetici Yetkisi'
        }
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        user_id = self.instance.id if self.instance else None
        
        if self.instance and self.instance.pk:
            # Düzenleme modunda kullanıcı adı değişmemeli
            return self.instance.username
        
        # Yeni kullanıcı için kullanıcı adının benzersiz olup olmadığını kontrol et
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            raise forms.ValidationError('Bu kullanıcı adı zaten kullanılıyor.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password:
            if not password_confirm:
                raise forms.ValidationError('Lütfen şifrenizi tekrar girin.')
            if password != password_confirm:
                raise forms.ValidationError('Şifreler eşleşmiyor.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        
        if password:
            user.set_password(password)
        
        # Düzenleme modunda grupları değiştirme
        if self.instance and self.instance.pk:
            # Grupları korumak için self.save_m2m'i kullanarak yeni grupları ayarlamayı engelle
            original_save_m2m = self.save_m2m
            def custom_save_m2m():
                pass  # Grupları değiştirme
            self.save_m2m = custom_save_m2m
        
        if commit:
            user.save()
            if not self.instance.pk:
                # Yalnızca yeni kullanıcı oluşturulurken grupları kaydet
                self.save_m2m()
            
            # Burada tenant ilişkisini kurma kısmını view'a bırakıyoruz
            # Bu kısım view'da özel olarak ele alınıyor
        
        return user

class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ['name', 'address', 'phone', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'İşletme Adı'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Adres', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefon Numarası'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ad'})
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Soyad'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kullanıcı Adı'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Şifre'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Şifre (Tekrar)'})
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Bu email adresi zaten kullanılıyor.')
        return email 

class TenantLoginForm(forms.Form):
    """İşletme kodu ve kullanıcı bilgileriyle giriş yapmak için form"""
    tenant_code = forms.CharField(
        label='İşletme Kodu',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'İşletme Kodu'}),
        required=True,
    )
    username = forms.CharField(
        label='Kullanıcı Adı',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kullanıcı Adı'}),
        required=True,
    )
    password = forms.CharField(
        label='Şifre',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Şifre'}),
        required=True,
    )
    
    def clean(self):
        cleaned_data = super().clean()
        tenant_code = cleaned_data.get('tenant_code')
        username = cleaned_data.get('username')
        
        # İşletme kodunu kontrol et
        try:
            tenant = Tenant.objects.get(name=tenant_code)
            cleaned_data['tenant'] = tenant
        except Tenant.DoesNotExist:
            raise forms.ValidationError('Geçersiz işletme kodu.')
        
        # Kullanıcının bu işletmeye bağlı olup olmadığını kontrol et
        try:
            user = User.objects.get(username=username)
            tenant_user = TenantUser.objects.get(user=user, tenant=tenant, is_active=True)
            cleaned_data['tenant_user'] = tenant_user
        except (User.DoesNotExist, TenantUser.DoesNotExist):
            raise forms.ValidationError('Bu kullanıcı bu işletmede kayıtlı değil veya hesabı aktif değil.')
        
        return cleaned_data 