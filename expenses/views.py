from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
from groups.models import Group, GroupMember
from .models import Expense, ExpenseSplit
from .forms import ExpenseForm
from notifications.models import Notification

@login_required
def expense_create_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Check if request.user is a member
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:list')

    members = [gm.user for gm in group.members.all()]

    if request.method == 'POST':
        form = ExpenseForm(request.POST, group=group)
        selected_members = request.POST.getlist('split_members')
        
        if form.is_valid():
            expense = form.save(commit=False)
            expense.group = group
            
            # Basic validation: must select at least one member
            if not selected_members:
                form.add_error(None, "You must select at least one member to split the expense with.")
            else:
                total_amount = expense.amount
                split_type = expense.split_type
                splits_to_create = []
                is_valid_splits = True
                
                if split_type == 'EQUAL':
                    # Split equally
                    qty = len(selected_members)
                    share = round(total_amount / qty, 2)
                    current_sum = Decimal('0.00')
                    for idx, m_id in enumerate(selected_members):
                        u = get_object_or_404(User, id=m_id)
                        if idx == qty - 1:
                            u_amount = total_amount - current_sum
                        else:
                            u_amount = share
                            current_sum += u_amount
                        splits_to_create.append(ExpenseSplit(user=u, amount=u_amount, percentage=Decimal(100) / qty))
                
                elif split_type == 'CUSTOM':
                    sum_amounts = Decimal('0.00')
                    for m_id in selected_members:
                        u = get_object_or_404(User, id=m_id)
                        val = request.POST.get(f'custom_amount_{m_id}', '0').strip()
                        try:
                            u_amount = Decimal(val) if val else Decimal('0.00')
                        except:
                            u_amount = Decimal('0.00')
                        sum_amounts += u_amount
                        splits_to_create.append(ExpenseSplit(user=u, amount=u_amount))
                    
                    if sum_amounts != total_amount:
                        form.add_error(None, f"The sum of custom split amounts (₹{sum_amounts}) must equal the total expense amount (₹{total_amount}).")
                        is_valid_splits = False
                        
                elif split_type == 'PERCENT':
                    sum_percents = Decimal('0.00')
                    percent_shares = []
                    for m_id in selected_members:
                        u = get_object_or_404(User, id=m_id)
                        val = request.POST.get(f'percent_{m_id}', '0').strip()
                        try:
                            u_pct = Decimal(val) if val else Decimal('0.00')
                        except:
                            u_pct = Decimal('0.00')
                        sum_percents += u_pct
                        percent_shares.append((u, u_pct))
                    
                    if sum_percents != Decimal('100.00'):
                        form.add_error(None, f"The sum of percentages ({sum_percents}%) must equal exactly 100%.")
                        is_valid_splits = False
                    else:
                        qty = len(percent_shares)
                        current_sum = Decimal('0.00')
                        for idx, (u, pct) in enumerate(percent_shares):
                            if idx == qty - 1:
                                u_amount = total_amount - current_sum
                            else:
                                u_amount = round(total_amount * (pct / Decimal('100.00')), 2)
                                current_sum += u_amount
                            splits_to_create.append(ExpenseSplit(user=u, amount=u_amount, percentage=pct))
                
                if is_valid_splits:
                    action = request.POST.get('action', 'save_manual')
                    if action == 'pay_now':
                        request.session['pending_expense'] = {
                            'expense': {
                                'title': expense.title,
                                'description': expense.description,
                                'amount': str(expense.amount),
                                'date': str(expense.date),
                                'category': expense.category,
                                'paid_by_id': expense.paid_by_id,
                                'split_type': expense.split_type,
                                'notes': expense.notes,
                                'group_id': group.id
                            },
                            'splits': [
                                {
                                    'user_id': sp.user_id,
                                    'amount': str(sp.amount),
                                    'percentage': str(sp.percentage) if sp.percentage else None
                                } for sp in splits_to_create
                            ]
                        }
                        return redirect('payments:checkout_expense')
                    else:
                        expense.save()
                        for sp in splits_to_create:
                            sp.expense = expense
                            sp.save()
                        
                        # Notify other members
                        for m in members:
                            if m != request.user:
                                Notification.objects.create(
                                    user=m,
                                    title="New Expense Added",
                                    message=f"{request.user.username} added '{expense.title}' of ₹{expense.amount} in '{group.name}'."
                                )
                        
                        messages.success(request, f"Expense '{expense.title}' recorded successfully!")
                        return redirect('groups:detail', group_id=group.id)
        else:
            messages.error(request, "Failed to log expense. Please fix errors.")
    else:
        form = ExpenseForm(group=group, initial={'paid_by': request.user, 'date': timezone.now().date()})
        # Default all members selected
        selected_members = [str(m.id) for m in members]

    # Re-fetch form and pre-fill selected members
    context = {
        'form': form,
        'group': group,
        'members': members,
        'selected_members': selected_members,
    }
    return render(request, 'expenses/create.html', context)

