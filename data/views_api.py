from rest_framework.views import APIView
from rest_framework.response import Response
from .models import DataPlan

class DataPlanByCategory(APIView):
    def get(self, request):
        cat_id = request.GET.get("category")
        plans = DataPlan.objects.filter(category_id=cat_id).values("id", "size", "selling_price")
        return Response({"plans": list(plans)})
