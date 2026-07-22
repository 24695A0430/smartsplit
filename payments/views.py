import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from groups.models import Group, GroupMember
from django.contrib.auth.models import User
from .models import Payment
from .forms import PaymentForm
from settlements.models import Settlement
from notifications.models import Notification

@login_required
def record_payment_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:list')

    if request.method == 'POST':
        form = PaymentForm(request.POST, group=group, user=request.user)
        if form.is_valid():
            payment = form.save(commit=False)
            
            # Check if there is already a pending payment to this payee
            duplicate_exists = Payment.objects.filter(
                group=group,
                paid_by=request.user,
                paid_to=payment.paid_to,
                status='PENDING'
            ).exists()
            if duplicate_exists:
                messages.error(request, f"You already have a pending payment to {payment.paid_to.username} awaiting approval. Please wait for them to confirm it.")
                return redirect('settlements:dashboard', group_id=group.id)

            payment.group = group
            payment.paid_by = request.user
            # Manual payments require payee approval, so start as PENDING
            payment.status = 'PENDING'
            payment.transaction_id = f"MANUAL-{uuid.uuid4().hex[:10].upper()}"
            payment.save()

            # Create corresponding settlement
            Settlement.objects.create(
                group=group,
                debtor=request.user,
                creditor=payment.paid_to,
                amount=payment.amount,
                payment=payment,
                status='PENDING'
            )

            # Notify payee
            Notification.objects.create(
                user=payment.paid_to,
                title="Payment Recorded (Pending)",
                message=f"{request.user.username} recorded a manual payment of ₹{payment.amount} to you. Please confirm to settle."
            )

            messages.success(request, f"Manual payment of ₹{payment.amount} recorded! Awaiting recipient approval.")
            return redirect('groups:detail', group_id=group.id)
    else:
        # Check if paying a specific user from query param
        target_payee_id = request.GET.get('payee_id')
        target_amount = request.GET.get('amount')
        
        if target_payee_id:
            # Check if there is already a pending payment to this payee
            duplicate_exists = Payment.objects.filter(
                group=group,
                paid_by=request.user,
                paid_to_id=target_payee_id,
                status='PENDING'
            ).exists()
            if duplicate_exists:
                payee_user = User.objects.filter(id=target_payee_id).first()
                payee_name = payee_user.username if payee_user else "this member"
                messages.warning(request, f"You already have a pending payment to {payee_name} awaiting approval. Please wait for them to confirm it.")
                return redirect('settlements:dashboard', group_id=group.id)

        initial_data = {'date': timezone.now().date()}
        if target_payee_id:
            initial_data['paid_to'] = target_payee_id
        if target_amount:
            initial_data['amount'] = target_amount
            
        form = PaymentForm(group=group, user=request.user, initial=initial_data)

    return render(request, 'payments/record.html', {'form': form, 'group': group})

@login_required
def checkout_view(request, group_id, payee_id):
    group = get_object_or_404(Group, id=group_id)
    payee = get_object_or_404(User, id=payee_id)
    amount = request.GET.get('amount', '0.00')

    # Basic membership check
    if not GroupMember.objects.filter(group=group, user=request.user).exists() or \
       not GroupMember.objects.filter(group=group, user=payee).exists():
        messages.error(request, "Invalid group membership context for payment.")
        return redirect('groups:list')

    # Check if there is already a pending payment to this payee
    duplicate_exists = Payment.objects.filter(
        group=group,
        paid_by=request.user,
        paid_to=payee,
        status='PENDING'
    ).exists()
    if duplicate_exists:
        messages.warning(request, f"You already have a pending payment to {payee.username} awaiting approval. Please wait for them to confirm it.")
        return redirect('settlements:dashboard', group_id=group.id)

    return render(request, 'payments/pay_now.html', {
        'group': group,
        'payee': payee,
        'amount': amount,
    })

@login_required
def process_payment_view(request, group_id, payee_id):
    if request.method != 'POST':
        return redirect('groups:list')

    group = get_object_or_404(Group, id=group_id)
    payee = get_object_or_404(User, id=payee_id)
    
    # Check if there is already a pending payment to this payee
    duplicate_exists = Payment.objects.filter(
        group=group,
        paid_by=request.user,
        paid_to=payee,
        status='PENDING'
    ).exists()
    if duplicate_exists:
        messages.error(request, f"You already have a pending payment to {payee.username} awaiting approval.")
        return redirect('settlements:dashboard', group_id=group.id)

    amount_str = request.POST.get('amount', '0.00')
    payment_method = request.POST.get('payment_method', 'UPI')
    simulate_status = request.POST.get('simulate_status', 'SUCCESS') # success or failed

    try:
        amount = float(amount_str)
    except ValueError:
        amount = 0.00

    # Create Payment transaction
    tx_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    payment = Payment.objects.create(
        group=group,
        amount=amount,
        paid_by=request.user,
        paid_to=payee,
        payment_method=payment_method,
        status=simulate_status,
        transaction_id=tx_id,
        notes="Online payment simulation."
    )

    if simulate_status == 'SUCCESS':
        # Create completed settlement
        Settlement.objects.create(
            group=group,
            debtor=request.user,
            creditor=payee,
            amount=amount,
            payment=payment,
            status='COMPLETED'
        )

        # Notify creditor
        Notification.objects.create(
            user=payee,
            title="Payment Received",
            message=f"{request.user.username} settled ₹{amount} to you via online checkout."
        )
        
        return redirect('payments:success', payment_id=payment.id)
    elif simulate_status == 'PENDING':
        # Create pending settlement
        Settlement.objects.create(
            group=group,
            debtor=request.user,
            creditor=payee,
            amount=amount,
            payment=payment,
            status='PENDING'
        )

        # Notify creditor
        Notification.objects.create(
            user=payee,
            title="Payment Recorded (Pending)",
            message=f"{request.user.username} recorded a payment of ₹{amount} to you via UPI. Please confirm receipt."
        )
        
        return redirect('payments:success', payment_id=payment.id)
    else:
        return redirect('payments:failed', payment_id=payment.id)

