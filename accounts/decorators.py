from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """
    Decorator kiểm tra role của user.
    Cách dùng: @role_required('admin') hoặc @role_required('admin', 'staff')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Vui lòng đăng nhập để tiếp tục.')
                return redirect('accounts:login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if hasattr(request.user, 'profile'):
                role = request.user.profile.role
                if role == 'doctor':
                    if (not hasattr(request.user, 'doctor')
                            or not request.user.doctor.is_active):
                        raise PermissionDenied
                if role in roles:
                    return view_func(request, *args, **kwargs)
            messages.error(request, f'Bạn không có quyền truy cập. (Cần: {", ".join(roles)})')
            return redirect('dashboard:index')
        return wrapper
    return decorator
