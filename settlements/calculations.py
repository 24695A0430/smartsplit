from decimal import Decimal
from django.contrib.auth.models import User
from groups.models import Group, GroupMember
from expenses.models import Expense, ExpenseSplit
from payments.models import Payment

def calculate_group_balances(group):
    """
    Computes net balances for all group members:
    Balance = (Total paid directly for expenses + Payments sent) - (Expense share + Payments received)
    
    Returns:
      - member_balances: Dict mapping user -> dict(paid, share, sent, received, net_balance)
      - simplified_debts: List of dicts specifying who owes whom how much:
        [{'debtor': user1, 'creditor': user2, 'amount': Decimal}]
    """
    members = [gm.user for gm in group.members.all()]
    member_data = {}
    
    for m in members:
        member_data[m.id] = {
            'user': m,
            'paid_expenses': Decimal('0.00'),
            'expense_share': Decimal('0.00'),
            'payments_sent': Decimal('0.00'),
            'payments_received': Decimal('0.00'),
        }

    # 1. Sum up expenses paid by each member and their split shares
    expenses = Expense.objects.filter(group=group)
    for exp in expenses:
        if exp.paid_by_id in member_data:
            member_data[exp.paid_by_id]['paid_expenses'] += exp.amount
            
        for split in exp.splits.all():
            if split.user_id in member_data:
                member_data[split.user_id]['expense_share'] += split.amount

    # 2. Sum up successful payments sent and received
    payments = Payment.objects.filter(group=group, status='SUCCESS')
    for pm in payments:
        if pm.paid_by_id in member_data:
            member_data[pm.paid_by_id]['payments_sent'] += pm.amount
        if pm.paid_to_id in member_data:
            member_data[pm.paid_to_id]['payments_received'] += pm.amount

    # 3. Calculate Net Balance for each member
    debtors = []
    creditors = []
    
    for uid, data in member_data.items():
        net = (data['paid_expenses'] + data['payments_sent']) - (data['expense_share'] + data['payments_received'])
        data['net_balance'] = round(net, 2)
        
        if data['net_balance'] < Decimal('-0.01'):
            debtors.append((uid, data['net_balance']))
        elif data['net_balance'] > Decimal('0.01'):
            creditors.append((uid, data['net_balance']))

    # 4. Simplify debts greedily
    simplified_debts = []
    # Sort debtors ascending (most negative first)
    debtors.sort(key=lambda x: x[1])
    # Sort creditors descending (most positive first)
    creditors.sort(key=lambda x: x[1], reverse=True)

    while debtors and creditors:
        d_id, d_bal = debtors[0]
        c_id, c_bal = creditors[0]
        
        amount_to_settle = min(abs(d_bal), c_bal)
        debtor_user = member_data[d_id]['user']
        creditor_user = member_data[c_id]['user']
        
        simplified_debts.append({
            'debtor': debtor_user,
            'creditor': creditor_user,
            'amount': round(amount_to_settle, 2)
        })
        
        new_d_bal = d_bal + amount_to_settle
        new_c_bal = c_bal - amount_to_settle
        
        if abs(new_d_bal) < Decimal('0.01'):
            debtors.pop(0)
        else:
            debtors[0] = (d_id, new_d_bal)
            
        if abs(new_c_bal) < Decimal('0.01'):
            creditors.pop(0)
        else:
            creditors[0] = (c_id, new_c_bal)

    return member_data, simplified_debts
