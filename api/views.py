import random
import requests
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models import Avg, Sum
from django.db.models.functions import TruncMonth
from datetime import date
from collections import defaultdict
import calendar as cal
from rest_framework import viewsets, status, generics, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User, Product, Vehicle, Shipment, DeliveryAgent
from .serializers import (
    UserSerializer, ProductSerializer, VehicleSerializer,
    ShipmentSerializer, DeliveryAgentSerializer
)
from . import utils

# --- Helper Function to get route from Google Maps ---
def get_google_maps_route(origin_address, destination_address):
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = { "origin": origin_address, "destination": destination_address, "key": settings.GOOGLE_MAPS_API_KEY }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Maps API: {e}")
        return None

# --- View for getting directions in the modal ---
class GetDirectionsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        start_address = request.data.get('start_address')
        end_address = request.data.get('end_address')
        if not start_address or not end_address:
            return Response({'error': 'Start and end addresses are required.'}, status=status.HTTP_400_BAD_REQUEST)
        google_response = get_google_maps_route(start_address, end_address)
        if not google_response or google_response['status'] != 'OK':
            error_message = google_response.get('error_message', 'Could not calculate route.')
            status_message = f"Google Maps Error: {google_response['status']}. {error_message}"
            return Response({'error': status_message}, status=status.HTTP_400_BAD_REQUEST)
        legs = google_response['routes'][0]['legs'][0]
        return Response({'distance': legs['distance']['text'], 'duration': legs['duration']['text']}, status=status.HTTP_200_OK)

# --- Authentication Views ---
class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        available_avatars = ['IMAGES/img1.png', 'IMAGES/img2.png', 'IMAGES/img3.png', 'IMAGES/img4.png']
        used_avatars = set(User.objects.exclude(avatar__isnull=True).values_list('avatar', flat=True))
        chosen_avatar = None
        for avatar_path in available_avatars:
            if avatar_path not in used_avatars:
                chosen_avatar = avatar_path
                break
        if not chosen_avatar:
            chosen_avatar = random.choice(available_avatars)
        user = serializer.save()
        user.avatar = chosen_avatar
        user.save()

class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    def get_object(self): return self.request.user

# --- Read-Only Data Views ---
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class VehicleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    
    def list(self, request, *args, **kwargs):
        vehicles_queryset = self.get_queryset()
        vehicles_serializer = self.get_serializer(vehicles_queryset, many=True)
        
        active_shipments_queryset = Shipment.objects.filter(
            status__in=['In Transit', 'Out for Delivery']
        )
        active_shipments_serializer = ShipmentSerializer(active_shipments_queryset, many=True)
        
        data = {
            'vehicles': vehicles_serializer.data,
            'active_shipments': active_shipments_serializer.data
        }
        return Response(data)


