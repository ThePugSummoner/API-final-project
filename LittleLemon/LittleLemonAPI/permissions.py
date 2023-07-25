from rest_framework import permissions
from django.contrib.auth.models import Group

class GroupPermission(permissions.BasePermission):
    
    def has_permission(self, request, view):
        
        group_name = 'Manager'
        if request.method == 'GET':
            return True
        if request.user.is_authenticated:

            try:
                manager_group = Group.objects.get(name=group_name)
                return manager_group in request.user.groups.all() or request.user.is_superuser
            except Group.DoesNotExist:
                return False
            
        return False

class IsManagerOrFullAccess(permissions.BasePermission):
    def has_permission(self, request, view):
        #if request.method in permissions.SAFE_METHODS:
        #    return True
        if request.user.groups.filter(name="Manager").exists():
            return True
        return request.user.is_authenticated #False #request.method in ["GET", "POST", "HEAD", "OPTIONS"]
    
class UserPerimission(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and obj.user == request.user
       
class IsDeliveryCrew(permissions.BasePermission):
    def has_permission(self, request, view):
        # Check if the user belongs to the "delivery_crew" group
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return user.groups.filter(name="Delivery crew").exists()
