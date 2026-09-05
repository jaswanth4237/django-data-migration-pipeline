import time
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import LegacyOrder, Order, OrderLine


class Command(BaseCommand):
    help = "Perform memory-efficient, resumable, and idempotent order data migration."

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process per batch.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Flag to simulate migration without making database changes.'
        )
        parser.add_argument(
            '--start-from',
            type=str,
            default=None,
            help='External ID from which to begin migration.'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        start_from = options['start_from']

        queryset = LegacyOrder.objects.filter(migrated=False).order_by('external_id')
        if start_from:
            queryset = queryset.filter(external_id__gte=start_from)

        total_unmigrated = queryset.count()

        if dry_run:
            self.stdout.write(
                f"[Dry Run] Would process {total_unmigrated:,} unmigrated legacy records with batch size {batch_size}."
            )
            return

        if total_unmigrated == 0:
            self.stdout.write("No unmigrated records found. Migration complete.")
            self.stdout.write("Total time: 0.00 seconds")
            self.stdout.write("Throughput: 0.00 records per second")
            return

        self.stdout.write(
            f"Starting migration of {total_unmigrated:,} legacy records (batch size: {batch_size})..."
        )
        start_time = time.perf_counter()

        orders_to_create = []
        lines_info = []
        processed_legacy_ids = []
        total_processed = 0

        for legacy_order in queryset.iterator(chunk_size=batch_size):
            raw_data = legacy_order.raw_data or {}

            customer_email = raw_data.get('customer_email', 'unknown@example.com')
            total = Decimal(str(raw_data.get('total', '0.00')))

            new_order = Order(
                external_id=legacy_order.external_id,
                customer_email=customer_email,
                total=total
            )
            orders_to_create.append(new_order)

            items = raw_data.get('items', [])
            for item in items:
                line_sku = item.get('sku', 'UNKNOWN')
                line_qty = int(item.get('quantity', 1))
                line_price = Decimal(str(item.get('unit_price', '0.00')))

                line_obj = OrderLine(
                    sku=line_sku,
                    quantity=line_qty,
                    unit_price=line_price
                )
                lines_info.append((legacy_order.external_id, line_obj))

            processed_legacy_ids.append(legacy_order.id)

            if len(orders_to_create) >= batch_size:
                self._process_batch(orders_to_create, lines_info, processed_legacy_ids)
                total_processed += len(orders_to_create)
                orders_to_create = []
                lines_info = []
                processed_legacy_ids = []

        if orders_to_create:
            self._process_batch(orders_to_create, lines_info, processed_legacy_ids)
            total_processed += len(orders_to_create)

        elapsed = time.perf_counter() - start_time
        throughput = total_processed / elapsed if elapsed > 0 else 0

        self.stdout.write(
            self.style.SUCCESS(
                f"Migration completed successfully! Processed {total_processed:,} records.\n"
                f"Total time: {elapsed:.2f} seconds\n"
                f"Throughput: {throughput:.2f} records per second"
            )
        )

    def _process_batch(self, orders, lines_info, legacy_ids):
        with transaction.atomic():
            Order.objects.bulk_create(orders, batch_size=len(orders))

            created_orders = Order.objects.filter(
                external_id__in=[o.external_id for o in orders]
            ).in_bulk(field_name='external_id')

            lines_to_create = []
            for ext_id, line_obj in lines_info:
                line_obj.order = created_orders[ext_id]
                lines_to_create.append(line_obj)

            if lines_to_create:
                OrderLine.objects.bulk_create(lines_to_create, batch_size=len(lines_to_create))

            LegacyOrder.objects.filter(id__in=legacy_ids).update(migrated=True)

        self.stdout.write(f"Successfully processed batch of {len(orders)} records.")
