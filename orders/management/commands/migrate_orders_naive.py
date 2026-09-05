import time
import tracemalloc
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from orders.models import LegacyOrder, Order, OrderLine


class Command(BaseCommand):
    help = "Naive implementation of order migration for benchmarking purposes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of records for testing (0 for all).'
        )

    def handle(self, *args, **options):
        limit = options['limit']

        tracemalloc.start()
        start_time = time.perf_counter()
        reset_queries()

        # Naive QuerySet evaluation - loads all matching records into memory
        legacy_orders = LegacyOrder.objects.filter(migrated=False).order_by('external_id')
        if limit > 0:
            legacy_orders = legacy_orders[:limit]

        # Convert to list to simulate naive loading of entire table in memory
        legacy_orders_list = list(legacy_orders)
        total_records = len(legacy_orders_list)

        self.stdout.write(f"[Naive] Processing {total_records} records one-by-one...")

        for legacy_order in legacy_orders_list:
            raw_data = legacy_order.raw_data or {}
            customer_email = raw_data.get('customer_email', 'unknown@example.com')
            total = Decimal(str(raw_data.get('total', '0.00')))

            order = Order.objects.create(
                external_id=legacy_order.external_id,
                customer_email=customer_email,
                total=total
            )

            items = raw_data.get('items', [])
            for item in items:
                OrderLine.objects.create(
                    order=order,
                    sku=item.get('sku', 'UNKNOWN'),
                    quantity=int(item.get('quantity', 1)),
                    unit_price=Decimal(str(item.get('unit_price', '0.00')))
                )

            legacy_order.migrated = True
            legacy_order.save()

        elapsed = time.perf_counter() - start_time
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        num_queries = len(connection.queries)

        self.stdout.write(self.style.SUCCESS(
            f"[Naive] Completed {total_records} records.\n"
            f"Total time: {elapsed:.2f} s\n"
            f"Peak Memory: {peak_mem / 1024 / 1024:.2f} MB\n"
            f"Queries Executed: {num_queries}"
        ))
