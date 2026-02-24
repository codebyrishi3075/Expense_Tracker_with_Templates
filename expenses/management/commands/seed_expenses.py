# api_expenses/management/commands/seed_expenses.py
# IMPROVED VERSION WITH USER SELECTION

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from expenses.models import Expense
from budget.models import BudgetCategory, Budget

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with budget categories and expenses for specific user"

    def add_arguments(self, parser):
        """Add command line arguments"""
        parser.add_argument(
            '--email',
            type=str,
            help='Email of user to seed data for (e.g., test@finpocket.com)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Seed data for ALL users (except superusers)'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete existing data before seeding'
        )

    def handle(self, *args, **kwargs):
        email = kwargs.get('email')
        seed_all = kwargs.get('all')
        clean = kwargs.get('clean')

        # ═══════════════════════════════════════════════
        # STEP 1: DETERMINE WHICH USERS TO SEED
        # ═══════════════════════════════════════════════
        
        if seed_all:
            # Seed for all non-superuser users
            users = User.objects.filter(is_superuser=False, is_active=True)
            if not users.exists():
                self.stdout.write(self.style.ERROR("❌ No active non-superuser users found!"))
                return
            
            self.stdout.write(
                self.style.SUCCESS(f"\n🌱 Seeding data for {users.count()} users...")
            )
        
        elif email:
            # Seed for specific user by email
            try:
                users = [User.objects.get(email=email)]
                self.stdout.write(
                    self.style.SUCCESS(f"\n🌱 Seeding data for user: {email}")
                )
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ User with email {email} not found!"))
                return
        
        else:
            # Interactive mode - show all users and let user choose
            all_users = User.objects.all().order_by('id')
            
            if not all_users.exists():
                self.stdout.write(self.style.ERROR("❌ No users found in database!"))
                return
            
            self.stdout.write(self.style.WARNING("\n📋 Available Users:"))
            self.stdout.write(self.style.WARNING("=" * 70))
            
            for idx, user in enumerate(all_users, 1):
                user_type = "🔐 Superuser" if user.is_superuser else "👤 Regular User"
                email_verified = "✅" if user.is_email_verified else "❌"
                
                self.stdout.write(
                    f"{idx}. {user_type} | Email: {user.email} | "
                    f"Verified: {email_verified} | ID: {user.id}"
                )
            
            self.stdout.write(self.style.WARNING("=" * 70))
            self.stdout.write(
                self.style.WARNING(
                    "\n💡 Usage:\n"
                    "   • python manage.py seed_expenses --email=user@example.com\n"
                    "   • python manage.py seed_expenses --all\n"
                    "   • python manage.py seed_expenses --all --clean\n"
                )
            )
            return

        # ═══════════════════════════════════════════════
        # STEP 2: SEED DATA FOR EACH USER
        # ═══════════════════════════════════════════════
        
        for user in users:
            self.stdout.write(
                self.style.SUCCESS(f"\n{'='*70}")
            )
            self.stdout.write(
                self.style.SUCCESS(f"👤 Processing User: {user.email} (ID: {user.id})")
            )
            self.stdout.write(
                self.style.SUCCESS(f"{'='*70}\n")
            )
            
            # Clean existing data if requested
            if clean:
                self._clean_user_data(user)
            
            # Seed the data
            self._seed_user_data(user)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'='*70}\n"
                f"🎉 SEEDING COMPLETED SUCCESSFULLY!\n"
                f"{'='*70}"
            )
        )

    def _clean_user_data(self, user):
        """Delete existing data for user"""
        self.stdout.write(self.style.WARNING(f"🧹 Cleaning existing data for {user.email}..."))
        
        expense_count = Expense.objects.filter(user=user).count()
        budget_count = Budget.objects.filter(user=user).count()
        category_count = BudgetCategory.objects.filter(user=user).count()
        
        Expense.objects.filter(user=user).delete()
        Budget.objects.filter(user=user).delete()
        BudgetCategory.objects.filter(user=user).delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"   ✅ Deleted: {expense_count} expenses, "
                f"{budget_count} budgets, {category_count} categories\n"
            )
        )

    def _seed_user_data(self, user):
        """Seed data for a specific user"""
        
        # Budget configuration
        budget_config = {
            'Food & Groceries': Decimal('25'),
            'Transportation': Decimal('15'),
            'Utilities': Decimal('12'),
            'Entertainment': Decimal('10'),
            'Shopping': Decimal('12'),
            'Health & Fitness': Decimal('8'),
            'Dining & Restaurants': Decimal('10'),
            'Insurance': Decimal('5'),
            'Subscriptions': Decimal('2'),
            'Miscellaneous': Decimal('1'),
        }

        category_objs = []
        total_budget = Decimal('15000')
        today = timezone.now().date()

        # ═══════════════════════════════════════════════
        # CREATE BUDGET CATEGORIES
        # ═══════════════════════════════════════════════
        
        self.stdout.write(self.style.WARNING("📋 Creating budget categories..."))
        
        for category_name, percentage in budget_config.items():
            cat, created = BudgetCategory.objects.get_or_create(
                user=user,
                name=category_name
            )
            category_objs.append(cat)
            
            status = "✅ Created" if created else "♻️ Already exists"
            self.stdout.write(f"   {status} - {category_name} ({percentage}%)")

        # ═══════════════════════════════════════════════
        # CREATE MONTHLY BUDGETS
        # ═══════════════════════════════════════════════
        
        self.stdout.write(
            self.style.WARNING(
                f"\n💰 Creating monthly budgets (9 months: 6 past + current + 3 future)..."
            )
        )
        
        for month_offset in range(-6, 4):
            budget_month = (today + relativedelta(months=month_offset)).replace(day=1)
            
            for category_name, percentage in budget_config.items():
                cat = BudgetCategory.objects.get(user=user, name=category_name)
                allocated_amount = (total_budget * percentage / Decimal('100')).quantize(Decimal('0.01'))
                
                budget, budget_created = Budget.objects.get_or_create(
                    user=user,
                    category=cat,
                    month=budget_month,
                    defaults={'amount': allocated_amount}
                )
                
                if not budget_created:
                    # Update amount if budget already exists
                    budget.amount = allocated_amount
                    budget.save()

        budgets_created = Budget.objects.filter(user=user).count()
        self.stdout.write(
            self.style.SUCCESS(f"   ✅ Total budgets: {budgets_created}")
        )

        # ═══════════════════════════════════════════════
        # CREATE EXPENSES (WITH DUPLICATE CHECK)
        # ═══════════════════════════════════════════════
        
        self.stdout.write(self.style.WARNING("\n📊 Seeding expenses for last 30 days..."))
        
        # Check if expenses already exist
        existing_expenses = Expense.objects.filter(
            user=user,
            date__gte=today - timedelta(days=30)
        ).count()
        
        if existing_expenses > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"   ⚠️ Found {existing_expenses} existing expenses in last 30 days."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    f"   💡 Use --clean flag to delete and recreate: "
                    f"python manage.py seed_expenses --email={user.email} --clean"
                )
            )
            return
        
        expenses_created = 0
        
        for i in range(30):
            expense_date = today - timedelta(days=i)
            category_idx = i % len(category_objs)
            category = category_objs[category_idx]
            amount = Decimal(random.randint(50, 500))
            
            Expense.objects.create(
                user=user,
                category=category,
                amount=amount,
                notes=f"Sample expense - {category.name}",
                date=expense_date
            )
            
            expenses_created += 1

        # ═══════════════════════════════════════════════
        # SUMMARY
        # ═══════════════════════════════════════════════
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ SEEDING SUMMARY for {user.email}:\n"
                f"   • Budget Categories: {len(category_objs)}\n"
                f"   • Monthly Budgets: {budgets_created}\n"
                f"   • Expenses Created: {expenses_created}\n"
                f"   • Total Monthly Budget: ₹{total_budget}\n"
                f"   • Date Range: Last 30 days\n"
            )
        )