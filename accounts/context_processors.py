def user_role(request):
    """
    Context processor: inject biến role vào mọi template.
    Dùng trong template: {% if is_admin %}, {% if is_staff %}, {% if is_doctor %}
    """
    ctx = {
        'is_admin': False,
        'is_staff_role': False,
        'is_doctor': False,
        'is_admin_or_staff': False,
    }
    if request.user.is_authenticated:
        if request.user.is_superuser:
            ctx['is_admin'] = True
            ctx['is_admin_or_staff'] = True
        elif hasattr(request.user, 'profile'):
            role = request.user.profile.role
            ctx['is_admin']         = (role == 'admin')
            ctx['is_staff_role']    = (role == 'staff')
            ctx['is_doctor']        = (role == 'doctor')
            ctx['is_admin_or_staff'] = (role in ['admin', 'staff'])
    return ctx
