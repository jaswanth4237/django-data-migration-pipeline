# Django Data Migration Pipeline

A Django and PostgreSQL demonstration project for migrating legacy order data into normalized order and order-line tables. It includes a memory-efficient migration command, a deliberately naive implementation for comparison, and a large-data seeder for performance testing.

## What it demonstrates

- Streaming legacy records with `QuerySet.iterator()`.
- Batch writes with `bulk_create()` inside atomic transactions.
- Resumable migration using an external ID checkpoint.
- Idempotent progress tracking through `LegacyOrder.migrated`.
- Dry-run support before changing data.
- Benchmarking memory usage, execution time, and database query counts.

## Requirements

- Docker Desktop with Docker Compose, or
- Python 3.12+, PostgreSQL 16+, and the packages in `requirements.txt`.

The Docker workflow is recommended because it provisions PostgreSQL with the expected connection settings.

## Run with Docker Compose

Build and start the application and database:

```bash
docker compose up --build
```

The Django development server is available at `http://localhost:8000`.

The application container runs Django migrations automatically when it starts. The PostgreSQL data is stored in the named `postgres_data` volume.

Stop the services:

```bash
docker compose down
```

Stop the services and remove the database volume:

```bash
docker compose down -v
```

## Seed legacy data

The default command creates 500,000 legacy orders. Use a smaller count while developing:

```bash
docker compose exec app python manage.py seed_legacy_data --count 1000
```

The seeder clears existing legacy, order, and order-line rows before inserting data. Its batch size can be changed independently:

```bash
docker compose exec app python manage.py seed_legacy_data --count 500000 --batch-size 20000
```

## Run the optimized migration

Preview how many records would be processed without changing the database:

```bash
docker compose exec app python manage.py migrate_orders --dry-run
```

Run the migration with the default batch size of 1,000:

```bash
docker compose exec app python manage.py migrate_orders
```

Tune the batch size for a benchmark environment:

```bash
docker compose exec app python manage.py migrate_orders --batch-size 5000
```

Resume from an external ID:

```bash
docker compose exec app python manage.py migrate_orders --start-from legacy-250000
```

Each batch creates `Order` and `OrderLine` rows and then marks the corresponding `LegacyOrder` rows as migrated in one transaction. Re-running the command processes only rows that remain unmigrated.

## Run the naive comparison

The naive command loads all selected legacy rows into memory and writes records one at a time. It is intended for controlled benchmarking, not production migration:

```bash
docker compose exec app python manage.py migrate_orders_naive --limit 1000
```

Use `--limit 0` to process all unmigrated rows. Do not use the unbounded mode on a constrained machine without understanding the memory impact.

## Project layout

```text
config/                         Django project configuration
orders/models.py                LegacyOrder, Order, and OrderLine models
orders/management/commands/     Seeder and migration commands
orders/migrations/              Database schema migrations
benchmark.md                    Benchmark results and analysis
docker-compose.yml              Local PostgreSQL and Django services
Dockerfile                      Application image definition
entrypoint.sh                   Runs migrations before the app starts
```

## Configuration

The application uses these environment variables for PostgreSQL:

| Variable | Default |
| --- | --- |
| `POSTGRES_DB` | `migratedb` |
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | `postgres` |
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `SECRET_KEY` | Development-only fallback |

Change the development defaults before using this project in a shared or production environment. `DEBUG` is enabled in the current settings and should also be disabled outside local development.

## Benchmark results

See [benchmark.md](benchmark.md) for the recorded comparison. The optimized implementation uses streaming reads and bulk writes to keep memory usage bounded and reduce database round trips.

## Development checks

Run Django's system checks inside the application container:

```bash
docker compose exec app python manage.py check
```

Create or apply migrations when model definitions change:

```bash
docker compose exec app python manage.py makemigrations
docker compose exec app python manage.py migrate
```
