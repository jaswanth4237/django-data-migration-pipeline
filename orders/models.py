from django.db import models


class LegacyOrder(models.Model):
    external_id = models.CharField(max_length=100, unique=True, db_index=True)
    raw_data = models.JSONField()
    migrated = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders_legacyorder'
        indexes = [
            models.Index(fields=['migrated', 'external_id']),
        ]

    def __str__(self):
        return self.external_id


class Order(models.Model):
    external_id = models.CharField(max_length=100, unique=True, db_index=True)
    customer_email = models.EmailField(max_length=254)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders_order'

    def __str__(self):
        return f"Order {self.external_id} ({self.customer_email})"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='lines')
    sku = models.CharField(max_length=100)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'orders_orderline'

    def __str__(self):
        return f"{self.sku} x {self.quantity}"
