from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(unique=True)
    avatar = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    low_stock_threshold = models.PositiveIntegerField(default=10)

    def __str__(self):
        return self.name

class Vehicle(models.Model):
    name = models.CharField(max_length=255)
    license_plate = models.CharField(max_length=20, unique=True)
    is_available = models.BooleanField(default=True)
    purchase_date = models.DateField(null=True, blank=True)
    total_km_driven = models.FloatField(default=0)

    def __str__(self):
        return f"{self.name} ({self.license_plate})"

class DeliveryAgent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="delivery_agent_profile")
    phone_number = models.CharField(max_length=15)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username

class Shipment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Transit', 'In Transit'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shipments")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    agent = models.ForeignKey(DeliveryAgent, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    start_address = models.CharField(max_length=255)
    end_address = models.CharField(max_length=255)
    
    start_location_lat = models.FloatField(null=True, blank=True)
    start_location_lng = models.FloatField(null=True, blank=True)
    end_location_lat = models.FloatField(null=True, blank=True)
    end_location_lng = models.FloatField(null=True, blank=True)
    
    # Stores the encoded polyline from Google Maps for drawing the route
    route_polyline = models.TextField(blank=True, null=True)
    distance_km = models.FloatField(null=True, blank=True)
    predicted_duration = models.CharField(max_length=50, blank=True, null=True)

    weather_forecast = models.CharField(max_length=100, blank=True, null=True)
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"Shipment #{self.id} for {self.client.username}"
