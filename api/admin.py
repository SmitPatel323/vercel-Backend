from django.contrib import admin
from .models import User, Product, Vehicle, DeliveryAgent, Shipment

admin.site.register(User)
admin.site.register(Product)
admin.site.register(Vehicle)
admin.site.register(DeliveryAgent)
admin.site.register(Shipment)
