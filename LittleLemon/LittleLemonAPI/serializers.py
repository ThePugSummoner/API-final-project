from rest_framework import serializers
from .models import MenuItem, Category, Cart, Order, OrderItem
from decimal import Decimal
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
from django.contrib.auth.models import User, Group
#import bleach

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields = ['id', 'username', 'email']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'title']

class MenuItemSerializer(serializers.ModelSerializer):                                     
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    ordering_fields=['price','inventory']
    search_fields=['title', 'category__title']
    
    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'category', 'category_id']

class CartSerializer(serializers.ModelSerializer):
    menuitem_title = serializers.SerializerMethodField()
    quantity = serializers.IntegerField()
    unit_price = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['menuitem', 'menuitem_title', 'quantity', 'unit_price', 'price']

    def get_menuitem_title(self, cart):
        return cart.menuitem.title if cart.menuitem else None
    
    def get_unit_price(self, cart):
        if cart.menuitem:
            return cart.menuitem.price
        return None

class OrderItemSerializer(serializers.ModelSerializer):
    menuitem_title = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['order', 'menuitem_title', 'menuitem', 'quantity', 'unit_price', 'price']
        extra_kwargs = {
            'price': {'read_only': True},
            'unit_price': {'read_only': True},
            'quantity': {'read_only': True},
            'menuitem': {'read_only': True},
            'order': {'read_only': True},
            'menuitem_title': {'read_only': True},
        }
    
    def get_menuitem_title(self, cart):
        return cart.menuitem.title if cart.menuitem else None

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(read_only=True, many=True)
    total = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True, required=False)
    delivery_crew = UserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'status', 'items', 'total']
    
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.method == 'POST':
            fields.pop('status', None)
        return fields
    
    def create(self, validated_data):
        # Exclude unnecessary fields from the input data
        validated_data.pop('user', None)
        validated_data.pop('delivery_crew', None)
        validated_data.pop('status', None)
        validated_data.pop('items', None)
        # Calculate the total price based on the order items
        order_items_data = self.initial_data.get('items', [])
        total = sum(item.get('price', 0) * item.get('quantity', 0) for item in order_items_data)
        # Create the order with the current user and total price
        user = self.context['request'].user
        order = Order.objects.create(user=user, **validated_data)
        return order
