import pytest
from unittest.mock import patch
from django.utils import timezone
from weather_query.models import WeatherQuery
from django.urls import reverse
from datetime import timedelta

@pytest.mark.django_db
@patch("weather_query.views.requests.get")
def test_cache_reuse(mock_get, client):
    mock_response = {
        "main": {"temp": 10, "humidity": 50},
        "weather": [{"description": "ясно", "icon": "01d"}],
        "wind": {"speed": 2},
        "name": "Минск",
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = mock_response


    client.post(reverse("weather"), {"city": "Минск"})
    assert WeatherQuery.objects.count() == 1
    first_query = WeatherQuery.objects.first()
    first_query.timestamp = timezone.now()
    first_query.save()

    client.post(reverse("weather"), {"city": "Минск"})
    assert WeatherQuery.objects.count() == 2

    assert WeatherQuery.objects.filter(from_cache=True).exists()
    assert mock_get.call_count == 1


@pytest.mark.django_db
def test_rate_limit_enforced(client, settings):
    settings.RATE_LIMIT_PER_MIN = 30

    url = reverse("weather")
    for i in range(30):
        client.post(url, {"city": f"Минск{i}"})

    response = client.post(url, {"city": "Минск"})
    assert response.status_code == 429


@pytest.mark.django_db
def test_pagination_and_filter(client):
    WeatherQuery.objects.bulk_create([
        WeatherQuery(city_name=f"City{i}", temperature=10, description="ok")
        for i in range(25)
    ])

    url = reverse("history")
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.context["page_obj"].object_list) == 10

    response2 = client.get(url + "?page=2")
    assert len(response2.context["page_obj"].object_list) == 10

    response_filtered = client.get(url + "?city=City1")
    for obj in response_filtered.context["page_obj"].object_list:
        assert "City1" in obj.city_name