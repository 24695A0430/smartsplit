from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from groups.models import Group, GroupMember
from .models import Settlement
from .calculations import calculate_group_balances
from notifications.models import Notification
from django.db.models import Q

@login_required
def group_settlements_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:list')

    # Compute dynamic balances and minimal debt path
    member_balances, simplified_debts = calculate_group_balances(group)

    # Fetch active pending manual settlements in this group
    pending_settlements = Settlement.objects.filter(
        group=group, status='PENDING'
    ).select_related('debtor', 'creditor', 'payment')

    # Fetch history of completed and rejected settlements
    completed_settlements = Settlement.objects.filter(
        group=group, status__in=['COMPLETED', 'REJECTED']
    ).select_related('debtor', 'creditor', 'payment').order_by('-updated_at')

    # Filter debts that involve the logged-in user
    user_debts = [d for d in simplified_debts if d['debtor'] == request.user or d['creditor'] == request.user]

    context = {
        'group': group,
        'member_balances': member_balances,
        'simplified_debts': simplified_debts,
        'user_debts': user_debts,
        'pending_settlements': pending_settlements,
        'completed_settlements': completed_settlements,
    }
    return render(request, 'settlements/dashboard.html', context)

@login_required
def approve_settlement_view(request, settlement_id):
    settlement = get_object_or_404(Settlement, id=settlement_id)
    
    # Check if the user is the creditor of this settlement
    if settlement.creditor != request.user:
        messages.error(request, "Only the recipient of the payment can approve this settlement.")
        return redirect('settlements:dashboard', group_id=settlement.group.id)

    if request.method == 'POST':
        settlement.status = 'COMPLETED'
        settlement.save()

        # Mark corresponding payment as SUCCESS
        if settlement.payment:
            settlement.payment.status = 'SUCCESS'
            settlement.payment.save()

        # Notify debtor (payment approved)
        Notification.objects.create(
            user=settlement.debtor,
            title="Payment Approved",
            message=f"{request.user.username} approved your payment of ₹{settlement.amount}."
        )

        # Notify both (settlement completed)
        Notification.objects.create(
            user=settlement.debtor,
            title="Settlement Completed",
            message=f"Settlement of ₹{settlement.amount} to {settlement.creditor.username} has been completed."
        )
        Notification.objects.create(
            user=settlement.creditor,
            title="Settlement Completed",
            message=f"Settlement of ₹{settlement.amount} from {settlement.debtor.username} has been completed."
        )

        messages.success(request, f"Settlement of ₹{settlement.amount} from {settlement.debtor.username} marked as completed.")
        return redirect('settlements:dashboard', group_id=settlement.group.id)

    return render(request, 'settlements/approve_confirm.html', {'settlement': settlement})

@login_required
def reject_settlement_view(request, settlement_id):
    settlement = get_object_or_404(Settlement, id=settlement_id)
    
    if settlement.creditor != request.user:
        messages.error(request, "Only the recipient can reject this settlement.")
        return redirect('settlements:dashboard', group_id=settlement.group.id)

    if request.method == 'POST':
        settlement.status = 'REJECTED'
        settlement.save()
        
        # Mark payment as REJECTED
        if settlement.payment:
            settlement.payment.status = 'REJECTED'
            settlement.payment.save()

        # Notify debtor
        Notification.objects.create(
            user=settlement.debtor,
            title="Payment Rejected",
            message=f"{request.user.username} rejected your payment record of ₹{settlement.amount}."
        )

        messages.warning(request, "Payment record has been rejected.")
        return redirect('settlements:dashboard', group_id=settlement.group.id)

    return render(request, 'settlements/reject_confirm.html', {'settlement': settlement})
