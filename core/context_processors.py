from accounts.models import Notification


def global_context(request):
    """Global context available in all templates."""
    ctx = {
        'site_name': 'TableMaster',
        'site_tagline': 'AI-Powered Restaurant Reservations',
    }
    if request.user.is_authenticated:
        ctx['unread_notifications'] = request.user.notifications.filter(is_read=False).count()
        ctx['recent_notifications'] = request.user.notifications.filter(is_read=False)[:3]
    return ctx
