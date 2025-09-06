# blog/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Q
from django.conf import settings

from .models import Post, Comment, Like
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateSerializer,
    CommentSerializer,
)

# Try to import cloudinary.uploader — it's optional (we handle absence)
try:
    import cloudinary.uploader
    _CLOUDINARY_AVAILABLE = True
except Exception:
    cloudinary = None
    _CLOUDINARY_AVAILABLE = False


class PostViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for posts (image uploads via multipart).
    - list/retrieve return annotated likes_count and comments_count
    - create/update support either a file upload (image) OR an 'image_url' (remote URL).
      When 'image_url' is provided and Cloudinary is configured, the backend uploads
      that remote image to Cloudinary into folder "futo_media/posts" and attaches
      the Cloudinary public_id to the Post so `.image.url` will return the
      canonical HTTPS CDN URL.
    - comments action supports threaded replies via 'parent' field and validates parent belongs to the same post.
    """
    queryset = Post.objects.all().order_by("-created_at")
    lookup_field = "slug"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        # annotate counts to avoid N+1 on serializer side
        qs = (
            Post.objects.all()
            .order_by("-created_at")
            .annotate(
                likes_count=Count("likes", distinct=True),
                comments_count=Count("comments", filter=Q(comments__is_active=True), distinct=True),
            )
        )
        return qs

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

    def _upload_remote_to_cloudinary(self, url):
        """
        Uploads an external image URL to Cloudinary folder 'futo_media/posts'.
        Returns the Cloudinary public_id (string) on success, or raises exception.
        """
        if not _CLOUDINARY_AVAILABLE:
            raise RuntimeError("Cloudinary is not available on the server (missing package/config).")

        # Basic upload options: place into folder futo_media/posts, preserve resource_type=image
        result = cloudinary.uploader.upload(
            url,
            folder="futo_media/posts",
            resource_type="image",
            use_filename=True,
            unique_filename=True,
        )
        # result should contain 'public_id' and 'secure_url'
        public_id = result.get("public_id")
        if not public_id:
            raise RuntimeError(f"Cloudinary upload did not return public_id: {result}")
        return public_id

    def create(self, request, *args, **kwargs):
        """
        Accepts file upload via `image` or a remote `image_url` string.
        For image_url, uploads to Cloudinary (if available) then creates Post and attaches the Cloudinary public id.
        """
        data = request.data.copy()

        image_url = data.get("image_url")
        # If image_url is provided (and no file was uploaded), try to upload it to Cloudinary
        temp_public_id = None
        if image_url:
            if not _CLOUDINARY_AVAILABLE:
                return Response(
                    {"image_url": "Cloudinary not configured on server. Provide a file upload instead."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                temp_public_id = self._upload_remote_to_cloudinary(image_url)
            except Exception as exc:
                return Response({"image_url": f"Failed to upload remote image: {str(exc)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Remove image_url so serializer (which expects ImageField) doesn't choke
        if "image_url" in data:
            data.pop("image_url")

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # if we uploaded to Cloudinary, set the CloudinaryField value to the public_id
        if temp_public_id:
            # assign public_id (CloudinaryField stores public_id as the model value)
            instance.image = temp_public_id
            instance.save(update_fields=["image"])

        # Return detail serializer so front-end receives image_url & top_level_comments etc.
        out_serializer = PostDetailSerializer(instance, context=self.get_serializer_context())
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Handles update; supports remote image_url (uploads to Cloudinary) or file replacement.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data.copy()

        image_url = data.get("image_url")
        temp_public_id = None
        if image_url:
            if not _CLOUDINARY_AVAILABLE:
                return Response(
                    {"image_url": "Cloudinary not configured on server. Provide a file upload instead."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                temp_public_id = self._upload_remote_to_cloudinary(image_url)
            except Exception as exc:
                return Response({"image_url": f"Failed to upload remote image: {str(exc)}"}, status=status.HTTP_400_BAD_REQUEST)

        if "image_url" in data:
            data.pop("image_url")

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        if temp_public_id:
            instance.image = temp_public_id
            instance.save(update_fields=["image"])

        out_serializer = PostDetailSerializer(instance, context=self.get_serializer_context())
        return Response(out_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["GET", "POST"], url_path="comments")
    def comments(self, request, slug=None):
        post = self.get_object()
        if request.method == "GET":
            # top-level comments returned (replies nested by serializer)
            comments_qs = post.comments.filter(parent__isnull=True, is_active=True).order_by("created_at")
            serializer = CommentSerializer(comments_qs, many=True, context=self.get_serializer_context())
            return Response(serializer.data)

        # POST: create comment (or reply if parent provided)
        serializer = CommentSerializer(data=request.data, context=self.get_serializer_context())
        if serializer.is_valid():
            parent = serializer.validated_data.get("parent")
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
            likes_count = post.likes.count()
            return Response({"likes_count": likes_count, "liked": False})
        else:
            Like.objects.create(post=post, visitor_id=visitor_id)
            likes_count = post.likes.count()
            return Response({"likes_count": likes_count, "liked": True})
