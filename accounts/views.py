from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if (not user.is_superuser
                    and hasattr(user, 'profile')
                    and user.profile.role == 'doctor'):
                if not hasattr(user, 'doctor'):
                    messages.error(request, 'Tài khoản bác sĩ chưa được liên kết.')
                    return render(request, 'accounts/login.html')
                if not user.doctor.is_active:
                    messages.error(request, 'Tài khoản bác sĩ đã ngừng hoạt động.')
                    return render(request, 'accounts/login.html')
            login(request, user)
            messages.success(request, f'Chào mừng {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next') or 'dashboard:index'
            return redirect(next_url)
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng!')

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Bạn đã đăng xuất thành công.')
    return redirect('accounts:login')
