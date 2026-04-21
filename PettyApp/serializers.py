from rest_framework import serializers
from .models import *


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    avg_rating = serializers.FloatField(read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    image = serializers.SerializerMethodField()  # ✅ FIX

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['user']  

    def get_image(self, obj):  # ✅ FIX
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None     


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")
    email = serializers.ReadOnlyField(source="user.email")
    image = serializers.SerializerMethodField()   # ✅ ADD THIS

    class Meta:
        model = Profile
        fields = "__all__"

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ["user"]  


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = ["user", "product"]


class ReplySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_image = serializers.SerializerMethodField()   # ✅ ADD

    class Meta:
        model = Reply
        fields = "__all__"
        read_only_fields = ["user", "comment"]

    def get_user_image(self, obj):
        request = self.context.get("request")
        if hasattr(obj.user, "profile") and obj.user.profile.image:
            return request.build_absolute_uri(obj.user.profile.image.url)
        return None


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.ReadOnlyField(source="user.id")
    user_image = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = "__all__"  
        read_only_fields = ["user", "blog"] 

    def get_user_image(self, obj):  # ✅ FIX
        request = self.context.get("request")
        if hasattr(obj.user, "profile") and obj.user.profile.image:
            return request.build_absolute_uri(obj.user.profile.image.url)
        return None       
    
    def get_replies(self, obj):
            request = self.context.get("request")
            return ReplySerializer(
                obj.replies.all(),
                many=True,
                context={"request": request}
            ).data


class BlogSerializer(serializers.ModelSerializer):
    total_likes = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Blog
        fields = '__all__'

    def get_total_likes(self, obj):
        return obj.likes.count()    
    
    def get_is_liked(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return obj.likes.filter(user=user).exists()
        return False
    
    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None
        

class TestimonialSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username") 

    class Meta:
        model = Testimonial
        fields = '__all__'


class SubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscriber
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = CartItem
        fields = '__all__'


class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = Wishlist
        fields = "__all__"        


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")
    product_image = serializers.SerializerMethodField()
    product_price = serializers.ReadOnlyField(source="product.price")

    class Meta:
        model = OrderItem
        fields = ["product_name", "product_image", "product_price", "quantity"]

    def get_product_image(self, obj):
        request = self.context.get("request")
        if obj.product.image:
            return request.build_absolute_uri(obj.product.image.url)
        return None


class OrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    address = AddressSerializer()
    username = serializers.ReadOnlyField(source="user.username")
    email = serializers.ReadOnlyField(source="user.email")

    class Meta:
        model = Order
        fields = "__all__"

    def get_items(self, obj):
        request = self.context.get("request")
        return OrderItemSerializer(
            obj.items.all(),
            many=True,
            context={"request": request}
        ).data  