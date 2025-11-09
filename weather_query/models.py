from django.db import models

class WeatherQuery(models.Model):
    UNIT_CHOICES = [
        ("metric", "°C"),
        ("imperial", "°F"),
    ]

    city_name = models.CharField(max_length=100, verbose_name="Название города")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время запроса")
    temperature = models.FloatField(verbose_name="Температура (°C)")
    description = models.CharField(max_length=255, verbose_name="Описание погоды")
    humidity = models.PositiveIntegerField(verbose_name="Влажность (%)", null=True, blank=True)
    wind_speed = models.FloatField(verbose_name="Скорость ветра (м/с)", null=True, blank=True)
    from_cache = models.BooleanField(default=False, verbose_name="Из кэша")
    units = models.CharField(max_length=10, choices=UNIT_CHOICES, default="metric", verbose_name="Единицы измерения")

    def __str__(self):
        symbol = "°C" if self.units == "metric" else "°F"
        return f"{self.city_name} — {self.temperature}°C ({self.description})"

    class Meta:
        verbose_name = "Запрос погоды"
        verbose_name_plural = "Запросы погоды"
        ordering = ['-timestamp']
