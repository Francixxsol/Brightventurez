from .models import DataCategory, DataPlan

def seed_vtu_plans():
    data = {
        # ---------------- MTN SME ----------------
        "MTN SME DATA": [
            {"size": "500MB", "duration": "7 Days", "provider_price": 430, "selling_price": 480},
            {"size": "500MB (SME LITE)", "duration": "30 Days", "provider_price": 450, "selling_price": 499},
            {"size": "1GB", "duration": "7-30 Days", "provider_price": 650, "selling_price": 720},
            {"size": "1GB (SME LITE)", "duration": "30 Days", "provider_price": 650, "selling_price": 730},
            {"size": "2GB", "duration": "7-30 Days", "provider_price": 1140, "selling_price": 1240},
            {"size": "2GB (SME LITE)", "duration": "30 Days", "provider_price": 1050, "selling_price": 1170},
            {"size": "3GB", "duration": "30 Days", "provider_price": 1660, "selling_price": 1860},
            {"size": "3GB (SME LITE)", "duration": "30 Days", "provider_price": 1650, "selling_price": 1800},
            {"size": "5GB", "duration": "30 Days", "provider_price": 2600, "selling_price": 2700},
            {"size": "5GB (SME LITE)", "duration": "30 Days", "provider_price": 2500, "selling_price": 2650},
            {"size": "10GB", "duration": "30 Days", "provider_price": 5700, "selling_price": 5850},
        ],

        # ---------------- MTN AWUF ----------------
        "MTN AWUF DATA": [
            {"size": "110MB", "duration": "1 Day", "provider_price": 99.2, "selling_price": 109},
            {"size": "230MB", "duration": "1 Day", "provider_price": 198.6, "selling_price": 200},
            {"size": "500MB", "duration": "1 Day", "provider_price": 349.5, "selling_price": 400},
            {"size": "500MB", "duration": "7 Days", "provider_price": 495, "selling_price": 500},
            {"size": "750MB", "duration": "3 Days", "provider_price": 451.5, "selling_price": 550},
            {"size": "1GB", "duration": "1 Day", "provider_price": 505, "selling_price": 599},
            {"size": "1GB", "duration": "7 Days", "provider_price": 796, "selling_price": 810},
            {"size": "1.2GB (All Social)", "duration": "30 Days", "provider_price": 460.5, "selling_price": 570},
            {"size": "1.2GB", "duration": "7 Days", "provider_price": 751.5, "selling_price": 800},
            {"size": "1.5GB", "duration": "2 Days", "provider_price": 612, "selling_price": 714},
            {"size": "1.5GB", "duration": "7 Days", "provider_price": 1000, "selling_price": 1100},
            {"size": "1.8GB (ThryveData)", "duration": "30 Days", "provider_price": 1491, "selling_price": 1600},
            {"size": "2GB", "duration": "2 Days", "provider_price": 767.5, "selling_price": 869},
            {"size": "2.5GB", "duration": "2 Days", "provider_price": 923, "selling_price": 1000},
            {"size": "3.2GB", "duration": "2 Days", "provider_price": 1034, "selling_price": 1140},
            {"size": "6GB", "duration": "7 Days", "provider_price": 2545, "selling_price": 2700},
            {"size": "6.75GB (XTRA-SPECIAL)", "duration": "30 Days", "provider_price": 3045, "selling_price": 3150},
            {"size": "11GB", "duration": "7 Days", "provider_price": 3615, "selling_price": 3720},
            {"size": "14.5GB (XTRA-SPECIAL)", "duration": "30 Days", "provider_price": 5140, "selling_price": 5300},
            {"size": "20GB", "duration": "7 Days", "provider_price": 5150, "selling_price": 5400},
        ],

        # ---------------- GLO SME ----------------
        "GLO SME DATA": [
            {"size": "500MB", "duration": "30 Days", "provider_price": 217.5, "selling_price": 320},
            {"size": "1GB", "duration": "30 Days", "provider_price": 435, "selling_price": 550},
            {"size": "2GB", "duration": "30 Days", "provider_price": 870, "selling_price": 980},
            {"size": "3GB", "duration": "30 Days", "provider_price": 1305, "selling_price": 1399},
            {"size": "5GB", "duration": "30 Days", "provider_price": 2175, "selling_price": 2300},
            {"size": "10GB", "duration": "30 Days", "provider_price": 4350, "selling_price": 4600},
        ],

        # ---------------- GLO AWUF ----------------
        "GLO AWUF DATA": [
            {"size": "750MB", "duration": "1 Day", "provider_price": 186, "selling_price": 270},
            {"size": "1.5GB", "duration": "1 Day", "provider_price": 279, "selling_price": 390},
            {"size": "2.5GB", "duration": "2 Days", "provider_price": 465, "selling_price": 580},
            {"size": "10GB", "duration": "7 Days", "provider_price": 1860, "selling_price": 2200},
        ],

        # ---------------- GLO GIFTING ----------------
        "GLO GIFTING DATA": [
            {"size": "2.9GB", "duration": "30 Days", "provider_price": 920.3, "selling_price": 1170},
            {"size": "5GB", "duration": "30 Days", "provider_price": 1385, "selling_price": 1500},
            {"size": "6.2GB", "duration": "30 Days", "provider_price": 1843.4, "selling_price": 2000},
            {"size": "7.5GB", "duration": "30 Days", "provider_price": 2302.5, "selling_price": 2450},
            {"size": "11GB", "duration": "30 Days", "provider_price": 2777, "selling_price": 2900},
            {"size": "14GB", "duration": "30 Days", "provider_price": 3698, "selling_price": 3800},
            {"size": "18GB", "duration": "30 Days", "provider_price": 4626, "selling_price": 4800},
            {"size": "29GB", "duration": "30 Days", "provider_price": 7403, "selling_price": 7600},
            {"size": "40GB", "duration": "30 Days", "provider_price": 9280, "selling_price": 9400},
            {"size": "69GB", "duration": "14 Days", "provider_price": 13983, "selling_price": 14000},
            {"size": "119GB", "duration": "30 Days", "provider_price": 17033, "selling_price": 17200},
            {"size": "110GB", "duration": "30 Days", "provider_price": 18770, "selling_price": 18900},
        ],

        # ---------------- AIRTEL AWUF ----------------
        "AIRTEL AWUF DATA": [
            {"size": "150MB", "duration": "1 Day", "provider_price": 70.06, "selling_price": 110},
            {"size": "200MB", "duration": "2 Days", "provider_price": 212.2, "selling_price": 280},
            {"size": "500MB", "duration": "7 Days", "provider_price": 525.5, "selling_price": 600},
            {"size": "1GB", "duration": "1 Day", "provider_price": 410.2, "selling_price": 520},
            {"size": "1GB", "duration": "7 Days", "provider_price": 800.05, "selling_price": 900.09},
            {"size": "1.5GB", "duration": "2 Days", "provider_price": 550.5, "selling_price": 660},
            {"size": "1.5GB", "duration": "7 Days", "provider_price": 1060, "selling_price": 1140},
            {"size": "2GB", "duration": "2 Days", "provider_price": 826.5, "selling_price": 1000},
            {"size": "3GB", "duration": "2 Days", "provider_price": 1091, "selling_price": 1250},
            {"size": "3GB", "duration": "7 Days", "provider_price": 1096.5, "selling_price": 1300},
            {"size": "3.5GB", "duration": "7 Days", "provider_price": 1526, "selling_price": 1700},
            {"size": "5GB", "duration": "2 Days", "provider_price": 1600, "selling_price": 1750},
            {"size": "6GB", "duration": "7 Days", "provider_price": 2644.5, "selling_price": 2800},
            {"size": "7GB", "duration": "7 Days", "provider_price": 2170.5, "selling_price": 2300},
            {"size": "9GB", "duration": "7 Days", "provider_price": 2642.5, "selling_price": 2800},
            {"size": "10GB", "duration": "7 Days", "provider_price": 3200, "selling_price": 3400},
            {"size": "10GB", "duration": "30 Days", "provider_price": 3250.5, "selling_price": 3400},
            {"size": "18GB", "duration": "7 Days", "provider_price": 5270, "selling_price": 5400},
        ],

        # ---------------- AIRTEL SME ----------------
        "AIRTEL SME DATA": [
            {"size": "500MB", "duration": "7 Days", "provider_price": 600, "selling_price": 700},
            {"size": "1GB", "duration": "7 Days", "provider_price": 850, "selling_price": 950},
            {"size": "2GB", "duration": "30 Days", "provider_price": 1700, "selling_price": 1850},
            {"size": "3GB", "duration": "30 Days", "provider_price": 2550, "selling_price": 2700},
            {"size": "3GB (LITE)", "duration": "7 Days", "provider_price": 1100, "selling_price": 1300},
            {"size": "8GB", "duration": "30 Days", "provider_price": 6800, "selling_price": 6900},
            {"size": "10GB", "duration": "30 Days", "provider_price": 8500, "selling_price": 8600},
        ],

        # ---------------- AIRTEL GIFTING ----------------
        "AIRTEL GIFTING DATA": [
            {"size": "500MB", "duration": "7 Days", "provider_price": 481.5, "selling_price": 550},
            {"size": "800MB", "duration": "7 Days", "provider_price": 767, "selling_price": 900},
            {"size": "1.5GB", "duration": "2 Days", "provider_price": 578, "selling_price": 700},
            {"size": "1.5GB", "duration": "7 Days", "provider_price": 962, "selling_price": 1100},
            {"size": "2GB", "duration": "2 Days", "provider_price": 723, "selling_price": 900},
            {"size": "2GB", "duration": "30 Days", "provider_price": 1447, "selling_price": 1550},
            {"size": "3GB", "duration": "2 Days", "provider_price": 964, "selling_price": 1100},
            {"size": "3GB", "duration": "30 Days", "provider_price": 1934, "selling_price": 2050},
            {"size": "3.5GB", "duration": "7 Days", "provider_price": 1450, "selling_price": 1550},
            {"size": "4GB", "duration": "30 Days", "provider_price": 2418, "selling_price": 2600},
            {"size": "5GB", "duration": "2 Days", "provider_price": 1447, "selling_price": 1650},
            {"size": "6GB", "duration": "7 Days", "provider_price": 2411, "selling_price": 2600},
            {"size": "8GB", "duration": "30 Days", "provider_price": 2896, "selling_price": 3000},
            {"size": "10GB", "duration": "7 Days", "provider_price": 2892, "selling_price": 3200},
            {"size": "10GB", "duration": "30 Days", "provider_price": 3852, "selling_price": 4000},
            {"size": "13GB", "duration": "30 Days", "provider_price": 4833, "selling_price": 5200},
            {"size": "18GB", "duration": "7 Days", "provider_price": 4838, "selling_price": 5000},
            {"size": "18GB", "duration": "30 Days", "provider_price": 5804, "selling_price": 6000},
            {"size": "25GB", "duration": "30 Days", "provider_price": 7722, "selling_price": 7900},
            {"size": "35GB", "duration": "30 Days", "provider_price": 9652, "selling_price": 9800},
            {"size": "60GB", "duration": "30 Days", "provider_price": 14431, "selling_price": 14600},
            {"size": "100GB", "duration": "30 Days", "provider_price": 19291, "selling_price": 19400},
            {"size": "160GB", "duration": "30 Days", "provider_price": 28891, "selling_price": 29000},
            {"size": "210GB", "duration": "30 Days", "provider_price": 38491, "selling_price": 38600},
        ],

        # ---------------- 9MOBILE SME ----------------
        "9MOBILE SME DATA": [
            {"size": "500MB", "duration": "Days", "provider_price": 125, "selling_price": 250},
            {"size": "1GB", "duration": "Days", "provider_price": 250, "selling_price": 350},
            {"size": "1.5GB", "duration": "Days", "provider_price": 375, "selling_price": 500},
            {"size": "2GB", "duration": "Days", "provider_price": 500, "selling_price": 650},
            {"size": "3GB", "duration": "Days", "provider_price": 750, "selling_price": 950},
            {"size": "5GB", "duration": "Days", "provider_price": 1250, "selling_price": 1400},
            {"size": "10GB", "duration": "Days", "provider_price": 2500, "selling_price": 2600},
            {"size": "15GB", "duration": "Days", "provider_price": 3750, "selling_price": 3900},
            {"size": "20GB", "duration": "Days", "provider_price": 5000, "selling_price": 5200},
            {"size": "50GB", "duration": "Days", "provider_price": 12500, "selling_price": 12600},
            {"size": "100GB", "duration": "Days", "provider_price": 25000, "selling_price": 25200},
        ],
    }

    for category_name, plans in data.items():
        category, _ = DataCategory.objects.get_or_create(name=category_name, network=category_name.split()[0])
        for p in plans:
            DataPlan.objects.get_or_create(
                category=category,
                size=p["size"],
                defaults={
                    "duration": p["duration"],
                    "provider_price": p["provider_price"],
                    "selling_price": p["selling_price"],
                }
            )
    print("✅ VTU plans seeded successfully!")
