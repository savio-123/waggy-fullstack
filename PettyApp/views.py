from rest_framework.views import APIView
from google import genai
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import *
from .serializers import *
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from urllib.parse import quote,unquote
from django.contrib.auth import authenticate
from django.db.models import Sum,Avg,Count
from django.conf import settings
from django.db.models.functions import Coalesce,TruncDate
from rest_framework.permissions import IsAuthenticated,IsAuthenticatedOrReadOnly,IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import ProductSerializer
import razorpay
import json
import re

def get_gemini_client():
    return genai.Client(api_key=settings.GEMINI_API)

class RegisterUser(APIView):

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"})

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"})
        
        if not email:
            return Response({"error": "Email is required"}, status=400)

        # ✅ PASSWORD VALIDATION
        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters"}, status=400)

        if not re.search(r'[A-Za-z]', password):
            return Response({"error": "Must include at least one letter"}, status=400)

        if not re.search(r'\d', password):
            return Response({"error": "Must include at least one number"}, status=400)

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return Response({"error": "Must include at least one special character"}, status=400)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        return Response({"message": "User created successfully"})
    
class LoginUser(APIView):

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=400
            )

        user = authenticate(username=username, password=password)

        if user is None:
            return Response(
                {"error": "Invalid username or password"},
                status=401
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })
    
class ForgotPassword(APIView):

    def post(self, request):
        email = request.data.get("email")

        try:
            user = User.objects.get(email=email)

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            safe_token = quote(token)
        

            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

            reset_link = f"{frontend_url}/reset-password?uid={uid}&token={safe_token}"

            print("UID:", uid)
            print("TOKEN:", token)
            print("VALID:", default_token_generator.check_token(user, token))

            send_mail(
                    "Password Reset",
                    "",   # ❌ remove plain text
                    "noreply@petty.com",
                    [email],
                    html_message=f"""
                            <h2>Password Reset</h2>
                            <p>Click the button below to reset your password:</p>

                            <a href="{reset_link}" 
                            style="
                            background:#000;
                            color:#fff;
                            padding:10px 20px;
                            text-decoration:none;
                            border-radius:5px;
                            ">
                            Reset Password
                            </a>

                            <p>If you didn’t request this, ignore this email.</p>
                            """,
                )
            return Response({"message": "Reset link sent to email"})

        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

class ResetPassword(APIView):

    def post(self, request):
        uid = request.data.get("uid")
        token = unquote(request.data.get("token"))
        password = request.data.get("password")

        # ✅ VALIDATION
        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters"}, status=400)

        if not re.search(r'[A-Za-z]', password):
            return Response({"error": "Must include at least one letter"}, status=400)

        if not re.search(r'\d', password):
            return Response({"error": "Must include at least one number"}, status=400)

        if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
            return Response({"error": "Must include at least one special character"}, status=400)
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)

            if default_token_generator.check_token(user, token):
                user.set_password(password)
                user.save()
                return Response({"message": "Password reset successful"})
            else:
                return Response({"error": "Invalid token"}, status=400)

        except Exception as e:
            print("ERROR:", e)
            return Response({"error": "Invalid request"}, status=400)
        
class AIChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get("message")

        try:
            products = Product.objects.filter(is_approved=True)

            CONTACT_INFO = """
            Contact us:
            - Email: support@petty.com
            - Phone: +91 9876543210
            """

            product_list = [
                f"""
                ID: {p.id}
                Name: {p.name}
                Category: {p.category.name}
                Price: ₹{p.price}
                Description: {p.description}
                """
                for p in products
            ]

            prompt = f"""
            You are a smart AI shopping assistant for a pet shop.

            Your job:
            - Understand user intent even if wording is imperfect
            - Recommend BEST matching products
            - Help with FAQs, orders, payments, returns, support

            IMPORTANT:
            - NEVER mention product IDs in reply
            - ALWAYS use product names in reply

            You must understand:
            1. Pet type (dog, cat, bird, etc.)
            2. Price intent:
               - cheap = lower price products
               - premium = higher price products
            3. Product type:
               - cloth = sweater, dress, outfit
            4. Color:
               - If exact color exists → prioritize it
               - If NOT → ignore color
               - If not found → match product type

            5. Ranking:
               - Always return TOP 3 best matches

            Available products:
            {product_list}

            Contact info:
            {CONTACT_INFO}

            User query:
            {message}

            Rules:
            - ALWAYS recommend products if somewhat relevant
            - NEVER say "I don't know" unless completely unrelated
            - Return maximum 3 product IDs

            Response format STRICT:
            {{
              "reply": "short helpful answer",
              "product_ids": [1,2,3]
            }}
            """

            client = get_gemini_client()

            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt
            )

            text = response.text
            match = re.search(r'\{.*\}', text, re.S)

            if match:
                try:
                    data = json.loads(match.group())
                except:
                    data = {"reply": text, "product_ids": []}
            else:
                data = {"reply": text, "product_ids": []}

            # ✅ FIX: keep only valid IDs
            valid_ids = set(products.values_list("id", flat=True))
            product_ids = [pid for pid in data.get("product_ids", []) if pid in valid_ids][:3]

            matched_products = Product.objects.filter(id__in=product_ids)

            product_data = ProductSerializer(
                            matched_products,
                            many=True,
                            context={"request": request}  
                        ).data

            return Response({
                "reply": data.get("reply", ""),
                "products": product_data
            })

        except Exception as e:
            if "429" in str(e):
                return Response({
                    "reply": "⚠️ AI is temporarily busy. Please try again in a minute.",
                    "products": []
                })

            return Response({
                "reply": "⚠️ Something went wrong. Please try again.",
                "products": []
            }, status=500)
        
