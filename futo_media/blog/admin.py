# blog/admin.py
from django.contrib import admin
from .models import Post, Comment, Like

class ReplyInline(admin.TabularInline):
    model = Comment
    fk_name = "parent"
    extra = 0
    fields = ("name", "content", "is_active", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "subtitle", "content")
    list_filter = ("created_at",)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "post", "parent", "created_at", "is_active")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "content")
    readonly_fields = ("created_at",)
    inlines = [ReplyInline]

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("post", "visitor_id", "created_at")
    readonly_fields = ("created_at",)
