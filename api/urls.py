from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    SignupView, ProfileView, ProductViewSet, VehicleViewSet,
    ShipmentViewSet, DashboardAnalyticsView, MarkAsDeliveredView,
    GetDirectionsView ,UpdateLocationView,UpdateStatusView 
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'shipments', ShipmentViewSet, basename='shipment')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
    path('shipments/<int:pk>/deliver/', MarkAsDeliveredView.as_view(), name='shipment-deliver'),
    path('get-directions/', GetDirectionsView.as_view(), name='get-directions'),

    path('shipments/<int:pk>/update_location/', UpdateLocationView.as_view(), name='shipment-update-location'),
    path('shipments/<int:pk>/update_status/', UpdateStatusView.as_view(), name='shipment-update-status'),

    # Auth
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileView.as_view(), name='user-profile'),
]
