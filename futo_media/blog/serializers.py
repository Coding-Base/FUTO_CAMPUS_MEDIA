# blog/serializers.py
from rest_framework import serializers
from .models import Post, Comment
from urllib.parse import unquote, urlsplit, urlunsplit

def _normalize_candidate(candidate: str) -> str | None:
    """
    Normalize a candidate string that may be:
    - percent-encoded (https%3A%2F%2F... or https%3A/...),
    - prefixed with '/media/' or 'media/',
    - containing an embedded http link like 'http://host/media/https://res.cloudinary.com/...'
    Returns a cleaned https:// or http:// URL string or None.
    """
    if not candidate:
        return None

    v = candidate

    # Repeatedly unquote a few times (handles double-encoded values)
    for _ in range(3):
        if "%" in v:
            try:
                new_v = unquote(v)
            except Exception:
                break
            if new_v == v:
                break
            v = new_v
        else:
            break

    # strip lead slashes/spaces
    v = v.lstrip().lstrip("/")

    # strip leading 'media/' if present
    if v.startswith("media/"):
        v = v[len("media/"):]

    # Some broken variants become 'https:/res.cloudinary.com/...' (single slash after :)
    # fix common malformed 'http:/' or 'https:/'
    if v.startswith("http:/") and not v.startswith("http://"):
        v = "http://" + v[len("http:/") :]
    if v.startswith("https:/") and not v.startswith("https://"):
        v = "https://" + v[len("https:/") :]

    # If still doesn't start with scheme but contains 'http' later, take last 'http' substring
    if not v.startswith(("http://", "https://")) and "http" in v:
        idx = v.rfind("http")
        if idx != -1:
            v = v[idx:]

    # If now looks like absolute URL, ensure scheme and return
    if v.startswith("http://") or v.startswith("https://"):
        # Prefer https scheme if possible (Cloudinary uses https)
        parts = urlsplit(v)
        scheme = parts.scheme
        if scheme == "http":
            # upgrade to https where possible (safe default)
            scheme = "https"
            v = urlunsplit((scheme, parts.netloc, parts.path, parts.query, parts.fragment))
        return v

    return None


class CommentSerializer(serializers.ModelSerializer):
    # supports threaded replies if your model has parent/replies fields
    parent = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), allow_null=True, required=False)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        # keep fields you previously used
        fields = ["id", "post", "parent", "name", "email", "content", "created_at", "is_active", "replies"]
        read_only_fields = ["id", "created_at", "post", "replies"]

    def get_replies(self, obj):
        # only active replies, ordered by created_at (matches your UI)
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
        """
        Return a cleaned absolute URL for an image:
         - prefer obj.image.name when it already contains an absolute URL
         - otherwise try obj.image.url (storage provided)
         - attempt to decode malformed/encoded values and return https://... when possible
         - fallback: build absolute URI from request when relative paths exist
        """
        # 1) If image.name stores a full Cloudinary URL already, prefer it.
        raw_name = getattr(obj.image, "name", "") or ""
        if raw_name.startswith("http://") or raw_name.startswith("https://"):
            # return as-is (already canonical). If you want to enforce https, you could rewrite here.
            return raw_name

        # 2) Try storage-provided .url
        try:
            raw_url = getattr(obj.image, "url", "") or ""
        except Exception:
            raw_url = ""

        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            return raw_url

        # 3) Try normalized candidates (name first, then url)
        decoded = _normalize_candidate(raw_name) or _normalize_candidate(raw_url)
        if decoded:
            return decoded

        # 4) Fallback to request-built absolute URI for relative/local paths
        request = self.context.get("request")
        if raw_url:
            try:
                return request.build_absolute_uri(raw_url) if request else raw_url
            except Exception:
                return raw_url
        if raw_name:
            path = raw_name if raw_name.startswith("/") else f"/{raw_name}"
            try:
                return request.build_absolute_uri(path) if request else path
            except Exception:
                return path

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
