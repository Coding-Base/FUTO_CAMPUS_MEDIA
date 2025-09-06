# blog/serializers.py
from urllib.parse import unquote, urlsplit, urlunsplit
from rest_framework import serializers
from .models import Post, Comment

def _normalize_candidate(candidate: str) -> str | None:
    """
    Normalize candidate strings into a sensible absolute URL if possible.

    Handles:
      - percent-encoded values (single or double encoded)
      - values prefixed with 'media/' or '/media/'
      - embedded/duplicated http fragments (take last 'http' occurrence)
      - malformed 'https:/' -> 'https://'
      - Cloudinary special case: ensure '/image/upload' exists in the path
    """
    if not candidate:
        return None

    v = candidate.strip()

    # If value contains multiple http(s) occurrences (duplication), keep last one
    if v.count("http") > 1:
        idx = v.rfind("http")
        v = v[idx:]

    # Repeatedly unquote a few times to handle double-encoded strings
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

    # trim leading slashes/spaces
    v = v.lstrip().lstrip("/")

    # strip leading media/ if present
    if v.startswith("media/"):
        v = v[len("media/"):]

    # Fix common malformed single-slash scheme patterns: 'http:/' or 'https:/'
    if v.startswith("http:/") and not v.startswith("http://"):
        v = "http://" + v[len("http:/") :]
    if v.startswith("https:/") and not v.startswith("https://"):
        v = "https://" + v[len("https:/") :]

    # If still doesn't start with scheme but contains 'http' later, take last 'http' substring
    if not v.startswith(("http://", "https://")) and "http" in v:
        idx = v.rfind("http")
        if idx != -1:
            v = v[idx:]

    # Now try to parse as URL; if it looks absolute, possibly repair cloudinary path
    if v.startswith("http://") or v.startswith("https://"):
        # Parse
        parts = urlsplit(v)
        scheme, netloc, path, query, frag = parts.scheme, parts.netloc, parts.path, parts.query, parts.fragment

        # upgrade http -> https by default (Cloudinary works on https)
        if scheme == "http":
            scheme = "https"

        # if it's a cloudinary URL but missing '/image/upload' insert it after cloud name
        # e.g. https://res.cloudinary.com/<cloud_name>/post_images/... -> insert /image/upload
        host = netloc.lower()
        if "res.cloudinary.com" in host:
            # Normalize path duplicates (if path contains another 'http' fragment, keep the last)
            if "http" in path:
                idx = path.rfind("http")
                path = path[idx:]

            # If /image/upload is missing, attempt to insert it:
            if "/image/upload" not in path:
                # split path into components: ['', cloud_name, rest...]
                comps = path.split("/")
                # ensure we have at least cloud_name in comps[1]
                if len(comps) > 1 and comps[1]:
                    cloud_name = comps[1]
                    rest = "/".join(comps[2:]) if len(comps) > 2 else ""
                    # build new path ensuring no duplicate slashes
                    if rest:
                        new_path = f"/{cloud_name}/image/upload/{rest}"
                    else:
                        new_path = f"/{cloud_name}/image/upload"
                    path = new_path

        # rebuild URL
        try:
            fixed = urlunsplit((scheme, netloc, path, query, frag))
        except Exception:
            fixed = v

        return fixed

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
        """
        Prefer canonical absolute image URLs:

        Order:
          1) obj.image.name if it already contains an absolute URL (some rows store full URLs)
          2) obj.image.url from storage (most correct when Cloudinary storage is active)
          3) try normalized decoding for name/url
          4) fallback: build absolute URI using request for relative values
        """
        # 1) raw .name might already be an absolute URL
        raw_name = getattr(obj.image, "name", "") or ""
        if raw_name.startswith("http://") or raw_name.startswith("https://"):
            # If it's a Cloudinary hostname missing '/image/upload' we'll try to normalize
            normalized = _normalize_candidate(raw_name)
            if normalized:
                return normalized
            return raw_name

        # 2) storage-provided .url (may throw)
        try:
            raw_url = getattr(obj.image, "url", "") or ""
        except Exception:
            raw_url = ""

        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            normalized = _normalize_candidate(raw_url)
            if normalized:
                return normalized
            return raw_url

        # 3) try to decode/normalize either name or url (handles encoded or malformed)
        decoded = _normalize_candidate(raw_name) or _normalize_candidate(raw_url)
        if decoded:
            return decoded

        # 4) fallback: build absolute URI from request for relative paths
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