@login_required
def payment_success_view(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, paid_by=request.user)
    return render(request, 'payments/success.html', {'payment': payment})

@login_required
def payment_failed_view(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id, paid_by=request.user)
    return render(request, 'payments/failed.html', {'payment': payment})

@login_required
def transaction_history_view(request):
    # Retrieve all payments sent or received by user
    payments = Payment.objects.filter(
        Q(paid_by=request.user) | Q(paid_to=request.user)
    ).select_related('paid_by', 'paid_to', 'group').order_by('-date', '-created_at')

    # Search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        payments = payments.filter(
            Q(group__name__icontains=search_query) |
            Q(paid_by__username__icontains=search_query) |
            Q(paid_to__username__icontains=search_query) |
            Q(transaction_id__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    # Filter by Group
    group_filter = request.GET.get('group', '').strip()
    if group_filter:
        payments = payments.filter(group_id=group_filter)

    # Filter by Method
    method_filter = request.GET.get('method', '').strip()
    if method_filter:
        payments = payments.filter(payment_method=method_filter)

    # Filter by Status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        payments = payments.filter(status=status_filter)

    # Fetch groups for filter dropdown
    member_groups = [gm.group for gm in GroupMember.objects.filter(user=request.user).select_related('group')]

    # Sorting
    sort_by = request.GET.get('sort', '-date')
    if sort_by in ['date', '-date', 'amount', '-amount']:
        payments = payments.order_by(sort_by)

    # Pagination: 10 transactions per page
    from django.core.paginator import Paginator
    paginator = Paginator(payments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'payments': page_obj,
        'page_obj': page_obj,
        'groups': member_groups,
        'search_query': search_query,
        'selected_group': group_filter,
        'selected_method': method_filter,
        'selected_status': status_filter,
        'selected_sort': sort_by,
        'method_choices': Payment.METHOD_CHOICES,
        'status_choices': Payment.STATUS_CHOICES,
    }
    return render(request, 'payments/history.html', context)

@login_required
def checkout_expense_view(request):
    pending_expense = request.session.get('pending_expense')
    if not pending_expense:
        messages.error(request, "No pending expense transaction found.")
        return redirect('dashboard:home')
        
    expense_data = pending_expense['expense']
    group = get_object_or_404(Group, id=expense_data['group_id'])
    
    return render(request, 'payments/checkout_expense.html', {
        'expense': expense_data,
        'group': group,
    })

@login_required
def process_expense_payment_view(request):
    if request.method != 'POST':
        return redirect('dashboard:home')
        
    pending_expense = request.session.get('pending_expense')
    if not pending_expense:
        messages.error(request, "No pending expense transaction found.")
        return redirect('dashboard:home')
        
    expense_data = pending_expense['expense']
    splits_data = pending_expense['splits']
    
    payment_method = request.POST.get('payment_method', 'UPI')
    simulate_status = request.POST.get('simulate_status', 'SUCCESS')
    
    group = get_object_or_404(Group, id=expense_data['group_id'])
    amount = Decimal(expense_data['amount'])
    
    # Create Payment transaction
    tx_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    payment = Payment.objects.create(
        group=group,
        amount=amount,
        paid_by=request.user,
        paid_to=None, # None denotes payment to merchant
        payment_method=payment_method,
        status=simulate_status,
        transaction_id=tx_id,
        notes=f"Online pre-payment for: {expense_data['title']}"
    )
    
    if simulate_status == 'SUCCESS':
        from expenses.models import Expense, ExpenseSplit
        from django.contrib.auth.models import User
        
        paid_by_user = get_object_or_404(User, id=expense_data['paid_by_id'])
        
        # Save Expense
        expense = Expense.objects.create(
            group=group,
            title=expense_data['title'],
            description=expense_data['description'],
            amount=amount,
            date=expense_data['date'],
            category=expense_data['category'],
            paid_by=paid_by_user,
            split_type=expense_data['split_type'],
            notes=expense_data['notes']
        )
        
        # Save Splits
        for sp in splits_data:
            user = get_object_or_404(User, id=sp['user_id'])
            pct = Decimal(sp['percentage']) if sp['percentage'] else None
            ExpenseSplit.objects.create(
                expense=expense,
                user=user,
                amount=Decimal(sp['amount']),
                percentage=pct
            )
            
        # Clear session
        del request.session['pending_expense']
        
        # Notify members
        members = [gm.user for gm in group.members.all()]
        for m in members:
            Notification.objects.create(
                user=m,
                title="Expense Payment Completed",
                message=f"Pre-paid expense '{expense.title}' of ₹{expense.amount} was recorded in '{group.name}' by {paid_by_user.username}."
            )
            
        messages.success(request, f"Payment successful! Expense '{expense.title}' recorded.")
        return redirect('payments:success', payment_id=payment.id)
    else:
        del request.session['pending_expense']
        messages.error(request, "Online pre-payment failed. Expense was not recorded.")
        return redirect('payments:failed', payment_id=payment.id)
