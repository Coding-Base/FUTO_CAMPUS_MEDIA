from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Post, Comment, Like
from .serializers import PostListSerializer, CommentSerializer
from django.shortcuts import get_object_or_404

class PostViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only list/detail for posts. Newest first (model Meta ordering).
    """
    queryset = Post.objects.all()
    serializer_class = PostListSerializer
    lookup_field = 'slug'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['GET', 'POST'], url_path='comments')
    def comments(self, request, slug=None):
        post = self.get_object()
        if request.method == 'GET':
            comments = post.comments.filter(is_active=True)
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        else:
            serializer = CommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(post=post)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='like')
    def like(self, request, slug=None):
        post = self.get_object()
        visitor_id = request.data.get('visitor_id') or request.META.get('REMOTE_ADDR') or str(post.id)
        # Toggle behaviour: create if not exists, else delete (unlike)
        like_qs = Like.objects.filter(post=post, visitor_id=visitor_id)
        if like_qs.exists():
            like_qs.delete()
            return Response({'likes_count': post.likes.count(), 'liked': False})
        else:
            Like.objects.create(post=post, visitor_id=visitor_id)
            return Response({'likes_count': post.likes.count(), 'liked': True})
