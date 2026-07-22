import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartsplit.settings')
django.setup()

from django.contrib.auth.models import User
from groups.models import Group, GroupMember

def seed_horsley_hills():
    print("Seeding Horsley Hills Trip group...")
    
    # 1. Ensure users exist
    usernames = ['sreeja', 'ravi', 'rahul', 'vini', 'sreeja7443__']
    users = {}
    
    for uname in usernames:
        user, created = User.objects.get_or_create(username=uname, defaults={
            'email': f"{uname}@example.com",
            'first_name': uname.capitalize(),
            'last_name': 'User' if uname != 'sreeja' else 'R'
        })
        if created:
            user.set_password('testpass123')
            user.save()
            print(f"Created user {user.username}")
        users[uname] = user

    # 2. Create Group
    group, created = Group.objects.get_or_create(name="Horsley Hills Trip", defaults={
        'description': "Splits for our trip to Horsley Hills. Let's log diesel, food, and other expenses!",
        'created_by': users['sreeja']
    })
    if created:
        print(f"Created group '{group.name}'")
    else:
        print(f"Group '{group.name}' already exists.")
    
    # Add members
    for u in users.values():
        gm, member_created = GroupMember.objects.get_or_create(group=group, user=u)
        if member_created:
            print(f"Added member {u.username} to group '{group.name}'")
            
    print("Successfully seeded Horsley Hills Trip!")

if __name__ == '__main__':
    seed_horsley_hills()
