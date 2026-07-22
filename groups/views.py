from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Group, GroupMember
from .forms import GroupForm
from django.contrib.auth.models import User

@login_required
def group_list_view(request):
    # Search functionality
    query = request.GET.get('search', '')
    memberships = GroupMember.objects.filter(user=request.user)
    
    if query:
        memberships = memberships.filter(group__name__icontains=query)
        
    groups = [m.group for m in memberships]
    return render(request, 'groups/list.html', {'groups': groups, 'query': query})

@login_required
def group_detail_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Check if user is a member
    if not GroupMember.objects.filter(group=group, user=request.user).exists():
        messages.error(request, "You are not a member of this group.")
        return redirect('groups:list')
    
    members = GroupMember.objects.filter(group=group).select_related('user')
    # Fetch recent expenses
    expenses = group.expenses.all().order_by('-date', '-created_at')[:10]
    
    # Generate WhatsApp invite text
    domain = request.get_host()
    invite_url = f"http://{domain}/groups/join/{group.invite_code}/"
    whatsapp_text = f"Join our expense sharing group '{group.name}' on SmartSplit! Use this link to join: {invite_url} or join using the code: {group.invite_code}"
    import urllib.parse
    whatsapp_share_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(whatsapp_text)}"

    context = {
        'group': group,
        'members': members,
        'expenses': expenses,
        'invite_url': invite_url,
        'whatsapp_share_url': whatsapp_share_url
    }
    return render(request, 'groups/detail.html', context)

@login_required
def group_create_view(request):
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            # Add creator as a member
            GroupMember.objects.create(group=group, user=request.user)
            messages.success(request, f"Group '{group.name}' created successfully!")
            
            # Send dynamic notification to creator
            from notifications.models import Notification
            Notification.objects.create(
                user=request.user,
                title="Group Created",
                message=f"You successfully created the group '{group.name}'."
            )
            
            return redirect('groups:detail', group_id=group.id)
    else:
        form = GroupForm()
    return render(request, 'groups/create.html', {'form': form})

@login_required
def group_edit_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    # Only creator can edit
    if group.created_by != request.user:
        messages.error(request, "Only the group creator can edit this group.")
        return redirect('groups:detail', group_id=group.id)
        
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "Group details updated!")
            return redirect('groups:detail', group_id=group.id)
    else:
        form = GroupForm(instance=group)
    return render(request, 'groups/edit.html', {'form': form, 'group': group})

@login_required
def group_delete_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if group.created_by != request.user:
        messages.error(request, "Only the group creator can delete this group.")
        return redirect('groups:detail', group_id=group.id)
        
    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f"Group '{group_name}' was successfully deleted.")
        return redirect('groups:list')
    return render(request, 'groups/delete.html', {'group': group})

@login_required
def join_group_code_view(request):
    if request.method == 'POST':
        code = request.POST.get('invite_code', '').strip().upper()
        try:
            group = Group.objects.get(invite_code=code)
            # Check if already a member
            if GroupMember.objects.filter(group=group, user=request.user).exists():
                messages.warning(request, f"You are already a member of '{group.name}'.")
                return redirect('groups:detail', group_id=group.id)
            
            GroupMember.objects.create(group=group, user=request.user)
            messages.success(request, f"Successfully joined '{group.name}'!")
            
            # Notifications
            from notifications.models import Notification
            Notification.objects.create(
                user=request.user,
                title="Joined Group",
                message=f"You joined the group '{group.name}'."
            )
            # Notify group creator
            Notification.objects.create(
                user=group.created_by,
                title="New Group Member",
                message=f"{request.user.username} joined your group '{group.name}' using invite code."
            )
            
            return redirect('groups:detail', group_id=group.id)
        except Group.DoesNotExist:
            messages.error(request, "Invalid invite code. Please try again.")
            return redirect('dashboard:home')
            
    return redirect('dashboard:home')

@login_required
def join_group_link_view(request, invite_code):
    invite_code = invite_code.upper()
    group = get_object_or_404(Group, invite_code=invite_code)
    
    # Check if already a member
    if GroupMember.objects.filter(group=group, user=request.user).exists():
        messages.warning(request, f"You are already a member of '{group.name}'.")
        return redirect('groups:detail', group_id=group.id)
        
    if request.method == 'POST':
        GroupMember.objects.create(group=group, user=request.user)
        messages.success(request, f"Successfully joined '{group.name}'!")
        
        # Notifications
        from notifications.models import Notification
        Notification.objects.create(
            user=request.user,
            title="Joined Group",
            message=f"You joined the group '{group.name}'."
        )
        Notification.objects.create(
            user=group.created_by,
            title="New Group Member",
            message=f"{request.user.username} joined your group '{group.name}' via invite link."
        )
        
        return redirect('groups:detail', group_id=group.id)
        
    return render(request, 'groups/join_confirm.html', {'group': group})

@login_required
def leave_group_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    member = get_object_or_404(GroupMember, group=group, user=request.user)
    
    if group.created_by == request.user:
        messages.error(request, "The group creator cannot leave the group. You must transfer ownership or delete the group.")
        return redirect('groups:detail', group_id=group.id)
        
    if request.method == 'POST':
        member.delete()
        messages.success(request, f"You have left the group '{group.name}'.")
        return redirect('groups:list')
        
    return render(request, 'groups/leave_confirm.html', {'group': group})

@login_required
def remove_member_view(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)
    # Only group creator can remove members
    if group.created_by != request.user:
        messages.error(request, "Only the group creator can remove members.")
        return redirect('groups:detail', group_id=group.id)
        
    user_to_remove = get_object_or_404(User, id=user_id)
    if user_to_remove == request.user:
        messages.error(request, "You cannot remove yourself. Leave the group instead.")
        return redirect('groups:detail', group_id=group.id)
        
    member = get_object_or_404(GroupMember, group=group, user=user_to_remove)
    if request.method == 'POST':
        member.delete()
        messages.success(request, f"Removed {user_to_remove.username} from the group.")
        
        # Notify removed user
        from notifications.models import Notification
        Notification.objects.create(
            user=user_to_remove,
            title="Removed from Group",
            message=f"You have been removed from the group '{group.name}' by the creator."
        )
        
        return redirect('groups:detail', group_id=group.id)
        
    return render(request, 'groups/remove_member_confirm.html', {'group': group, 'member_user': user_to_remove})
