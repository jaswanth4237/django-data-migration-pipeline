import time
from django.core.management.base import BaseCommand
from orders.models import LegacyOrder, Order, OrderLine


class Command(BaseCommand):
    help = "Seed the database with 500,000 legacy order records."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=500000,
            help='Number of legacy records to seed (default: 500000).'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=20000,
            help='Batch size for bulk_create (default: 20000).'
        )

    def handle(self, *args, **options):
        count = options['count']
        batch_size = options['batch_size']

        self.stdout.write("Clearing existing database tables...")
        OrderLine.objects.all().delete()
        Order.objects.all().delete()
        LegacyOrder.objects.all().delete()

        self.stdout.write(f"Seeding {count:,} legacy records...")
        start_time = time.perf_counter()

        batch = []
        total_created = 0

        for i in range(1, count + 1):
            ext_id = f"legacy-{i}"
            raw_data = {
                "customer_email": f"customer_{i}@example.com",
                "total": "199.98",
                "items": [
                    {"sku": "SKU-A1", "quantity": 2, "unit_price": "49.99"},
                    {"sku": "SKU-B2", "quantity": 1, "unit_price": "99.99"}
                ]
            }
            batch.append(LegacyOrder(
                external_id=ext_id,
                raw_data=raw_data,
                migrated=False
            ))

            if len(batch) >= batch_size:
                LegacyOrder.objects.bulk_create(batch, batch_size=5000)
                total_created += len(batch)
                self.stdout.write(f"Inserted {total_created:,}/{count:,} records...")
                batch = []

        if batch:
            LegacyOrder.objects.bulk_create(batch, batch_size=5000)
            total_created += len(batch)

        elapsed = time.perf_counter() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {total_created:,} legacy order records in {elapsed:.2f} seconds."
            )
        )
