from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category,
    Product,
    Profile,
    Address,
    Review,
    Blog,
    BlogLike,
    Comment,
    Reply,
    Testimonial,
    Subscriber,
    Cart,
    CartItem,
    Wishlist,
    Order,
    OrderItem,
)

admin.site.site_header = "Petty Admin"
admin.site.site_title = "Petty Admin Portal"
admin.site.index_title = "Welcome to Your Admin Panel"


# =========================
# INLINE ADMINS
# =========================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity")
    can_delete = False


# =========================
# BLOG ADMIN
# =========================
class BlogLikeInline(admin.TabularInline):
    model = BlogLike
    extra = 0
    readonly_fields = ("user",)
    can_delete = False

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    inlines = [BlogLikeInline]
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="60" style="object-fit:cover; border-radius:6px;" />',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Image"

    list_display = (
        "id",
        "title",
        "user",
        "image_preview",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("title", "user__username")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


# =========================
# PROFILE ADMIN
# =========================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius:50%; object-fit:cover;" />',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Profile Image"

    list_display = (
        "id",
        "user",
        "phone",
        "gender",
        "city",
        "state",
        "pincode",
        "image_preview",
    )
    list_filter = ("city", "state", "gender")
    search_fields = ("user__username", "user__email", "city", "state")


# =========================
# ADDRESS ADMIN
# =========================
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "name",
        "phone",
        "city",
        "state",
        "pincode",
        "is_default",
    )
    list_filter = ("city", "state", "is_default")
    search_fields = ("user__username", "name", "phone", "city", "pincode")
    ordering = ("-id",)


# =========================
# COMMENT ADMIN
# =========================
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "blog",
        "content",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("user__username", "content", "blog__title")
    ordering = ("-created_at",)


# =========================
# REPLY ADMIN
# =========================
@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "comment",
        "content",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("user__username", "content", "comment__content")
    ordering = ("-created_at",)


# =========================
# PRODUCT ADMIN
# =========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit:cover; border-radius:6px;" />',
                obj.image.url
            )
        return "No Image"

    image_preview.short_description = "Image"

    def colored_status(self, obj):
        color = "green" if obj.is_approved else "red"
        label = "Approved" if obj.is_approved else "Pending"
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            label
        )

    colored_status.short_description = "Approval"

    list_display = (
        "id",
        "name",
        "user",
        "price",
        "category",
        "colored_status",
        "is_approved",
        "image_preview",
    )
    list_filter = ("is_approved", "category")
    search_fields = ("name", "user__username", "description")
    list_editable = ("is_approved",)
    ordering = ("-id",)


# =========================
# REVIEW ADMIN
# =========================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "user",
        "rating",
        "created_at",
    )
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user__username", "comment")
    ordering = ("-created_at",)


# =========================
# ORDER ADMIN
# =========================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]

    def colored_status(self, obj):
        colors = {
            "Pending": "orange",
            "Shipped": "blue",
            "Delivered": "green",
        }
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            colors.get(obj.status, "black"),
            obj.status
        )

    colored_status.short_description = "Status"

    def colored_payment(self, obj):
        color = "green" if obj.is_paid else "red"
        label = "Paid" if obj.is_paid else "Unpaid"
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            label
        )

    colored_payment.short_description = "Payment"

    list_display = (
        "id",
        "user",
        "total_price",
        "colored_status",
        "payment_method",
        "colored_payment",
        "return_requested",
        "return_status",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_method",
        "is_paid",
        "return_requested",
        "return_status",
    )
    search_fields = ("user__username", "id")
    ordering = ("-created_at",)


# =========================
# ORDER ITEM ADMIN
# =========================
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity")
    search_fields = ("order__id", "product__name")
    ordering = ("-id",)


# =========================
# CATEGORY ADMIN
# =========================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("id",)


# =========================
# CART ADMIN
# =========================
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user")
    search_fields = ("user__username",)
    ordering = ("-id",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity")
    search_fields = ("cart__user__username", "product__name")
    ordering = ("-id",)


# =========================
# WISHLIST ADMIN
# =========================
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product")
    search_fields = ("user__username", "product__name")
    ordering = ("-id",)


# =========================
# TESTIMONIAL ADMIN
# =========================
@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message")
    search_fields = ("user__username", "message")
    ordering = ("-id",)


# =========================
# SUBSCRIBER ADMIN
# =========================
@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("id", "email")
    search_fields = ("email",)
    ordering = ("-id",)
