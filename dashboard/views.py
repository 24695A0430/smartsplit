from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from groups.models import Group, GroupMember
from expenses.models import Expense, ExpenseSplit
from payments.models import Payment
from settlements.models import Settlement
from settlements.calculations import calculate_group_balances
from notifications.models import Notification
from decimal import Decimal
import datetime

@login_required
def dashboard_home_view(request):
    # Fetch all user group memberships
    memberships = GroupMember.objects.filter(user=request.user).select_related('group')
    group_ids = [m.group_id for m in memberships]
    
    total_groups = len(group_ids)
    total_paid = Decimal('0.00')
    total_owed = Decimal('0.00')
    total_receivable = Decimal('0.00')
    
    # Calculate aggregate metrics from group balances
    for gid in group_ids:
        group = Group.objects.get(id=gid)
        member_balances, _ = calculate_group_balances(group)
        if request.user.id in member_balances:
            data = member_balances[request.user.id]
            total_paid += data['paid_expenses']
            net = data['net_balance']
            if net > 0:
                total_receivable += net
            elif net < 0:
                total_owed += abs(net)

    # Fetch total expenses in user's groups
    total_expenses_amount = Expense.objects.filter(group_id__in=group_ids).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Fetch recent transactions (expenses & payments combined/separately)
    recent_expenses = Expense.objects.filter(group_id__in=group_ids).select_related('group', 'paid_by').order_by('-date', '-created_at')[:5]
    recent_payments = Payment.objects.filter(
        Q(paid_by=request.user) | Q(paid_to=request.user)
    ).select_related('paid_by', 'paid_to', 'group').order_by('-date', '-created_at')[:5]

    # Fetch pending approvals (where user is creditor and payment status is PENDING)
    pending_approvals = Settlement.objects.filter(
        creditor=request.user, status='PENDING'
    ).select_related('debtor', 'group', 'payment')

    # Chart 1: Expenses by Category for the current user (using ExpenseSplit)
    category_data = ExpenseSplit.objects.filter(
        user=request.user
    ).values('expense__category').annotate(total=Sum('amount')).order_by('-total')
    
    categories = [item['expense__category'] for item in category_data]
    category_totals = [float(item['total']) for item in category_data]

    # Chart 2: Monthly trend of user's expense shares
    today = datetime.date.today()
    six_months_ago = today - datetime.timedelta(days=180)
    monthly_data = ExpenseSplit.objects.filter(
        user=request.user,
        expense__date__gte=six_months_ago
    ).values('expense__date__year', 'expense__date__month').annotate(total=Sum('amount')).order_by('expense__date__year', 'expense__date__month')

    months = []
    monthly_totals = []
    for item in monthly_data:
        m_str = datetime.date(item['expense__date__year'], item['expense__date__month'], 1).strftime('%b %Y')
        months.append(m_str)
        monthly_totals.append(float(item['total']))

    # Global search functionality (Groups, members, expenses, transactions)
    search_query = request.GET.get('q', '').strip()
    search_results = None
    if search_query:
        # Search Groups
        found_groups = Group.objects.filter(id__in=group_ids, name__icontains=search_query)
        # Search Expenses
        found_expenses = Expense.objects.filter(group_id__in=group_ids, title__icontains=search_query)
        # Search Payments
        found_payments = Payment.objects.filter(
            Q(group_id__in=group_ids),
            Q(paid_by__username__icontains=search_query) | 
            Q(paid_to__username__icontains=search_query) |
            Q(transaction_id__icontains=search_query)
        )
        search_results = {
            'groups': found_groups,
            'expenses': found_expenses,
            'payments': found_payments,
        }

    context = {
        'total_groups': total_groups,
        'total_paid': total_paid,
        'total_owed': total_owed,
        'total_receivable': total_receivable,
        'total_expenses_amount': total_expenses_amount,
        'recent_expenses': recent_expenses,
        'recent_payments': recent_payments,
        'pending_approvals': pending_approvals,
        'categories': categories,
        'category_totals': category_totals,
        'months': months,
        'monthly_totals': monthly_totals,
        'search_query': search_query,
        'search_results': search_results,
    }
    return render(request, 'dashboard/index.html', context)
