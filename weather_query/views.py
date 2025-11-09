import requests
import pycountry
from django.shortcuts import render, redirect
from django.urls import reverse
from .models import WeatherQuery
from django.core.paginator import Paginator
from django.db.models import F
from django.db.models.functions import Lower
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
from django.core.cache import cache
import csv
import json
import logging
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse



logger = logging.getLogger(__name__)

API_KEY = "f0ed68a6bc30ea933aa09d0aff26804b"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

RATE_LIMIT = 30
RATE_WINDOW = 60

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def check_rate_limit(ip):
    key = f"rate_limit_{ip}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return False
    cache.set(key, count + 1, RATE_WINDOW)
    return True

def weather(request):
    weather_data = None
    error_message = None

    selected_units = request.session.get("units", "metric")

    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        return render(request, "weather_query/limit_exceeded.html", status=429)

    if request.method == "POST":
        city = request.POST.get("city")
        units = request.POST.get("units", selected_units)
        request.session["units"] = units
        now = timezone.now()

        recent_query = WeatherQuery.objects.filter(
            city_name__iexact=city,
            timestamp__gte=now - timedelta(minutes=5)
        ).order_by('-timestamp').first()

        if recent_query:
            WeatherQuery.objects.create(
                city_name=city,
                temperature=recent_query.temperature,
                description=recent_query.description,
                humidity=recent_query.humidity,
                wind_speed=recent_query.wind_speed,
                from_cache=True,
                units = units
            )

            weather_data = {
                "city": recent_query.city_name,
                "temperature": recent_query.temperature,
                "description": recent_query.description,
                "humidity": recent_query.humidity,
                "wind_speed": recent_query.wind_speed,
                "icon": "cached",
                "from_cache": True,
                "units": units
            }

        else:
            params = {
                "q": city,
                "appid": API_KEY,
                "units": units,
                "lang": "ru"
            }

            response = requests.get(BASE_URL, params=params)

            if response.status_code == 200:
                data = response.json()
                WeatherQuery.objects.create(
                    city_name=data["name"],
                    temperature=data["main"]["temp"],
                    description=data["weather"][0]["description"],
                    humidity=data["main"]["humidity"],
                    wind_speed=data["wind"]["speed"],
                    from_cache=False,
                    units=units
                )

                weather_data = {
                    "city": data["name"],
                    "temperature": data["main"]["temp"],
                    "description": data["weather"][0]["description"],
                    "humidity": data["main"]["humidity"],
                    "wind_speed": data["wind"]["speed"],
                    "icon": data["weather"][0]["icon"],
                    "units": units
                }
            else:
                error_message = "Город не найден!"

        request.session["weather_data"] = weather_data
        request.session["error_message"] = error_message
        return redirect(reverse("weather"))

    if "weather_data" in request.session:
        weather_data = request.session.pop("weather_data")
    if "error_message" in request.session:
        error_message = request.session.pop("error_message")

    return render(request, "weather_query/weather.html", {
        "weather_data": weather_data,
        "error_message": error_message,
        "selected_units": selected_units
    })


def weather_history(request):
    posts = WeatherQuery.objects.all().order_by("-timestamp")

    city = request.GET.get('city')
    date_min = request.GET.get('date_min')
    date_max = request.GET.get('date_max')

    if city:
        posts = posts.filter(city_name__icontains=city)
    if date_min:
        posts = posts.filter(timestamp__date__gte=date_min)
    if date_max:
        posts = posts.filter(timestamp__date__lte=date_max)

    cities = (
        WeatherQuery.objects
        .annotate(city_lower=Lower('city_name'))
        .values_list('city_lower', flat=True)
        .distinct()
    )

    cities = sorted(set(c.title() for c in cities))

    paginator = Paginator(posts, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        'posts': page_obj,
        'cities': cities,
        'selected_city': city,
        'date_min': date_min,
        'date_max': date_max,
        'page_obj': page_obj,
    }
    return render(request, "weather_query/weather_history.html", context)


def export_weather_csv(request):
    city_filter = request.GET.get("city")

    queries = WeatherQuery.objects.all().order_by("-timestamp")
    if city_filter:
        queries = queries.filter(city_name__iexact=city_filter)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response['Content-Disposition'] = 'attachment; filename="weather_history.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        "ID",
        "City",
        "Temperature",
        "Description",
        "Humidity",
        "Wind Speed",
        "Timestamp",
        "From Cache",
        "Units"
    ])

    for q in queries:
        writer.writerow([
            q.id,
            q.city_name,
            q.temperature,
            q.description,
            q.humidity,
            q.wind_speed,
            q.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Yes" if q.from_cache else "No",
            q.units
        ])

    return response


def health_check(request):
    status = {"database": False, "external_api": False, "timestamp": timezone.now().isoformat()}
    logger.info(json.dumps({"event": "health_check_started", "timestamp": status["timestamp"]}))


    try:
        db_conn = connections['default']
        db_conn.cursor()
        status["database"] = True
    except OperationalError as e:
        logger.error(json.dumps({"event": "db_connection_failed", "error": str(e)}))


    try:
        response = requests.get(
            f"{BASE_URL}?q=London&appid={API_KEY}",
            timeout=2
        )
        status["external_api"] = response.status_code == 200
    except requests.RequestException as e:
        logger.warning(json.dumps({"event": "external_api_unreachable", "error": str(e)}))

    overall_status = "ok" if all(status.values()) else "degraded"
    logger.info(json.dumps({"event": "health_check_completed", "status": overall_status}))

    return JsonResponse({
        "status": overall_status,
        "details": status
    })