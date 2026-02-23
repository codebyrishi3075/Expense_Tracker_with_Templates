from django.db import models
from django.conf import settings


class BudgetCategory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budget_categories'
    )
    name       = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')
        ordering        = ['name']

    def __str__(self):
        return f"{self.name} ({self.user.email})"


class Budget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    category = models.ForeignKey(
        BudgetCategory,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    month      = models.DateField()          # First day of month e.g. 2026-02-01
    amount     = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'category', 'month')
        ordering        = ['-month']

    def __str__(self):
        return f"{self.user.email} - {self.category.name} - {self.month}"