@login_required
def expense_edit_view(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    group = expense.group
    
    # Check if request.user is a member
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:list')

    members = [gm.user for gm in group.members.all()]
    current_splits = {sp.user_id: sp for sp in expense.splits.all()}

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, group=group)
        selected_members = request.POST.getlist('split_members')
        
        if form.is_valid():
            expense = form.save(commit=False)
            
            if not selected_members:
                form.add_error(None, "You must select at least one member to split the expense with.")
            else:
                total_amount = expense.amount
                split_type = expense.split_type
                splits_to_create = []
                is_valid_splits = True
                
                if split_type == 'EQUAL':
                    qty = len(selected_members)
                    share = round(total_amount / qty, 2)
                    current_sum = Decimal('0.00')
                    for idx, m_id in enumerate(selected_members):
                        u = get_object_or_404(User, id=m_id)
                        if idx == qty - 1:
                            u_amount = total_amount - current_sum
                        else:
                            u_amount = share
                            current_sum += u_amount
                        splits_to_create.append(ExpenseSplit(user=u, amount=u_amount, percentage=Decimal(100) / qty))
                
                elif split_type == 'CUSTOM':
                    sum_amounts = Decimal('0.00')
                    for m_id in selected_members:
                        u = get_object_or_404(User, id=m_id)
                        val = request.POST.get(f'custom_amount_{m_id}', '0').strip()
                        try:
                            u_amount = Decimal(val) if val else Decimal('0.00')
                        except:
                            u_amount = Decimal('0.00')
                        sum_amounts += u_amount
                        splits_to_create.append(ExpenseSplit(user=u, amount=u_amount))
                    
                    if sum_amounts != total_amount:
                        form.add_error(None, f"The sum of custom split amounts (₹{sum_amounts}) must equal the total expense amount (₹{total_amount}).")
                        is_valid_splits = False
                        
                elif split_type == 'PERCENT':
                    sum_percents = Decimal('0.00')
                    percent_shares = []
                    for m_id in selected_members:
                        u = get_object_or_404(User, id=m_id)
                        val = request.POST.get(f'percent_{m_id}', '0').strip()
                        try:
                            u_pct = Decimal(val) if val else Decimal('0.00')
                        except:
                            u_pct = Decimal('0.00')
                        sum_percents += u_pct
                        percent_shares.append((u, u_pct))
                    
                    if sum_percents != Decimal('100.00'):
                        form.add_error(None, f"The sum of percentages ({sum_percents}%) must equal exactly 100%.")
                        is_valid_splits = False
                    else:
                        qty = len(percent_shares)
                        current_sum = Decimal('0.00')
                        for idx, (u, pct) in enumerate(percent_shares):
                            if idx == qty - 1:
                                u_amount = total_amount - current_sum
                            else:
                                u_amount = round(total_amount * (pct / Decimal('100.00')), 2)
                                current_sum += u_amount
                            splits_to_create.append(ExpenseSplit(user=u, amount=u_amount, percentage=pct))
                
                if is_valid_splits:
                    expense.save()
                    # Delete old splits and write new ones
                    expense.splits.all().delete()
                    for sp in splits_to_create:
                        sp.expense = expense
                        sp.save()
                        
                    messages.success(request, f"Expense '{expense.title}' updated successfully!")
                    return redirect('groups:detail', group_id=group.id)
        else:
            messages.error(request, "Failed to update expense. Please check input values.")
    else:
        form = ExpenseForm(instance=expense, group=group)
        selected_members = [str(uid) for uid in current_splits.keys()]

    members_with_splits = []
    for m in members:
        split = current_splits.get(m.id)
        if request.method == 'POST':
            is_selected = str(m.id) in selected_members
            amt = request.POST.get(f'custom_amount_{m.id}', '0.00')
            pct = request.POST.get(f'percent_{m.id}', '0.00')
        else:
            is_selected = split is not None
            amt = split.amount if split else Decimal('0.00')
            pct = split.percentage if split else Decimal('0.00')
            
        members_with_splits.append({
            'user': m,
            'is_selected': is_selected,
            'amount': amt,
            'percentage': pct,
        })

    context = {
        'form': form,
        'expense': expense,
        'group': group,
        'members_with_splits': members_with_splits,
        'selected_members': selected_members,
    }
    return render(request, 'expenses/edit.html', context)

@login_required
def expense_detail_view(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    # Check membership
    if not GroupMember.objects.filter(group=expense.group, user=request.user).exists():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:list')
    
    splits = expense.splits.all().select_related('user')
    return render(request, 'expenses/detail.html', {'expense': expense, 'splits': splits})

@login_required
def expense_delete_view(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    group = expense.group
    
    # Authorized if paid_by user or group creator
    if expense.paid_by != request.user and group.created_by != request.user:
        messages.error(request, "You are not authorized to delete this expense.")
        return redirect('groups:detail', group_id=group.id)
        
    if request.method == 'POST':
        title = expense.title
        expense.delete()
        messages.success(request, f"Expense '{title}' was deleted.")
        return redirect('groups:detail', group_id=group.id)
        
    return render(request, 'expenses/delete.html', {'expense': expense})
