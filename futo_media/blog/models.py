# blog/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField 

User = get_user_model()


def generate_unique_slug(instance, value):
    base = slugify(value)[:200]
    slug = base
    ModelClass = instance.__class__
    counter = 1
    while ModelClass.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


class Post(models.Model):
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    # Increased max_length so Cloudinary URLs won’t be truncated
    image = CloudinaryField(
        "image",
        folder="futo_media/posts",
        resource_type="image",
        blank=True,
        null=True,
        max_length=500
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    # NOTE: these properties now accept annotated values from queryset.
    # Django will be able to set .likes_count and .comments_count when using annotate().
    @property
    def likes_count(self):
        # Prefer an annotated value stored on the instance (set by queryset annotation).
        if "likes_count" in self.__dict__:
            try:
                return int(self.__dict__["likes_count"])
            except Exception:
                pass
        # fallback to counting related likes
        return self.likes.count()

    @likes_count.setter
    def likes_count(self, value):
        # allow Django to set annotated value
        try:
            self.__dict__["likes_count"] = int(value)
        except Exception:
            self.__dict__["likes_count"] = value

    @property
    def comments_count(self):
        if "comments_count" in self.__dict__:
            try:
                return int(self.__dict__["comments_count"])
            except Exception:
                pass
        # fallback to counting active comments
        return self.comments.filter(is_active=True).count()

    @comments_count.setter
    def comments_count(self, value):
        try:
            self.__dict__["comments_count"] = int(value)
        except Exception:
            self.__dict__["comments_count"] = value


@receiver(pre_save, sender=Post)
def ensure_slug(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = generate_unique_slug(instance, instance.title)


class Comment(models.Model):
    post = models.ForeignKey(Post, related_name="comments", on_delete=models.CASCADE)
    parent = models.ForeignKey("self", related_name="replies", null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.name}"


class Like(models.Model):
    post = models.ForeignKey(Post, related_name="likes", on_delete=models.CASCADE)
    visitor_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "visitor_id")

    def __str__(self):
        return f"Like {self.post_id} by {self.visitor_id}"

