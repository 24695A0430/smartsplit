from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from groups.models import Group, GroupMember
from expenses.models import Expense, ExpenseSplit
from .calculations import calculate_group_balances

class DebtSimplificationTestCase(TestCase):
    def setUp(self):
        # Create users
        self.ravi = User.objects.create_user(username='ravi', email='ravi@example.com', password='testpass123')
        self.sreeja = User.objects.create_user(username='sreeja', email='sreeja@example.com', password='testpass123')
        self.rahul = User.objects.create_user(username='rahul', email='rahul@example.com', password='testpass123')
        
        # Create group
        self.group = Group.objects.create(name='Goa Trip', created_by=self.ravi)
        GroupMember.objects.create(group=self.group, user=self.ravi)
        GroupMember.objects.create(group=self.group, user=self.sreeja)
        GroupMember.objects.create(group=self.group, user=self.rahul)

    def test_debt_calculation_multiple_expenses(self):
        # 1. Cab booking paid by Ravi - 800
        cab = Expense.objects.create(
            group=self.group, title='Cab Booking', amount=Decimal('800.00'),
            paid_by=self.ravi, split_type='EQUAL'
        )
        # Create splits (266.67, 266.67, 266.66)
        ExpenseSplit.objects.create(expense=cab, user=self.ravi, amount=Decimal('266.67'))
        ExpenseSplit.objects.create(expense=cab, user=self.sreeja, amount=Decimal('266.67'))
        ExpenseSplit.objects.create(expense=cab, user=self.rahul, amount=Decimal('266.66'))

        # 2. Hotel stay paid by Sreeja - 1200
        hotel = Expense.objects.create(
            group=self.group, title='Hotel Stay', amount=Decimal('1200.00'),
            paid_by=self.sreeja, split_type='EQUAL'
        )
        ExpenseSplit.objects.create(expense=hotel, user=self.ravi, amount=Decimal('400.00'))
        ExpenseSplit.objects.create(expense=hotel, user=self.sreeja, amount=Decimal('400.00'))
        ExpenseSplit.objects.create(expense=hotel, user=self.rahul, amount=Decimal('400.00'))

        # 3. Dinner paid by Rahul - 600
        dinner = Expense.objects.create(
            group=self.group, title='Dinner Party', amount=Decimal('600.00'),
            paid_by=self.rahul, split_type='EQUAL'
        )
        ExpenseSplit.objects.create(expense=dinner, user=self.ravi, amount=Decimal('200.00'))
        ExpenseSplit.objects.create(expense=dinner, user=self.sreeja, amount=Decimal('200.00'))
        ExpenseSplit.objects.create(expense=dinner, user=self.rahul, amount=Decimal('200.00'))

        # Execute balance calculation
        member_balances, simplified_debts = calculate_group_balances(self.group)

        # Assert net balances
        # Ravi: Paid 800, Share (266.67 + 400 + 200) = 866.67. Net = 800 - 866.67 = -66.67
        self.assertEqual(member_balances[self.ravi.id]['net_balance'], Decimal('-66.67'))
        # Sreeja: Paid 1200, Share (266.67 + 400 + 200) = 866.67. Net = 1200 - 866.67 = +333.33
        self.assertEqual(member_balances[self.sreeja.id]['net_balance'], Decimal('333.33'))
        # Rahul: Paid 600, Share (266.66 + 400 + 200) = 866.66. Net = 600 - 866.66 = -266.66
        self.assertEqual(member_balances[self.rahul.id]['net_balance'], Decimal('-266.66'))

        # Assert simplified debt counts & transactions
        self.assertEqual(len(simplified_debts), 2)
        
        # Debts: Rahul owes Sreeja 266.66, Ravi owes Sreeja 66.67
        # Verify Rahul owes Sreeja
        rahul_to_sreeja = [d for d in simplified_debts if d['debtor'] == self.rahul and d['creditor'] == self.sreeja]
        self.assertEqual(len(rahul_to_sreeja), 1)
        self.assertEqual(rahul_to_sreeja[0]['amount'], Decimal('266.66'))

        # Verify Ravi owes Sreeja
        ravi_to_sreeja = [d for d in simplified_debts if d['debtor'] == self.ravi and d['creditor'] == self.sreeja]
        self.assertEqual(len(ravi_to_sreeja), 1)
        self.assertEqual(ravi_to_sreeja[0]['amount'], Decimal('66.67'))

    def test_rejected_payment_does_not_affect_balances(self):
        from payments.models import Payment
        from settlements.models import Settlement
        
        # Log a single expense of 300 paid by Sreeja:
        expense = Expense.objects.create(
            group=self.group, title='Lunch', amount=Decimal('300.00'),
            paid_by=self.sreeja, split_type='EQUAL'
        )
        ExpenseSplit.objects.create(expense=expense, user=self.ravi, amount=Decimal('100.00'))
        ExpenseSplit.objects.create(expense=expense, user=self.sreeja, amount=Decimal('100.00'))
        ExpenseSplit.objects.create(expense=expense, user=self.rahul, amount=Decimal('100.00'))

        # Record a manual payment of 100 from Rahul to Sreeja (PENDING)
        pm = Payment.objects.create(
            group=self.group, amount=Decimal('100.00'),
            paid_by=self.rahul, paid_to=self.sreeja,
            payment_method='CASH', status='PENDING'
        )
        st = Settlement.objects.create(
            group=self.group, debtor=self.rahul, creditor=self.sreeja,
            amount=Decimal('100.00'), payment=pm, status='PENDING'
        )
        
        # PENDING payment shouldn't reduce Rahul's debt (still -100)
        balances, _ = calculate_group_balances(self.group)
        self.assertEqual(balances[self.rahul.id]['net_balance'], Decimal('-100.00'))
        
        # Now REJECT the payment:
        pm.status = 'REJECTED'
        pm.save()
        st.status = 'REJECTED'
        st.save()
        
        # Balances should still be -100 (no changes occur)
        balances, _ = calculate_group_balances(self.group)
        self.assertEqual(balances[self.rahul.id]['net_balance'], Decimal('-100.00'))
