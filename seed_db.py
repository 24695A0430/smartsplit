import os
import django
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsplit.settings')
django.setup()

from django.contrib.auth.models import User
from groups.models import Group, GroupMember
from expenses.models import Expense, ExpenseSplit
from notifications.models import Notification

def seed():
    print("Seeding database...")
    
    # 1. Create Users
    users_data = [
        {'username': 'ravi', 'email': 'ravi@example.com', 'first_name': 'Ravi', 'last_name': 'Kumar'},
        {'username': 'sreeja', 'email': 'sreeja@example.com', 'first_name': 'Sreeja', 'last_name': 'R'},
        {'username': 'rahul', 'email': 'rahul@example.com', 'first_name': 'Rahul', 'last_name': 'Sharma'},
    ]
    
    users = {}
    for ud in users_data:
        user, created = User.objects.get_or_create(username=ud['username'], defaults={
            'email': ud['email'],
            'first_name': ud['first_name'],
            'last_name': ud['last_name']
        })
        if created:
            user.set_password('testpass123')
            user.save()
            print(f"Created user {user.username}")
        users[user.username] = user

    # 2. Create Group
    group, created = Group.objects.get_or_create(name="Goa Trip", defaults={
        'description': "Splits for our weekend Goa Trip",
        'created_by': users['ravi']
    })
    if created:
        print(f"Created group '{group.name}'")
    
    # Add members
    for u in users.values():
        gm, member_created = GroupMember.objects.get_or_create(group=group, user=u)
        if member_created:
            print(f"Added member {u.username} to group '{group.name}'")

    # 3. Create Expenses and Splits
    expenses_data = [
        {'title': 'Cab Booking', 'amount': Decimal('800.00'), 'paid_by': users['ravi'], 'category': 'Travel'},
        {'title': 'Hotel Stay', 'amount': Decimal('1200.00'), 'paid_by': users['sreeja'], 'category': 'Rent'},
        {'title': 'Dinner Party', 'amount': Decimal('600.00'), 'paid_by': users['rahul'], 'category': 'Food'},
    ]

    for ed in expenses_data:
        # Create expense if not exists
        expense, exp_created = Expense.objects.get_or_create(
            group=group,
            title=ed['title'],
            defaults={
                'amount': ed['amount'],
                'paid_by': ed['paid_by'],
                'category': ed['category'],
                'split_type': 'EQUAL',
                'description': f"Logged by seed script for {ed['title']}"
            }
        )
        if exp_created:
            print(f"Created expense '{expense.title}' of Rs.{expense.amount} paid by {expense.paid_by.username}")
            # Create splits equally
            qty = len(users)
            share = round(expense.amount / qty, 2)
            current_sum = Decimal('0.00')
            user_list = list(users.values())
            
            for idx, u in enumerate(user_list):
                if idx == qty - 1:
                    u_amount = expense.amount - current_sum
                else:
                    u_amount = share
                    current_sum += u_amount
                
                ExpenseSplit.objects.create(
                    expense=expense,
                    user=u,
                    amount=u_amount,
                    percentage=Decimal(100) / qty
                )
                print(f"  - Split for {u.username}: Rs.{u_amount}")

    print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed()
