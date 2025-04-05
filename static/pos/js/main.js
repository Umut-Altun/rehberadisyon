// Document Ready
$(document).ready(function() {
    // Sayfanın tamamen yüklenmesini bekle
    $(window).on('load', function() {
        // Sayfa yüklendikten sonra transition'ları aktif et
        setTimeout(function() {
            document.documentElement.classList.remove('loading');
            
            // CSS geçişlerini yeniden etkinleştir
            setTimeout(function() {
                const styleEl = document.createElement('style');
                styleEl.innerHTML = `
                    .sidebar { transition: width .4s, background-color .4s !important; }
                    .header { transition: padding .4s !important; }
                    #main.container-fluid { transition: padding .4s, margin-top .4s !important; }
                `;
                document.head.appendChild(styleEl);
            }, 300);
        }, 100);
    });

    // Bootstrap Tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Alert Auto Close
    $('.alert').alert();
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);

    // Table Status Update
    $('.table-status-update').change(function() {
        var tableId = $(this).data('table-id');
        var isOccupied = $(this).is(':checked');
        
        $.ajax({
            url: '/api/table/' + tableId + '/status/',
            method: 'POST',
            data: {
                is_occupied: isOccupied,
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    location.reload();
                }
            }
        });
    });

    // Order Item Quantity Update
    $('.order-item-quantity').change(function() {
        var itemId = $(this).data('item-id');
        var quantity = $(this).val();
        
        $.ajax({
            url: '/api/order-item/' + itemId + '/quantity/',
            method: 'POST',
            data: {
                quantity: quantity,
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    updateOrderTotal();
                }
            }
        });
    });

    // Product Search
    $('#product-search').on('input', function() {
        var query = $(this).val().toLowerCase();
        $('.product-card').each(function() {
            var productName = $(this).data('product-name').toLowerCase();
            var productCategory = $(this).data('product-category').toLowerCase();
            
            if (productName.includes(query) || productCategory.includes(query)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    // Category Filter
    $('.category-filter').click(function() {
        var category = $(this).data('category');
        
        if (category === 'all') {
            $('.product-card').show();
        } else {
            $('.product-card').each(function() {
                if ($(this).data('product-category') === category) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });
        }
        
        $('.category-filter').removeClass('active');
        $(this).addClass('active');
    });

    // Kitchen Order Status Update
    $('.kitchen-order-status').change(function() {
        var orderId = $(this).data('order-id');
        var status = $(this).val();
        
        $.ajax({
            url: '/api/order/' + orderId + '/status/',
            method: 'POST',
            data: {
                status: status,
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    location.reload();
                }
            }
        });
    });

    // Auto Refresh Kitchen Display
    if ($('#kitchen-display').length) {
        setInterval(function() {
            location.reload();
        }, 60000); // Her 1 dakikada bir yenile
    }

    // Payment Form Validation
    $('#payment-form').submit(function(e) {
        var amount = parseFloat($('#payment-amount').val());
        var total = parseFloat($('#order-total').val());
        
        if (amount < total) {
            e.preventDefault();
            alert('Ödeme tutarı toplam tutardan az olamaz!');
        }
    });

    // Print Order
    $('.print-order').click(function() {
        var orderId = $(this).data('order-id');
        window.open('/order/' + orderId + '/print/', '_blank');
    });

    // SIDEBAR: Toggle sidebar visibility
    const showSidebar = (toggleId, sidebarId, headerId, mainId) =>{
        const toggle = document.getElementById(toggleId),
              sidebar = document.getElementById(sidebarId),
              header = document.getElementById(headerId),
              main = document.getElementById(mainId)
              
        // Büyük ekranlarda sidebar kontrolü
        function handleSidebarToggle() {
            /* Toggle body class for styling */
            document.body.classList.toggle('sidebar-collapsed');
            
            // Sidebar durumunu cookie'de sakla
            if(document.body.classList.contains('sidebar-collapsed')) {
                document.cookie = "sidebar_state=collapsed; path=/; max-age=31536000";
            } else {
                document.cookie = "sidebar_state=expanded; path=/; max-age=31536000";
            }
        }
        
        // Küçük ekranlarda sidebar göster/gizle
        function handleMobileSidebar() {
            sidebar.classList.toggle('show-sidebar');
        }

        if(toggle && sidebar && header && main){
            toggle.addEventListener('click', () => {
                const isMobile = window.innerWidth < 1150;
                
                if (isMobile) {
                    handleMobileSidebar();
                } else {
                    handleSidebarToggle();
                }
            });
            
            // Sayfa yüklendiğinde sidebar durumu kontrolü
            const getCookie = (name) => {
                const value = `; ${document.cookie}`;
                const parts = value.split(`; ${name}=`);
                if (parts.length === 2) return parts.pop().split(';').shift();
                return null;
            };
            
            // Sayfanın ilk yüklenişinde sidebar durumunu ayarla
            const sidebarState = getCookie('sidebar_state');
            
            if (sidebarState === 'collapsed') {
                document.body.classList.add('sidebar-collapsed');
            } else {
                document.body.classList.remove('sidebar-collapsed');
            }
        }
    }
    showSidebar('header-toggle','sidebar', 'header', 'main');

    // SIDEBAR: Link active control
    const sidebarLink = document.querySelectorAll('.sidebar__list a');

    function linkColor(){
        sidebarLink.forEach(l => l.classList.remove('active-link'))
        this.classList.add('active-link')
    }

    sidebarLink.forEach(l => {
        if (!l.classList.contains('active-link')) {
            l.addEventListener('click', linkColor)
        }
    });

    // THEME: Dark/Light theme toggle
    const themeButton = document.getElementById('theme-button');
    const darkTheme = 'dark-theme';
    const iconTheme = 'ri-sun-fill';

    // Previously selected topic (if user selected)
    const selectedTheme = localStorage.getItem('selected-theme');
    const selectedIcon = localStorage.getItem('selected-icon');

    // We obtain the current theme that the interface has by validating the dark-theme class
    const getCurrentTheme = () => document.body.classList.contains(darkTheme) ? 'dark' : 'light';
    const getCurrentIcon = () => themeButton.querySelector('i').classList.contains(iconTheme) ? 'ri-moon-clear-fill' : 'ri-sun-fill';

    // We validate if the user previously chose a topic
    if (selectedTheme) {
        // If the validation is fulfilled, we ask what the issue was to know if we activated or deactivated the dark
        document.body.classList[selectedTheme === 'dark' ? 'add' : 'remove'](darkTheme);
        themeButton.querySelector('i').classList[selectedIcon === 'ri-moon-clear-fill' ? 'add' : 'remove'](iconTheme);
    }

    // Activate / deactivate the theme manually with the button
    if (themeButton) {
        themeButton.addEventListener('click', (e) => {
            e.preventDefault(); // Link'in yönlendirmesini engelle
            
            // Add or remove the dark / icon theme
            document.body.classList.toggle(darkTheme);
            themeButton.querySelector('i').classList.toggle(iconTheme);
            
            // We save the theme and the current icon that the user chose
            localStorage.setItem('selected-theme', getCurrentTheme());
            localStorage.setItem('selected-icon', getCurrentIcon());
        });
    }

    // Preload class'ını kaldır
    document.body.classList.remove('preload');
});

// Helper Functions
function updateOrderTotal() {
    var total = 0;
    $('.order-item-row').each(function() {
        var price = parseFloat($(this).data('price'));
        var quantity = parseInt($(this).find('.order-item-quantity').val());
        total += price * quantity;
    });
    
    $('#order-total').text(total.toFixed(2) + ' ₺');
}

function formatPrice(price) {
    return parseFloat(price).toFixed(2) + ' ₺';
}

function formatDate(dateString) {
    var options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString('tr-TR', options);
} 