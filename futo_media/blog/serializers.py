# blog/serializers.py
from rest_framework import serializers
from .models import Post, Comment

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
        # CloudinaryField exposes .url (absolute https) when configured correctly
        try:
            if obj.image:
                # obj.image.url is the canonical CDN URL
                url = getattr(obj.image, "url", None)
                if url:
                    return url
        except Exception:
            pass

        # Fallbacks (shouldn't be necessary when using CloudinaryField):
        return None


class PostDetailSerializer(PostListSerializer):
    top_level_comments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ["top_level_comments"]

    def get_top_level_comments(self, obj):
        qs = obj.comments.filter(parent__isnull=True, is_active=True).order_by("created_at")
        return CommentSerializer(qs, many=True, context=self.context).data


class PostCreateSerializer(serializers.ModelSerializer):
    # allow image uploads via multipart/form-data
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Post
        fields = ["id", "title", "subtitle", "content", "image", "slug"]
        read_only_fields = ["id", "slug"]

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
