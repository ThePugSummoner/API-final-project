from django.shortcuts import render
from rest_framework import generics, status, viewsets, permissions
from .models import MenuItem, Category, Cart, Order, OrderItem
from .serializers import MenuItemSerializer, CategorySerializer, CartSerializer, UserSerializer, OrderItemSerializer, OrderSerializer
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.contrib.auth.models import User, Group
from .permissions import GroupPermission, UserPerimission, IsManagerOrFullAccess

# Create your views here.

class MenuCategoryView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, GroupPermission]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class MenuItemsView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, GroupPermission]
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    
class SingleMenuItem(generics.RetrieveUpdateAPIView, generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, GroupPermission]
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

class CartView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        user = self.request.user
        return Cart.objects.filter(user=user)
    
    def perform_create(self, serializer):
        menuitem_id = self.request.data.get('menuitem')
        quantity = self.request.data.get('quantity')

        if menuitem_id and quantity:
            menuitem = MenuItem.objects.get(pk=menuitem_id)
            unit_price = menuitem.price
        cart = serializer.save(user=self.request.user, unit_price=unit_price)
        cart.price = cart.unit_price * cart.quantity
        cart.save()

    def delete(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        if queryset.exists():
            cart = queryset.first()

            if cart.user == request.user:
               cart.clear_cart_items()
            return Response({"message": "All items have been deleted from the cart."}, status=status.HTTP_204_NO_CONTENT)
    
        return Response({"error": "You don't have permission to delete this cart."}, status=status.HTTP_403_FORBIDDEN)
    
class OrderView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsManagerOrFullAccess]
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get_queryset(self):
        user = self.request.user

        if user.groups.filter(name="Manager").exists():
            return Order.objects.all()
        
        if user.groups.filter(name="Delivery crew").exists():
            return Order.objects.filter(delivery_crew__isnull=False)
        
        return Order.objects.filter(user=user)
    
    def perform_create(self, serializer):
        cart_items = Cart.objects.filter(user=self.request.user)
        total = sum(cart_item.price for cart_item in cart_items)
        order = serializer.save(user=self.request.user, total=total)

        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                menuitem=cart_item.menuitem,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                price=cart_item.price,
            )
        cart_items.delete()

        return order
    

