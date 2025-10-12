from django.shortcuts import render
from django.http import JsonResponse
from .models import DataCategory, DataPlan
from .api_client import send_data_request

def buy_data(request):
    if request.method == "POST":
        category_id = request.POST.get("category")
        plan_id = request.POST.get("plan")
        phone = request.POST.get("phone")

        plan = DataPlan.objects.get(id=plan_id)
        category = plan.category

        result = send_data_request(category.network, category.name, phone, plan.size)

        return JsonResponse(result)

    categories = DataCategory.objects.all()
    return render(request, "core/buy_data.html", {"categories": categories})
