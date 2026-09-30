from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
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
    status = request.GET.get('status', '')
    if status in dict(Invoice.STATUS_CHOICES):
        invoices = invoices.filter(status=status)
    if not request.user.is_superuser and request.user.profile.role == 'doctor':
        invoices = invoices.filter(medical_record__appointment__doctor__user=request.user)
    return render(request, 'billing/invoice_list.html', {'invoices': invoices, 'status_filter': status})


@login_required
@role_required('admin', 'staff', 'doctor')
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            'medical_record__appointment__patient',
            'medical_record__appointment__doctor',
        ).prefetch_related('services', 'medical_record__prescriptions__medicine'),
        pk=pk,
    )
    if (not request.user.is_superuser
            and request.user.profile.role == 'doctor'
            and invoice.medical_record.appointment.doctor.user != request.user):
        raise PermissionDenied
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})


@login_required
@role_required('admin', 'staff')
def invoice_update(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
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
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.status = 'Paid'
    invoice.save(update_fields=['status'])
    messages.success(request, f'Hóa đơn #{invoice.pk} đã được đánh dấu đã thanh toán.')
    return redirect('billing:detail', pk=pk)
