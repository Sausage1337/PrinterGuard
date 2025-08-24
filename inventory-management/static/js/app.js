// Проверка уведомлений о низких остатках
function checkNotifications() {
    $.ajax({
        url: '/api/notifications/low-stock',
        method: 'GET',
        success: function(notifications) {
            const badge = $('#notification-badge');
            if (notifications.length > 0) {
                badge.text(notifications.length).show();
                
                // Показываем критические уведомления
                const critical = notifications.filter(n => n.severity === 'critical');
                if (critical.length > 0) {
                    badge.removeClass('bg-danger bg-warning').addClass('bg-danger');
                } else {
                    badge.removeClass('bg-danger bg-warning').addClass('bg-warning');
                }
            } else {
                badge.hide();
            }
        }
    });
}

// Проверяем уведомления при загрузке страницы
$(document).ready(function() {
    if ($('#notification-badge').length > 0) {
        checkNotifications();
        // Проверяем каждые 60 секунд
        setInterval(checkNotifications, 60000);
    }
    
    // Инициализация всплывающих подсказок Bootstrap
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
});

// Функция для форматирования даты
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Функция для отображения сообщений
function showAlert(message, type = 'success') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('main').prepend(alertHtml);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(function() {
        $('.alert').fadeOut('slow', function() {
            $(this).remove();
        });
    }, 5000);
}