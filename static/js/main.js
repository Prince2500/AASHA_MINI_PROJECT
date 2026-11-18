// AASHA Healthcare Portal - Core Client-Side Utilities

document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss standard alerts after 6 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 6000);
  });

  // Notification Polling (for logged-in users)
  const notifBadge = document.getElementById('navbarNotifBadge');
  const notifList = document.getElementById('navbarNotifList');

  if (notifBadge && notifList) {
    function refreshNotifications() {
      fetch('/api/notifications')
        .then(res => res.json())
        .then(data => {
          if (data && typeof data.unread_count !== 'undefined') {
            if (data.unread_count > 0) {
              notifBadge.textContent = data.unread_count;
              notifBadge.classList.remove('d-none');
            } else {
              notifBadge.classList.add('d-none');
            }

            // Populate notification dropdown items
            if (data.notifications && data.notifications.length > 0) {
              notifList.innerHTML = data.notifications.map(n => `
                <li class="px-3 py-2 border-bottom ${n.is_read ? 'bg-light' : 'bg-white'}">
                  <div class="d-flex justify-content-between align-items-start">
                    <span class="fw-bold small text-${n.notification_type === 'urgent_alert' ? 'danger' : 'success'}">${escapeHtml(n.title)}</span>
                    <small class="text-muted ms-2">${n.created_at}</small>
                  </div>
                  <p class="small mb-1 text-muted">${escapeHtml(n.message)}</p>
                  ${n.report_id ? `<a href="/reports/${n.report_id}" class="badge bg-success text-white text-decoration-none">View Case</a>` : ''}
                </li>
              `).join('');
            } else {
              notifList.innerHTML = '<li class="p-3 text-center text-muted small">No notifications yet</li>';
            }
          }
        })
        .catch(err => console.debug('Notif refresh paused'));
    }

    // Refresh every 20s
    setInterval(refreshNotifications, 20000);

    // Mark all read button
    const markAllBtn = document.getElementById('markAllNotifsReadBtn');
    if (markAllBtn) {
      markAllBtn.addEventListener('click', function (e) {
        e.preventDefault();
        fetch('/api/notifications/mark-all-read', { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            notifBadge.classList.add('d-none');
            refreshNotifications();
          });
      });
    }
  }
});

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, function (m) {
    return {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[m];
  });
}