class OrderItemView(generics.ListAPIView, generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    #queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

    def get_queryset(self):
        user = self.request.user
        order_id = self.kwargs['order_id']
        try:
            order = Order.objects.get(id=order_id)
            #return OrderItem.objects.filter(order=order)
        except Order.DoesNotExist:
            return None
        if user.groups.filter(name="Manager").exists() or order.user == user:
            return OrderItem.objects.filter(order=order)
        
        return None

    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            if queryset is not None:
                serializer = OrderItemSerializer(queryset, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Order not found or does not belong to current user."}, status=status.HTTP_404_NOT_FOUND)
        except Order.DoesNotExist as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
    
    def update_order(self, request, order):
        user = request.user    
        # Check if the user is a manager or the owner of the order
        #if not request.user.groups.filter(name="Manager").exists() and order.user != request.user:
        #    return Response({"error": "You don't have permission to modify this order."}, status=status.HTTP_403_FORBIDDEN)
        
        # Update delivery_crew and status if provided in the request data
        if user.groups.filter(name='Manager').exists():
            delivery_crew_id = request.data.get('delivery_crew')

            if delivery_crew_id:
                try:
                    delivery_crew = User.objects.get(pk=delivery_crew_id)
                    if not delivery_crew.groups.filter(name="Delivery crew").exists():
                        return Response(
                            {"error": "The selected user is not a member of the Delivery crew group."},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    order.delivery_crew = delivery_crew
                except User.DoesNotExist:
                    return Response({"error": "Delivery crew user not found."}, status=status.HTTP_404_NOT_FOUND)

            status_value = request.data.get('status')

            if status_value:
                order.status = status_value

            order.save()
            serializer = OrderItemSerializer(order.orderitem_set.all(), many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        elif user.groups.filter(name='Delivery crew').exists():
            status_value = request.data.get('status')

            if status_value:
                order.status = status_value
                order.save()
                return Response({"message": "Order status updated successfully."}, status=status.HTTP_200_OK)
        return Response({"error": "You don't have permission to modify this order."}, status=status.HTTP_403_FORBIDDEN)
        


    def put(self, request, *args, **kwargs):
        order_id = self.kwargs['order_id']
        try:
            order = Order.objects.get(id=order_id)
            return self.update_order(request, order)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, *args, **kwargs):
        order_id = self.kwargs['order_id']
        try:
            order = Order.objects.get(id=order_id)
            return self.update_order(request, order)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    
    def delete_order(self, request, order):
        # Check if the user is a manager or the owner of the order
        if not request.user.groups.filter(name="Manager").exists():
            return Response({"error": "You don't have permission to delete this order."}, status=status.HTTP_403_FORBIDDEN)

        # Delete the order
        order.delete()
        return Response({"message": "Order deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        order_id = self.kwargs['order_id']
        try:
            order = Order.objects.get(id=order_id)

            # Check if the user is the owner of the order
            if order.user == request.user:
                return Response({"error": "You don't have permission to delete this order."}, status=status.HTTP_403_FORBIDDEN)

            return self.delete_order(request, order)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        
  
     
@api_view(['GET', 'POST'])                                                                                        
@permission_classes({IsAuthenticated})                                                              
def manager_view(request):
    try:
        managers_group = Group.objects.get(name="Manager")
        if request.method == 'GET':
            if request.user.groups.filter(name='Manager').exists():
                managers = User.objects.filter(groups=managers_group)
                serializer = UserSerializer(managers, many=True)
                return Response(serializer.data)
            else:
                return Response({"message": "You are not authorized"}, status=status.HTTP_403_FORBIDDEN)
        elif request.method == 'POST':
            if request.user.groups.filter(name='Manager').exists():
                data = request.data
                username = data.get('username', None)
                if not username:
                    return Response({"error":"Please provide a username in the request data"}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    user = User.objects.get(username=username)
                    user.groups.add(managers_group)
                    return Response({"message":f"User '{username}' added to the Manager group"}, status=status.HTTP_201_CREATED)
                except User.DoesNotExist:
                    return Response({"error": f"User '{username}' does not exist."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"message": "You are not authorized to add users to the Manager group."}, status=status.HTTP_403_FORBIDDEN)

    except Group.DoesNotExist:
        return Response({"message": "Manager group does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['DELETE'])
@permission_classes({IsAuthenticated})
def managers(request, user_id):
   
    if request.method == 'DELETE':
        if request.user.groups.filter(name='Manager').exists():
            try:
                user = get_object_or_404(User, id=user_id)
                managers_group = Group.objects.get(name='Manager')
                managers_group.user_set.remove(user)
                return Response({"message": "User removed from the Manager group"}, status=status.HTTP_204_NO_CONTENT)
            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=404)
        else:
            return Response({"message": "You are not authorized"}, status=status.HTTP_403_FORBIDDEN)
    
    return Response({"message": "Invalid request method."}, status=400)

@api_view(['GET', 'POST'])                                                                                        
@permission_classes({IsAuthenticated})                                                              
def deliverycrew_view(request):
    try:
        deliverycrew_group = Group.objects.get(name="Delivery crew")
        if request.method == 'GET':
            if request.user.groups.filter(name='Manager').exists():
                deliverycrew = User.objects.filter(groups=deliverycrew_group)
                serializer = UserSerializer(deliverycrew, many=True)
                return Response(serializer.data)
            else:
                return Response({"message": "You are not authorized"}, status=status.HTTP_403_FORBIDDEN)
        elif request.method == 'POST':
            if request.user.groups.filter(name='Manager').exists():
                data = request.data
                username = data.get('username', None)
                if not username:
                    return Response({"error":"Please provide a username in the request data"}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    user = User.objects.get(username=username)
                    user.groups.add(deliverycrew_group)
                    return Response({"message":f"User '{username}' added to the Delivery crew group"}, status=status.HTTP_201_CREATED)
                except User.DoesNotExist:
                    return Response({"error": f"User '{username}' does not exist."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"message": "You are not authorized to add users to the Delivery crew group."}, status=status.HTTP_403_FORBIDDEN)

    except Group.DoesNotExist:
        return Response({"message": "Delivery crew group does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['DELETE'])
@permission_classes({IsAuthenticated})
def deliverycrew(request, user_id):
   
    if request.method == 'DELETE':
        if request.user.groups.filter(name='Manager').exists():
            try:
                user = get_object_or_404(User, id=user_id)
                deliverycrew_group = Group.objects.get(name='Delivery crew')
                deliverycrew_group.user_set.remove(user)
                return Response({"message": "User removed from the Delivery crew group"}, status=status.HTTP_204_NO_CONTENT)
            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=404)
        else:
            return Response({"message": "You are not authorized"}, status=status.HTTP_403_FORBIDDEN)
    
    return Response({"message": "Invalid request method."}, status=400)