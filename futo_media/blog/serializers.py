from rest_framework import serializers
from .models import Post, Comment, Like

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'post', 'name', 'email', 'content', 'created_at']
        read_only_fields = ['id', 'created_at', 'post']

class PostListSerializer(serializers.ModelSerializer):
    likes_count = serializers.IntegerField(source='likes_count', read_only=True)
    comments_count = serializers.IntegerField(source='comments_count', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'title', 'subtitle', 'slug', 'content', 'image_url', 'created_at', 'likes_count', 'comments_count']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            try:
                if request:
                    return request.build_absolute_uri(obj.image.url)
            except Exception:
                return obj.image.url
        return None

class PostDetailSerializer(PostListSerializer):
    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + []
