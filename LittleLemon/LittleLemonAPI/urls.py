from django.urls import path
from . import views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('menu-items/', views.MenuItemsView.as_view()),
    path('menu-items/<int:pk>', views.SingleMenuItem.as_view()),
    path('cart/menu-items/', views.CartView.as_view()),
    path('groups/manager/users/', views.manager_view),
    path('groups/manager/users/<user_id>/', views.managers),
    path('groups/delivery-crew/users/', views.deliverycrew_view),
    path('groups/delivery-crew/users/<user_id>/', views.deliverycrew),
    path('category/', views.MenuCategoryView.as_view()),
    path('orders/', views.OrderView.as_view()),
    path('orders/<order_id>', views.OrderItemView.as_view()),
    #path('throttle-check/', views.throttle_check),
    
]