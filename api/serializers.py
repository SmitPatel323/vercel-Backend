from rest_framework import serializers
from .models import User, Product, Vehicle, DeliveryAgent, Shipment


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'avatar', 'avatar_url']
        extra_kwargs = {
            'password': {'write_only': True},
            'avatar': {'read_only': True} 
        }

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar:
            if obj.avatar.startswith('http'):
                return obj.avatar
            if request:
                return request.build_absolute_uri(f'/media/{obj.avatar}')
        return None 

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user

class ProductSerializer(serializers.ModelSerializer):
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'stock', 'description', 'low_stock_threshold', 'stock_status']
        
    def get_stock_status(self, obj):
        """
        Returns a string representing the stock status based on the threshold.
        """
        if obj.stock == 0:
            return "Out of Stock"
        if obj.stock < obj.low_stock_threshold:
            return "Low Stock"
        return "In Stock"

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class DeliveryAgentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = DeliveryAgent
        fields = '__all__'

class ShipmentSerializer(serializers.ModelSerializer):
    client = UserSerializer(read_only=True)
    agent = DeliveryAgentSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = Shipment
        fields = [
            'id', 'client', 'product', 'product_id', 'quantity', 'agent',
            'vehicle', 'status', 'created_at', 'delivered_at', 'start_address', 
            'end_address', 'start_location_lat', 'start_location_lng', 
            'end_location_lat', 'end_location_lng', 'route_polyline',
            'distance_km', 'predicted_duration','weather_forecast','current_lat', 'current_lng'

        ]
        read_only_fields = ('client', 'agent', 'vehicle', 'status', 'created_at', 'delivered_at', 'start_location_lat', 'start_location_lng', 'end_location_lat', 'end_location_lng', 'route_polyline',
                            'distance_km', 'predicted_duration',
                            'weather_forecast','current_lat', 'current_lng'
            )

