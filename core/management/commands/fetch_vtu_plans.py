from django.core.management.base import BaseCommand
from core.models import PriceTable
import requests
import os

# -------------------------------------
# API credentials
# -------------------------------------
DATAHOUSE_API_TOKEN = os.getenv("DATAHOUSE_API_TOKEN", "94ef2cdfce6a4a4fab12a07b409ee5db166da2f2")

# API endpoint
DATAHOUSE_ENDPOINT = "https://www.datahouse.com.ng/api/user/"

class Command(BaseCommand):
    help = "Fetches data from DataHouse API and saves to PriceTable"

    def handle(self, *args, **kwargs):
        self.stdout.write("Fetching DataHouse plans...")

        headers = {
            "Authorization": f"Token {DATAHOUSE_API_TOKEN}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(DATAHOUSE_ENDPOINT, headers=headers, timeout=10)
            self.stdout.write(f"Raw response: {response.text[:500]}")  # print first 500 chars

            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(
                    f"❌ Endpoint returned status {response.status_code}"
                ))
                return

            data = response.json()

            # Example: assuming the API returns a 'data' list
            plans = data.get("data")
            if not plans:
                self.stdout.write(self.style.ERROR("❌ No data found in API response"))
                return

            for plan in plans:
                network = plan.get("network")
                plan_name = plan.get("name") or plan.get("plan_name")
                plan_code = plan.get("code") or plan.get("plan")
                price = float(plan.get("price", 0))
                my_price = price + 50  # profit margin

                obj, created = PriceTable.objects.update_or_create(
                    network=network,
                    plan_name=plan_name,
                    defaults={
                        "vtu_cost": price,
                        "my_price": my_price,
                        "api_code": plan_code,
                        "plan_type": "datahouse"
                    },
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Added {network} - {plan_name}"))
                else:
                    self.stdout.write(f"Updated {network} - {plan_name}")

            self.stdout.write(self.style.SUCCESS("✅ All DataHouse plans synced successfully!"))

        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"❌ Request failed: {str(e)}"))
        except ValueError:
            self.stdout.write(self.style.ERROR("❌ Invalid JSON returned by API"))