# --- Main Shipment Logic ---
class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer
    def get_queryset(self):
        return Shipment.objects.filter(client=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        product = serializer.validated_data.get('product')
        quantity = serializer.validated_data.get('quantity')
        if product.stock < quantity:
            raise serializers.ValidationError(f"Out of stock. Only {product.stock} units available for {product.name}.")
        
        available_agents = list(DeliveryAgent.objects.filter(is_available=True))
        available_vehicles = list(Vehicle.objects.filter(is_available=True))
        if not available_agents or not available_vehicles:
            raise serializers.ValidationError("No available delivery agents or vehicles at the moment.")
        
        agent = random.choice(available_agents)
        vehicle = random.choice(available_vehicles)
        start_address = serializer.validated_data.get('start_address')
        end_address = serializer.validated_data.get('end_address')
        
        google_response = get_google_maps_route(start_address, end_address)
        if not google_response or google_response['status'] != 'OK':
            error_message = google_response.get('error_message', 'Could not calculate route.')
            status_message = f"Google Maps Error: {google_response['status']}. {error_message}"
            raise serializers.ValidationError(status_message)
        
        route = google_response['routes'][0]
        legs = route['legs'][0]
        distance_km = legs['distance']['value'] / 1000.0
        predicted_duration_hours = utils.predict_delivery_time(distance_km)
        predicted_duration_text = f"{predicted_duration_hours:.1f} hours"
        
        
        
        print(f"DEBUG: Full address received: '{end_address}'")
        
        address_parts = [part.strip() for part in end_address.split(',')]
        if len(address_parts) >= 2:
            destination_city = address_parts[-2]
        else:
            destination_city = address_parts[0]

        print(f"DEBUG: Parsed city for weather: '{destination_city}'")
        weather_forecast = utils.get_weather_forecast(destination_city)
        print(f"DEBUG: Fetched weather result: '{weather_forecast}'")
        
        shipment = serializer.save(
            client=self.request.user, agent=agent, vehicle=vehicle, status='In Transit',
            start_location_lat=legs['start_location']['lat'],
            start_location_lng=legs['start_location']['lng'],
            end_location_lat=legs['end_location']['lat'],
            end_location_lng=legs['end_location']['lng'],
            route_polyline=route['overview_polyline']['points'],
            distance_km=distance_km,
            predicted_duration=predicted_duration_text,
            weather_forecast=weather_forecast,
            current_lat=legs['start_location']['lat'], 
            current_lng=legs['start_location']['lng']
        )
        
        agent.is_available = False
        vehicle.is_available = False
        agent.save()
        vehicle.save()
        
# --- Analytics View ---
class DashboardAnalyticsView(APIView):
    def get(self, request):
        user = request.user
        total_shipments = Shipment.objects.filter(client=user).count()
        in_transit_count = Shipment.objects.filter(client=user, status='In Transit').count()
        delivered_count = Shipment.objects.filter(client=user, status='Delivered').count()
        low_stock_products = Product.objects.filter(stock__gt=0, stock__lt=models.F('low_stock_threshold')).count()
        out_of_stock_products = Product.objects.filter(stock=0).count()
        total_alerts = low_stock_products + out_of_stock_products
        
        user_shipments = Shipment.objects.filter(client=user)
        average_distance_agg = user_shipments.aggregate(Avg('distance_km'))
        average_distance = average_distance_agg['distance_km__avg'] or 75
        predicted_time_hours = utils.predict_delivery_time(average_distance)
        
        all_vehicles = Vehicle.objects.filter(purchase_date__isnull=False)
        total_age_days = 0
        for vehicle in all_vehicles:
            age_in_days = (date.today() - vehicle.purchase_date).days
            total_age_days += max(0, age_in_days)
        average_age_years = (total_age_days / 365.25) / all_vehicles.count() if all_vehicles.count() > 0 else 2
        average_mileage_agg = all_vehicles.aggregate(Avg('total_km_driven'))
        average_mileage = average_mileage_agg['total_km_driven__avg'] or 50000
        predicted_maint_cost = utils.predict_maintenance_cost(average_age_years, average_mileage)
        if predicted_maint_cost < 50:
            predicted_maint_cost = 50.0
        
        delivered_shipments = Shipment.objects.filter(client=request.user, status='Delivered')
        monthly_totals = delivered_shipments.annotate(month=TruncMonth('created_at')).values('month').annotate(total_quantity=Sum('quantity')).values('month', 'total_quantity')
        
        product_details_by_month = defaultdict(list)
        for shipment in delivered_shipments:
            month_key = shipment.created_at.month
            product_details_by_month[month_key].append({
                'name': shipment.product.name,
                'quantity': shipment.quantity
            })

        monthly_volume_data = []
        month_map = {item['month'].month: item['total_quantity'] for item in monthly_totals if item['month']}
        for i in range(1, 13):
            month_name = cal.month_abbr[i]
            total_volume = month_map.get(i, 0)
            products = product_details_by_month.get(i, [])
            monthly_volume_data.append({
                "month": month_name,
                "totalVolume": total_volume,
                "products": products
            })
        
        on_time_percentage = random.randint(85, 98)
        data = {
            'stats': { 'totalShipments': total_shipments, 'inTransit': in_transit_count, 'delivered': delivered_count, 'lowStockAlerts': total_alerts },
            'charts': {
                'monthlyVolume': monthly_volume_data,
                'deliveryPerformance': { 'labels': ['On-Time', 'Delayed'], 'data': [on_time_percentage, 100 - on_time_percentage] }
            },
            'predictions': { 'deliveryTime': f"{predicted_time_hours:.1f} hours", 'maintenanceCost': f"₹{predicted_maint_cost:.2f}" }
        }
        return Response(data, status=status.HTTP_200_OK)


class MarkAsDeliveredView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            shipment = Shipment.objects.get(pk=pk, client=request.user)
        except Shipment.DoesNotExist:
            return Response({'error': 'Shipment not found.'}, status=status.HTTP_404_NOT_FOUND)

        if shipment.status != 'Delivered':
            product = shipment.product
            if product.stock >= shipment.quantity:
                product.stock -= shipment.quantity
                product.save()
            else:
                print(f"Warning: Stock for {product.name} was insufficient at time of delivery.")

            shipment.status = 'Delivered'
            shipment.delivered_at = timezone.now()
            shipment.save()

            if shipment.agent:
                shipment.agent.is_available = True
                shipment.agent.save()

            if shipment.vehicle:
                if shipment.distance_km:
                    shipment.vehicle.total_km_driven += shipment.distance_km
                shipment.vehicle.is_available = True
                shipment.vehicle.save()
            
            return Response({'status': 'Shipment marked as delivered'}, status=status.HTTP_200_OK)
        
        
        return Response({'status': 'Shipment was already delivered'}, status=status.HTTP_200_OK)

# --- View to Update Intermediate Statuses ---
class UpdateStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        try:
            shipment = Shipment.objects.get(pk=pk, client=request.user)
        except Shipment.DoesNotExist:
            return Response({'error': 'Shipment not found.'}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get('status')
        valid_statuses = [choice[0] for choice in Shipment.STATUS_CHOICES]
        if new_status in valid_statuses:
            shipment.status = new_status
            shipment.save()
            return Response({'status': f'Shipment status updated to {new_status}'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid status provided'}, status=status.HTTP_400_BAD_REQUEST)

# --- View to Update Live Location ---
class UpdateLocationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            shipment = Shipment.objects.get(pk=pk, client=request.user)
        except Shipment.DoesNotExist:
            return Response({'error': 'Shipment not found.'}, status=status.HTTP_404_NOT_FOUND)
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        if lat is not None and lng is not None:
            shipment.current_lat = lat
            shipment.current_lng = lng
            shipment.save()
            return Response({'status': 'Location updated'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid coordinates'}, status=status.HTTP_400_BAD_REQUEST)
