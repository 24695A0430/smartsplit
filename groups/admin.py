from django.contrib import admin
from .models import Group, GroupMember

class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 1

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_date', 'invite_code')
    search_fields = ('name', 'created_by__username', 'invite_code')
    inlines = [GroupMemberInline]

@admin.register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'joined_date')
    search_fields = ('group__name', 'user__username')
