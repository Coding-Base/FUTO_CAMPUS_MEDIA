# blog/serializers.py
from rest_framework import serializers
from .models import Post, Comment
from urllib.parse import unquote

def _try_decode_url(value):
    if not value:
        return None
    decoded = value
    for _ in range(2):
        if "%" in decoded:
            try:
                decoded = unquote(decoded)
            except Exception:
                break
        else:
            break
    decoded = decoded.lstrip("/")
    if decoded.startswith("media/"):
        decoded = decoded[len("media/"):]
    if decoded.startswith("http://") or decoded.startswith("https://"):
        return decoded
    return None

class CommentSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), allow_null=True, required=False)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "post", "parent", "name", "email", "content", "created_at", "is_active", "replies"]
        read_only_fields = ["id", "created_at", "post", "replies"]

    def get_replies(self, obj):
        qs = obj.replies.filter(is_active=True).order_by("created_at")
        return CommentSerializer(qs, many=True, context=self.context).data

class PostListSerializer(serializers.ModelSerializer):
    likes_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "subtitle",
            "slug",
            "content",
            "image_url",
            "created_at",
            "likes_count",
            "comments_count",
        ]

    def get_image_url(self, obj):
        raw_name = getattr(obj.image, "name", "") or ""
        if raw_name.startswith("http://") or raw_name.startswith("https://"):
            return raw_name

        try:
            raw_url = getattr(obj.image, "url", "") or ""
        except Exception:
            raw_url = ""

        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            return raw_url

        decoded = _try_decode_url(raw_name) or _try_decode_url(raw_url)
        if decoded:
            return decoded

        request = self.context.get("request")
        if raw_url:
            return request.build_absolute_uri(raw_url) if request else raw_url
        if raw_name:
            path = raw_name if raw_name.startswith("/") else f"/{raw_name}"
            return request.build_absolute_uri(path) if request else path

        return None

class PostDetailSerializer(PostListSerializer):
    top_level_comments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ["top_level_comments"]

    def get_top_level_comments(self, obj):
        qs = obj.comments.filter(parent__isnull=True, is_active=True).order_by("created_at")
        return CommentSerializer(qs, many=True, context=self.context).data

class PostCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Post
        fields = ["id", "title", "subtitle", "content", "image", "slug"]
        read_only_fields = ["id", "slug"]

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
