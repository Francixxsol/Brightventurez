from django.core.management.base import BaseCommand
from core.models import PriceTable
import json

class Command(BaseCommand):
    help = "Seed the PriceTable with VTU plans"

    def handle(self, *args, **kwargs):
        data_json = """
        [
            {"network": "01", "plan": "1GB (CG_LITE) - 30 Days", "epincode": "36", "price_api": "880", "my_price": "950", "datatype": "cglite"},
            {"network": "01", "plan": "2 GB (CG_LITE) - 30 Days", "epincode": "37", "price_api": "1700", "my_price": "1850", "datatype": "cglite"},
            {"network": "01", "plan": "3 GB (CG_LITE) - 30 Days", "epincode": "41", "price_api": "2550", "my_price": "2680", "datatype": "cglite"},
            {"network": "01", "plan": "5GB (CG_LITE)", "epincode": "42", "price_api": "4250", "my_price": "4370", "datatype": "cglite"},
            {"network": "01", "plan": "10 GB (CG_LITE) - 30 Days", "epincode": "43", "price_api": "8500", "my_price": "8640", "datatype": "cglite"},
            {"network": "01", "plan": "1GB (SME) - 30days", "epincode": "57", "price_api": "550", "my_price": "610", "datatype": "sme"},
            {"network": "01", "plan": "500MB (SME) - 30days", "epincode": "58", "price_api": "420", "my_price": "480", "datatype": "sme"},
            {"network": "01", "plan": "2GB (SME) - 30days", "epincode": "59", "price_api": "1140", "my_price": "1240", "datatype": "sme"},
            {"network": "01", "plan": "3 GB (SME) - 30days", "epincode": "60", "price_api": "1740", "my_price": "1840", "datatype": "sme"},
            {"network": "01", "plan": "5GB (SME) - 30days", "epincode": "61", "price_api": "2350", "my_price": "2470", "datatype": "sme"},
            {"network": "01", "plan": "20GB (SME) - 7 days", "epincode": "62", "price_api": "5700", "my_price": "5800", "datatype": "sme"},
            {"network": "01", "plan": "500MB (GIFTING) - 7days", "epincode": "65", "price_api": "375", "my_price": "480", "datatype": "gifting"},
            {"network": "01", "plan": "1GB (GIFTING) - 30days", "epincode": "66", "price_api": "580", "my_price": "640", "datatype": "gifting"},
            {"network": "01", "plan": "2GB (GIFTING) - 30days", "epincode": "67", "price_api": "980", "my_price": "1080", "datatype": "gifting"},
            {"network": "01", "plan": "3GB (GIFTING) - 30days", "epincode": "68", "price_api": "1500", "my_price": "1600", "datatype": "gifting"},
            {"network": "01", "plan": "5GB (GIFTING) - 30days", "epincode": "69", "price_api": "2550", "my_price": "2650", "datatype": "gifting"},
            {"network": "04", "plan": "500MB (CG) - 30days", "epincode": "86", "price_api": "425", "my_price": "480", "datatype": "gifting"},
            {"network": "02", "plan": "200MB (CG) - 14days", "epincode": "93", "price_api": "95", "my_price": "150", "datatype": "gifting"},
            {"network": "02", "plan": "500MB (CG) - 30days", "epincode": "94", "price_api": "200", "my_price": "280", "datatype": "gifting"},
            {"network": "02", "plan": "1GB (CG) - 30days", "epincode": "95", "price_api": "398", "my_price": "480", "datatype": "gifting"},
            {"network": "02", "plan": "2GB (CG) - 30days", "epincode": "96", "price_api": "796", "my_price": "880", "datatype": "gifting"},
            {"network": "02", "plan": "3GB (CG) - 30days", "epincode": "97", "price_api": "1194", "my_price": "1280", "datatype": "gifting"},
            {"network": "02", "plan": "5GB (CG) - 30days", "epincode": "98", "price_api": "1990", "my_price": "2080", "datatype": "gifting"},
            {"network": "02", "plan": "10GB (CG) - 30days", "epincode": "99", "price_api": "3980", "my_price": "4100", "datatype": "gifting"}
        ]
        """

        plans = json.loads(data_json)

        # Delete old records
        PriceTable.objects.all().delete()

        # Insert new records
        for p in plans:
            PriceTable.objects.create(
                network=p.get("network"),
                plan_name=p.get("plan"),
                network_id=int(p.get("epincode")),
                plan_code=int(p.get("epincode")),
                vtu_cost=float(p.get("price_api")),
                my_price=float(p.get("my_price")),
                plan_type=p.get("datatype").upper()
            )

        self.stdout.write(self.style.SUCCESS("✅ PriceTable replaced successfully!"))
