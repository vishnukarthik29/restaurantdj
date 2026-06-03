from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db import transaction

from .models import User, CustomerProfile, Notification
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, CustomerProfileForm, ChangePasswordForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('customer_dashboard')
    form = UserRegistrationForm()
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                # Auto-generate username from email prefix + count
                base = form.cleaned_data['email'].split('@')[0]
                username = base
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base}{counter}"
                    counter += 1
                user.username = username
                user.role = User.ROLE_CUSTOMER
                user.save()
                CustomerProfile.objects.create(
                    user=user,
                    whatsapp_number=form.cleaned_data.get('whatsapp_number', ''),
                )
                Notification.objects.create(
                    user=user,
                    notification_type=Notification.TYPE_SYSTEM,
                    title='Welcome to TableMaster! 🎉',
                    message='Your account is ready. Start exploring restaurants and make your first reservation.',
                    link='/restaurants/',
                )
                login(request, user)
                messages.success(request, f'Welcome, {user.first_name}! Your account has been created.')
                return redirect('customer_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('customer_dashboard')
    form = UserLoginForm()
    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
                    User.objects.filter(pk=user.pk).update(last_login_ip=ip)
                    messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                    if next_url:
                        return redirect(next_url)
                    if user.is_admin_user:
                        return redirect('admin_dashboard')
                    return redirect('customer_dashboard')
                else:
                    messages.error(request, 'Your account has been deactivated.')
            else:
                messages.error(request, 'Invalid email or password.')
    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out. See you soon!')
    return redirect('home')


@login_required
def profile_view(request):
    user = request.user
    try:
        profile = user.customerprofile
    except CustomerProfile.DoesNotExist:
        profile = CustomerProfile.objects.create(user=user)

    user_form = UserProfileForm(instance=user)
    profile_form = CustomerProfileForm(instance=profile)

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=user)
        profile_form = CustomerProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password updated successfully!')
        else:
            for field_errors in form.errors.values():
                for err in field_errors:
                    messages.error(request, err)
    return redirect('profile')


@login_required
def notifications_view(request):
    notif_qs = request.user.notifications.all()
    paginator = Paginator(notif_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'accounts/notifications.html', {
        'notifications': page_obj,
        'unread_count': request.user.notifications.filter(is_read=False).count(),
    })


@login_required
@require_POST
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.mark_read()
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})
