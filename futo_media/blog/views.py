# blog/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Post, Comment, Like
from .serializers import PostListSerializer, PostDetailSerializer, PostCreateSerializer, CommentSerializer

class PostViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for posts (image uploads via multipart).
    Comments action supports threaded replies via 'parent' field.
    """
    queryset = Post.objects.all().order_by("-created_at")
    lookup_field = "slug"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        return PostCreateSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    @action(detail=True, methods=["GET", "POST"], url_path="comments")
    def comments(self, request, slug=None):
        post = self.get_object()
        if request.method == "GET":
            # only top-level comments; replies are nested in serializer
            comments = post.comments.filter(parent__isnull=True, is_active=True).order_by("created_at")
            serializer = CommentSerializer(comments, many=True, context=self.get_serializer_context())
            return Response(serializer.data)
        else:
            # create comment or reply
            serializer = CommentSerializer(data=request.data, context=self.get_serializer_context())
            if serializer.is_valid():
                parent = serializer.validated_data.get("parent", None)
                # validate parent belongs to same post
                if parent is not None and parent.post_id != post.id:
                    return Response({"parent": "Parent comment does not belong to this post."}, status=status.HTTP_400_BAD_REQUEST)
                serializer.save(post=post)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["POST"], url_path="like")
    def like(self, request, slug=None):
        post = self.get_object()
        visitor_id = request.data.get("visitor_id") or request.META.get("REMOTE_ADDR") or str(post.id)
        like_qs = Like.objects.filter(post=post, visitor_id=visitor_id)
        if like_qs.exists():
            like_qs.delete()
            return Response({"likes_count": post.likes.count(), "liked": False})
        else:
            Like.objects.create(post=post, visitor_id=visitor_id)
            return Response({"likes_count": post.likes.count(), "liked": True})