class AllProducts(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        products = Product.objects.filter(is_approved=True)
        serializer = ProductSerializer(
                            products,
                            many=True,
                            context={"request": request}   # ✅ FIX
                        )
        return Response(serializer.data)      

# PRODUCTS
class ApproveProduct(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, id):
        product = get_object_or_404(Product, id=id)
        product.is_approved = True
        product.save()

        return Response({"message": "Product approved"})
    
class PendingProducts(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        products = Product.objects.filter(is_approved=False)
        return Response(
                        ProductSerializer(
                            products,
                            many=True,
                            context={"request": request}   # ✅ FIX
                        ).data
                    )    
    
class ProductList(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        query = request.GET.get("search")
        category = request.GET.get("category") 
        animal = request.GET.get("animal")
        rating = request.GET.get("rating")
        min_price = request.GET.get("minPrice")
        max_price = request.GET.get("maxPrice")
        sort = request.GET.get("sort")

        data = Product.objects.filter(is_approved=True)\
              .select_related('category', 'user')\
              .prefetch_related('reviews')\
              .annotate(
                avg_rating=Coalesce(Avg('reviews__rating'), 0.0),
                total_reviews=Count('reviews')
            )

        if query:
            data = data.filter(name__icontains=query)

        if category and category != "all":
            data = data.filter(category__name__icontains=category)

        if animal and animal != "all":
            data = data.filter(category__name__icontains=animal)

        if rating:
            data = data.filter(avg_rating__gte=float(rating))   

        if min_price:
            data = data.filter(price__gte=min_price)

        if max_price:
            data = data.filter(price__lte=max_price)

        if sort == "price_low":
            data = data.order_by("price")

        if sort == "price_high":
            data = data.order_by("-price")

        paginator = PageNumberPagination()
        paginator.page_size = 8

        result_page = paginator.paginate_queryset(data, request)

        serializer = ProductSerializer(
                                    result_page,
                                    many=True,
                                    context={"request": request}   # ✅ FIX
                                )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                user=request.user,
                is_approved=False
            )
            return Response({"message": "Product submitted for approval"})
        return Response(serializer.errors)


class ProductDetail(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, id):
        return get_object_or_404(Product, id=id)

    def get(self, request, id):
        product = Product.objects.filter(id=id)\
            .select_related('category', 'user')\
            .annotate(
                avg_rating=Avg('reviews__rating'),
                total_reviews=Count('reviews')
            ).first()

        if not product:
            return Response({"error": "Not found"}, status=404)

        if not product.is_approved and product.user != request.user and not request.user.is_staff:
            return Response({"error": "Not allowed"}, status=403)

        return Response(
                        ProductSerializer(
                            product,
                            context={"request": request}   # ✅ FIX
                        ).data
                    )


    def put(self, request, id):
        product = self.get_object(id)

        if product.user != request.user and not request.user.is_staff:
            return Response({"error": "Not allowed"}, status=403)

        data = request.data.copy()

        if not request.user.is_staff:
            data.pop("is_approved", None)

        serializer = ProductSerializer(product, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors)

    def delete(self, request, id):
        product = self.get_object(id)
        if product.user != request.user and not request.user.is_staff:
            return Response({"error": "Not allowed"}, status=403)
        product.delete()
        return Response({"message": "Deleted"})
    
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(
            request.user.profile,
            context={"request": request}   # ✅ ADD THIS
        )
        data = serializer.data
        data["is_staff"] = request.user.is_staff
        return Response(data)

    def put(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request}   # ✅ ADD THIS
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors)
    

class AddressListCreate(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = Address.objects.filter(user=request.user)
        return Response(AddressSerializer(addresses, many=True).data)

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data)
        return Response(serializer.errors)


class AddressDetail(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        address = get_object_or_404(Address, id=id, user=request.user)
        
        if request.data.get("is_default"):
            Address.objects.filter(user=request.user).update(is_default=False)

        serializer = AddressSerializer(address, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors)
    
    def delete(self, request, id):
        address = get_object_or_404(Address, id=id, user=request.user)
        address.delete()
        return Response({"message": "Deleted"})    

class ReviewListCreate(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, product_id):
        reviews = Review.objects.filter(product_id=product_id)
        return Response(ReviewSerializer(reviews, many=True).data)

    def post(self, request, product_id):
        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, product_id=product_id)
            return Response(serializer.data, status=201)
        return Response(serializer.errors)    
    
class ProductByCategory(APIView):

    def get(self, request):
        category = request.GET.get("category") 
        animal = request.GET.get("animal")       

        products = Product.objects.filter(is_approved=True)\
                    .annotate(
                        avg_rating=Coalesce(Avg('reviews__rating'), 0.0),
                        total_reviews=Count('reviews')
                    )

        if category:
            products = products.filter(category__name__icontains=category)

        if animal:
            products = products.filter(category__name__icontains=animal)

        return Response(
                        ProductSerializer(
                            products,
                            many=True,
                            context={"request": request}   # ✅ FIX
                        ).data
                    )

class BestSellingProducts(APIView):
    def get(self, request):

        products = Product.objects.filter(is_approved=True).annotate(
            total_sold=Coalesce(Sum('orderitem__quantity'), 0)  # ✅ FIXED
        ).order_by('-total_sold')[:10]

        return Response(
                        ProductSerializer(
                            products,
                            many=True,
                            context={"request": request}   # ✅ FIX
                        ).data
                    ) 
    
class CategoryList(APIView):

    def get(self, request):
        data = Category.objects.all()
        return Response(CategorySerializer(data, many=True).data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors)
    
class CategoryDetail(APIView):

    def get_object(self, id):
        return get_object_or_404(Category, id=id)

    def get(self, request, id):
        return Response(CategorySerializer(self.get_object(id)).data)

    def put(self, request, id):
        category = self.get_object(id)
        serializer = CategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

    def delete(self, request, id):
        self.get_object(id).delete()
        return Response({"message": "Deleted"})    

# BLOGS
class BlogList(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        data = Blog.objects.all()\
                .select_related('user')\
                .prefetch_related('likes', 'comments')
        serializer = BlogSerializer(data, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        serializer = BlogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors)


class BlogDetail(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, id):
        return get_object_or_404(Blog, id=id)

    def get(self, request, id):
        blog = self.get_object(id)
        serializer = BlogSerializer(blog, context={"request": request})  # FIX
        return Response(serializer.data)

    def put(self, request, id):
        blog = self.get_object(id)
        if blog.user != request.user:
            return Response({"error": "Not allowed"}, status=403)
        serializer = BlogSerializer(blog, data=request.data,context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

    def delete(self, request, id):
        blog = self.get_object(id)
        if blog.user != request.user:
            return Response({"error": "Not allowed"}, status=403)
        blog.delete()
        return Response({"message": "Deleted"})
    
class ToggleLike(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, blog_id):
        blog = get_object_or_404(Blog, id=blog_id)

        like, created = BlogLike.objects.get_or_create(
            user=request.user,
            blog=blog
        )

        if not created:
            like.delete()
            return Response({"message": "Unliked"})

        return Response({"message": "Liked"})

class CommentListCreate(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, blog_id):
        comments = Comment.objects.filter(blog_id=blog_id).order_by("-created_at")

        return Response(
            CommentSerializer(
                comments,
                many=True,
                context={"request": request}   # ✅ ADD THIS
            ).data
        )

    def post(self, request, blog_id):
        blog = get_object_or_404(Blog, id=blog_id)  
        if not request.data.get("content"):
            return Response({"error": "Empty comment"}, status=400)
        serializer = CommentSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user, blog=blog)

            return Response(
                CommentSerializer(
                    serializer.instance,
                    context={"request": request}
                ).data,
                status=201
            )

        return Response(serializer.errors, status=400)

class CommentDetail(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, id):
        return get_object_or_404(Comment, id=id)

    def put(self, request, id):
        comment = self.get_object(id)

        if comment.user != request.user:
            return Response({"error": "Not allowed"}, status=403)

        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if not request.data.get("content"):
            return Response({"error": "Empty comment"}, status=400)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors)

    def delete(self, request, id):
        comment = self.get_object(id)

        if comment.user != request.user:
            return Response({"error": "Not allowed"}, status=403)

        comment.delete()
        return Response({"message": "Deleted"})        
        
class ReplyCreate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)  

        if not request.data.get("content"):
            return Response({"error": "Empty reply"}, status=400)

        serializer = ReplySerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user, comment=comment)

            return Response(
                ReplySerializer(
                    serializer.instance,
                    context={"request": request}
                ).data,
                status=201
            )

        return Response(serializer.errors, status=400)   
    
