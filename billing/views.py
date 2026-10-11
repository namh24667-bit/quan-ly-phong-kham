from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required

from .forms import InvoiceForm
from .models import Invoice


@login_required
@role_required('admin', 'staff', 'doctor')
def invoice_list(request):
    invoices = Invoice.objects.select_related(
        'medical_record__appointment__patient',
        'medical_record__appointment__doctor',
    ).prefetch_related('services')
    if not request.user.is_superuser and request.user.profile.role == 'doctor':
        invoices = invoices.filter(medical_record__appointment__doctor__user=request.user)

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    if query:
        invoices = invoices.filter(
            Q(medical_record__appointment__patient__full_name__icontains=query)
        )
    if status_filter not in dict(Invoice.STATUS_CHOICES):
        status_filter = ''
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    invoices = invoices.order_by('-created_at', '-pk')
    paginator = Paginator(invoices, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, 'billing/invoice_list.html', {
        'invoices': page_obj,
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'status_choices': Invoice.STATUS_CHOICES,
        'query_string': query_params.urlencode(),
        'total': paginator.count,
        'has_filters': bool(query or status_filter),
    })


@login_required
@role_required('admin', 'staff', 'doctor')
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            'medical_record__appointment__patient',
            'medical_record__appointment__doctor',
        ),
        pk=pk,
    )
    if (not request.user.is_superuser
            and request.user.profile.role == 'doctor'
            and invoice.medical_record.appointment.doctor.user != request.user):
        raise PermissionDenied
    context = {'invoice': invoice}
    if invoice.status == 'Paid':
        if invoice.paid_snapshot is None:
            context['snapshot_warning'] = 'Hóa đơn cũ chưa có bản lưu chi tiết lúc thanh toán; chỉ hiển thị các tổng tiền đã lưu.'
        else:
            try:
                context['paid_snapshot'] = invoice.validate_paid_snapshot(invoice.paid_snapshot)
            except ValueError:
                context['snapshot_warning'] = 'Bản lưu chi tiết hóa đơn không hợp lệ hoặc không được hỗ trợ; chỉ hiển thị các tổng tiền đã lưu.'
    return render(request, 'billing/invoice_detail.html', context)


@login_required
@role_required('admin', 'staff')
def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.status == 'Paid':
        raise PermissionDenied
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            with transaction.atomic():
                invoice = form.save()
                invoice.recalculate()
            messages.success(request, 'Đã cập nhật hóa đơn và tính lại tổng tiền.')
            return redirect('billing:detail', pk=invoice.pk)
    else:
        form = InvoiceForm(instance=invoice)
    return render(request, 'billing/invoice_form.html', {'form': form, 'invoice': invoice})


@login_required
@role_required('admin', 'staff')
def invoice_mark_paid(request, pk):
    if request.method != 'POST':
        return redirect('billing:detail', pk=pk)
    with transaction.atomic():
        invoice = get_object_or_404(
            Invoice.objects.select_related('medical_record__appointment').select_for_update(),
            pk=pk,
        )
        if (invoice.status != 'Pending'
                or invoice.paid_snapshot is not None
                or invoice.medical_record.appointment.status != 'done'):
            raise PermissionDenied
        invoice.recalculate()
        snapshot = invoice.build_paid_snapshot()
        updated = Invoice.objects.filter(pk=pk, status='Pending', paid_snapshot__isnull=True).update(
            status='Paid', paid_snapshot=snapshot,
        )
        if updated != 1:
            raise PermissionDenied
    messages.success(request, f'Hóa đơn #{invoice.pk} đã được đánh dấu đã thanh toán.')
    return redirect('billing:detail', pk=pk)
