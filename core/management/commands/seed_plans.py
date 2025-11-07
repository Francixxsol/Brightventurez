from django.core.management.base import BaseCommand
from core.models import PriceTable

class Command(BaseCommand):
    help = "Seed the database with network data plans and prices"

    def handle(self, *args, **options):
        plans = [
            # === MTN SME ===
            ("MTN", "SME", "Data Share 10GB", 5700, 5850),
            ("MTN", "SME", "SME 500MB", 430, 480),
            ("MTN", "SME", "SME LITE 500MB", 450, 499),
            ("MTN", "SME", "SME 1GB", 650, 720),
            ("MTN", "SME", "SME LITE 1GB", 650, 730),
            ("MTN", "SME", "SME 2GB", 1140, 1240),
            ("MTN", "SME", "SME LITE 2GB", 1050, 1170),
            ("MTN", "SME", "SME 3GB", 1660, 1860),
            ("MTN", "SME", "SME LITE 3GB", 1650, 1800),
            ("MTN", "SME", "SME 5GB", 2600, 2700),

            # === GLO SME ===
            ("GLO", "SME", "GLO 500MB", 217.5, 320),
            ("GLO", "SME", "GLO 1GB", 435, 550),
            ("GLO", "SME", "GLO 2GB", 870, 980),
            ("GLO", "SME", "GLO 3GB", 1305, 1399),
            ("GLO", "SME", "GLO 5GB", 2175, 2300),

            # === AIRTEL SME ===
            ("AIRTEL", "SME", "Airtel 500MB", 600, 700),
            ("AIRTEL", "SME", "Airtel 1GB", 850, 950),
            ("AIRTEL", "SME", "Airtel 2GB", 1700, 1850),
            ("AIRTEL", "SME", "Airtel 3GB", 2550, 2700),
            ("AIRTEL", "SME", "Airtel 10GB", 8500, 8600),

            # === 9MOBILE SME ===
            ("9MOBILE", "SME", "9mobile 500MB", 125, 250),
            ("9MOBILE", "SME", "9mobile 1GB", 250, 350),
            ("9MOBILE", "SME", "9mobile 2GB", 500, 650),
            ("9MOBILE", "SME", "9mobile 5GB", 1250, 1400),
        ]

        created_count = 0
        for net, dtype, name, vtu_cost, my_price in plans:
            obj, created = PriceTable.objects.get_or_create(
                network=net,
                data_type=dtype,
                plan_name=name,
                defaults={"vtu_cost": vtu_cost, "my_price": my_price},
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {created_count} plans added successfully!"))