class RelatedProducts(APIView):

    def get(self, request, id):
        product = get_object_or_404(Product, id=id)

        related = Product.objects.filter(
                category=product.category,
                is_approved=True
            ).exclude(id=id)\
            .select_related('category')\
            .annotate(
                avg_rating=Avg('reviews__rating'),
                total_reviews=Count('reviews')
            )[:8]

        return Response(
                        ProductSerializer(
                            related,
                            many=True,
                            context={"request": request}   # ✅ FIX
                        ).data
                    )    
                                
    
class AddToCart(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        product_id = request.data.get('product_id')

        cart, _ = Cart.objects.get_or_create(user=user)
        product = get_object_or_404(Product, id=product_id)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product
        )

        if not created:
            item.quantity += 1 
        else:
            item.quantity = 1 

        item.save()

        return Response({"message": "Added"})

class RemoveFromCart(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        product_id = request.data.get('product_id')

        cart, _ = Cart.objects.get_or_create(user=user)
        item = get_object_or_404(CartItem, cart=cart, product_id=product_id)

        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()

        return Response({"message": "Updated"})
    
class DeleteCartItem(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        product_id = request.data.get('product_id')

        cart, _ = Cart.objects.get_or_create(user=user)
        item = get_object_or_404(CartItem, cart=cart, product_id=product_id)

        item.delete()

        return Response({"message": "Item removed"})    

class ViewCart(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = CartItem.objects.filter(cart=cart).select_related('product')

        return Response(
            CartItemSerializer(
                items,
                many=True,
                context={"request": request}   # ✅ ADD THIS
            ).data
        )
         
class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Wishlist.objects.filter(user=request.user)\
                .select_related('product')

        return Response(
            WishlistSerializer(
                items,
                many=True,
                context={"request": request}   # ✅ ADD THIS
            ).data
        )

class ToggleWishlist(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        product = get_object_or_404(Product, id=product_id)

        wishlist, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:
            wishlist.delete()
            return Response({"message": "Removed from wishlist"})

        return Response({"message": "Added to wishlist"})    

# TESTIMONIALS
class TestimonialList(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        data = Testimonial.objects.all().order_by('-id')[:3]
        return Response(TestimonialSerializer(data, many=True).data)

    def post(self, request):
        print("USER:", request.user)
        serializer = TestimonialSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)  
            return Response(serializer.data, status=201)
        return Response(serializer.errors)



# REGISTER / NEWSLETTER
class Register(APIView):
    def post(self, request):
        email = request.data.get("email")
        if Subscriber.objects.filter(email=email).exists():
            return Response({"error": "Already subscribed"})
        Subscriber.objects.create(email=email)
        return Response({"message": "Subscribed successfully"})
    
class CreateRazorpayOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        address_id = request.data.get("address_id")

        cart, _ = Cart.objects.get_or_create(user=user)
        items = CartItem.objects.filter(cart=cart)

        if not items.exists():
            return Response({"error": "Cart empty"}, status=400)

        address = get_object_or_404(Address, id=address_id, user=user)

        total = sum(item.product.price * item.quantity for item in items)

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        razorpay_order = client.order.create({
            "amount": int(total * 100),  # paise
            "currency": "INR",
            "payment_capture": 1
        })


        return Response({
            "razorpay_order_id": razorpay_order["id"],
            "amount": total,
            "key": settings.RAZORPAY_KEY_ID
        })    
    
class VerifyPayment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        address_id = request.data.get("address_id")

        cart, _ = Cart.objects.get_or_create(user=user)
        items = CartItem.objects.filter(cart=cart)

        if not items.exists():
            return Response({"error": "Cart empty"}, status=400)

        address = get_object_or_404(Address, id=address_id, user=user)

        total = sum(item.product.price * item.quantity for item in items)

        # CREATE ORDER ONLY AFTER PAYMENT SUCCESS
        order = Order.objects.create(
            user=user,
            address=address,
            total_price=total,
            payment_method="ONLINE",
            is_paid=True
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity
            )

        items.delete()

        return Response({"message": "Payment verified & order created"})
    
class UpdatePaymentStatus(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, id):
        order = Order.objects.get(id=id)
        if order.payment_method == "ONLINE":
            return Response(
                {"error": "Online payments cannot be modified"},
                status=400
            )

        order.is_paid = request.data.get("is_paid")
        order.save()

        return Response({"message": "Payment status updated"})    

class RetryPayment(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id, user=request.user)

        if order.is_paid:
            return Response({"error": "Already paid"}, status=400)

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        razorpay_order = client.order.create({
            "amount": int(order.total_price * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        order.razorpay_order_id = razorpay_order["id"]
        order.save()

        return Response({
            "razorpay_order_id": razorpay_order["id"],
            "amount": order.total_price,
            "order_id": order.id,
            "key": settings.RAZORPAY_KEY_ID
        })    

class CreateOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        address_id = request.data.get("address_id")

        cart, _ = Cart.objects.get_or_create(user=user)
        items = CartItem.objects.filter(cart=cart)

        if not items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        address = get_object_or_404(Address, id=address_id, user=user)

        total = sum(item.product.price * item.quantity for item in items)

        order = Order.objects.create(
        user=user,
        address=address,
        total_price=total,
        payment_method="COD"   
    )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity
            )

        items.delete()

        return Response({"message": "Order placed"})
    
class OrderList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by("-id")
        return Response(
        OrderSerializer(
            orders,
            many=True,
            context={"request": request}
        ).data
    )

class RequestReturn(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id, user=request.user)

        # ✅ CONDITIONS
        if order.created_at < timezone.now() - timedelta(days=7):
            return Response({"error": "Return window closed"}, status=400)
        
        if order.status != "Delivered":
            return Response({"error": "Only delivered orders can be returned"}, status=400)

        if not order.is_paid:
            return Response({"error": "Only paid orders eligible"}, status=400)

        if order.return_requested:
            return Response({"error": "Already requested"}, status=400)

        order.return_requested = True
        order.return_status = "Requested"
        order.save()

        return Response({"message": "Return request submitted"})
    
class HandleReturn(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id)

        action = request.data.get("action")  # approve / reject

        if action == "approve":
            order.return_status = "Approved"
            order.refund_status = "Processed"  # simple version
        elif action == "reject":
            order.return_status = "Rejected"

        order.save()

        return Response({"message": f"Return {action}ed"})    

class AdminOrderList(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        orders = Order.objects.all().order_by("-id")

        return Response(
            OrderSerializer(
                orders,
                many=True,
                context={"request": request}
            ).data
        )
    
class AdminStats(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_orders = Order.objects.count()

        revenue_data = Order.objects.filter(
            status="Delivered"
        ).aggregate(total=Sum("total_price"))

        total_revenue = revenue_data["total"] or 0  # ✅ SAFE FIX

        pending_orders = Order.objects.filter(status="Pending").count()
        shipped_orders = Order.objects.filter(status="Shipped").count()
        delivered_orders = Order.objects.filter(status="Delivered").count()

        return Response({
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "pending_orders": pending_orders,
            "shipped_orders": shipped_orders,
            "delivered_orders": delivered_orders
        })


class AdminTopProducts(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = (
            OrderItem.objects
            .values("product__name")
            .annotate(total=Sum("quantity"))
            .order_by("-total")[:5]
        )

        result = [
            {
                "name": item["product__name"],
                "value": item["total"]
            }
            for item in data
        ]

        return Response(result)    

class AdminChartData(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = (
            Order.objects.filter(status="Delivered")
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(total=Sum("total_price"))
            .order_by("date")
        )

        return Response(data)    

class AdminRecentOrders(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        orders = Order.objects.order_by("-id")[:5]

        return Response(
            OrderSerializer(
                orders,
                many=True,
                context={"request": request}
            ).data
        )

class AdminReturnList(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        orders = Order.objects.filter(return_requested=True).order_by("-id")

        return Response(
            OrderSerializer(
                orders,
                many=True,
                context={"request": request}
            ).data
        )

class DeleteOrderAdmin(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, id):
        order = get_object_or_404(Order, id=id)
        order.delete()
        return Response({"message": "Order deleted"})
    
class AdminProductList(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        products = Product.objects.all().select_related("category", "user")

        #  SEARCH
        search = request.GET.get("search")
        if search:
            products = products.filter(name__icontains=search)

        #  CATEGORY
        category = request.GET.get("category")
        if category and category != "all":
            products = products.filter(category_id=category)

        # STATUS
        status = request.GET.get("status")
        if status == "approved":
            products = products.filter(is_approved=True)
        elif status == "pending":
            products = products.filter(is_approved=False)

        #  PAGINATION
        paginator = PageNumberPagination()
        paginator.page_size = 8 
        result = paginator.paginate_queryset(products, request)

        serializer = ProductSerializer(
                                    result,
                                    many=True,
                                    context={"request": request}   # ✅ FIX
                                )

        return paginator.get_paginated_response(serializer.data)    

class DeleteProductAdmin(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, id):
        product = get_object_or_404(Product, id=id)
        product.delete()
        return Response({"message": "Product deleted"})    
    
class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        order = get_object_or_404(Order, id=id, user=request.user)
        return Response(OrderSerializer(order, context={"request": request}).data)   
    
class UpdateOrderStatus(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, id):
        order = get_object_or_404(Order, id=id)

        new_status = request.data.get("status")

        valid_transitions = {
            "Pending": ["Shipped"],
            "Shipped": ["Delivered"],
            "Delivered": []
        }


        if new_status not in ["Pending", "Shipped", "Delivered"]:
            return Response({"error": "Invalid status"}, status=400)
        
        allowed_next = valid_transitions[order.status]

        if new_status not in allowed_next:
            return Response({"error": "Invalid transition"}, status=400)

        order.status = new_status
        order.save()

        return Response({"message": "Status updated"})    
    
class CancelOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id, user=request.user)

        # Only allow cancel if not paid and still pending
        if order.is_paid:
            return Response({"error": "Paid orders cannot be cancelled"}, status=400)

        if order.status != "Pending":
            return Response({"error": "Only pending orders can be cancelled"}, status=400)

        order.delete()

        return Response({"message": "Order cancelled successfully"})    