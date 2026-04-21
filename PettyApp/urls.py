from django.urls import path
from .views import *

urlpatterns = [
    
    path('auth/register/', RegisterUser.as_view()),
    path('auth/login/', LoginUser.as_view()),

    path("auth/forgot-password/", ForgotPassword.as_view()),
    path("auth/reset-password/", ResetPassword.as_view()),

    path("ai-chat/", AIChatView.as_view()),
    path("products/all/", AllProducts.as_view()),

    # CATEGORY
    path('categories/', CategoryList.as_view()),
    path('categories/<int:id>/', CategoryDetail.as_view()),

    path("profile/", ProfileView.as_view()),
    path("addresses/", AddressListCreate.as_view()),
    path("addresses/<int:id>/", AddressDetail.as_view()),
    # PRODUCTS
    path('products/', ProductList.as_view()),
    path('products/<int:id>/', ProductDetail.as_view()),
    path('products/filter/', ProductByCategory.as_view()),
    path('products/<int:product_id>/reviews/', ReviewListCreate.as_view()),

    path('products/pending/', PendingProducts.as_view()),
    path('products/approve/<int:id>/', ApproveProduct.as_view()),
    path("products/best-selling/", BestSellingProducts.as_view()),
    path("products/<int:id>/related/", RelatedProducts.as_view()),

    # BLOGS
    path('blogs/', BlogList.as_view()),
    path('blogs/<int:id>/', BlogDetail.as_view()),
    path("blogs/<int:blog_id>/like/", ToggleLike.as_view()),
    path("blogs/<int:blog_id>/comments/", CommentListCreate.as_view()),
    path("comments/<int:comment_id>/reply/", ReplyCreate.as_view()),
    path("comments/<int:id>/", CommentDetail.as_view()),

    # TESTIMONIAL
    path('testimonials/', TestimonialList.as_view()),

    # REGISTER
    path('register/', Register.as_view()),

    # CART
    path('cart/', ViewCart.as_view()),
    path('cart/add/', AddToCart.as_view()),
    path('cart/remove/', RemoveFromCart.as_view()),
    path('cart/delete/', DeleteCartItem.as_view()),

    path("wishlist/", WishlistView.as_view()),  
    path("wishlist/toggle/", ToggleWishlist.as_view()),

    # ORDER
    path("payment/create/", CreateRazorpayOrder.as_view()),
    path("payment/verify/", VerifyPayment.as_view()),
    path("orders/<int:id>/payment/", UpdatePaymentStatus.as_view()),
    path("orders/<int:id>/retry-payment/", RetryPayment.as_view()),
    path('order/create/', CreateOrder.as_view()),
    path("admin/orders/", AdminOrderList.as_view()),
    path("admin/orders/<int:id>/delete/", DeleteOrderAdmin.as_view()),
    path("admin/products/", AdminProductList.as_view()),
    path("admin/stats/", AdminStats.as_view()),
    path("admin/chart/", AdminChartData.as_view()),
    path("admin/top-products/", AdminTopProducts.as_view()),
    path("admin/recent-orders/", AdminRecentOrders.as_view()),
    path("admin/products/<int:id>/delete/", DeleteProductAdmin.as_view()),
    path("orders/<int:id>/return/", RequestReturn.as_view()),
    path("admin/returns/", AdminReturnList.as_view()),
    path("admin/orders/<int:id>/return/", HandleReturn.as_view()),
    path("orders/", OrderList.as_view()),
    path("orders/<int:id>/", OrderDetailView.as_view()),
    path("orders/<int:id>/status/", UpdateOrderStatus.as_view()),
    path("orders/<int:id>/cancel/", CancelOrder.as_view()),
]