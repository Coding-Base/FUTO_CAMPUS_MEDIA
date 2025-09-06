# blog/management/commands/migrate_images_to_cloudinary.py
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from blog.models import Post
import cloudinary
import cloudinary.uploader

class Command(BaseCommand):
    help = "Upload local / old post images to Cloudinary (folder futo_media/posts) and update Post.image to point to Cloudinary public_id."

    def handle(self, *args, **options):
        if not getattr(settings, "CLOUDINARY_STORAGE", None) and not getattr(settings, "CLOUDINARY_CLOUD_NAME", None):
            self.stdout.write(self.style.ERROR("Cloudinary credentials not configured in settings. Aborting."))
            return

        posts = Post.objects.all()
        total = posts.count()
        self.stdout.write(f"Found {total} posts. Processing...")

        for p in posts:
            img_field = getattr(p, "image", None)
            name = None
            try:
                name = getattr(img_field, "name", None)
            except Exception:
                name = None

            # Skip if already looks like a Cloudinary public_id or already uploaded (public_id rarely contains '/media' or '/post_images')
            if not name:
                self.stdout.write(f"- Post {p.pk}: no image, skipping.")
                continue

            # If name looks like an absolute url to Cloudinary, skip
            if name.startswith("http://") or name.startswith("https://") or name.startswith("futo_media/") or "res.cloudinary.com" in str(name):
                self.stdout.write(f"- Post {p.pk}: already absolute or cloud path ({name}), skipping.")
                continue

            # Construct local path
            local_path = os.path.join(settings.MEDIA_ROOT, name) if not os.path.isabs(name) else name
            if not os.path.exists(local_path):
                self.stdout.write(self.style.WARNING(f"- Post {p.pk}: local file not found at {local_path}. Skipping."))
                continue

            # Upload to Cloudinary
            try:
                result = cloudinary.uploader.upload(local_path, folder="futo_media/posts", resource_type="image", use_filename=True, unique_filename=True)
                public_id = result.get("public_id")
                secure_url = result.get("secure_url")
                if public_id:
                    # set the CloudinaryField value to public_id (CloudinaryField will resolve .url)
                    p.image = public_id
                    p.save(update_fields=["image"])
                    self.stdout.write(self.style.SUCCESS(f"- Post {p.pk}: uploaded -> {secure_url}"))
                else:
                    self.stdout.write(self.style.ERROR(f"- Post {p.pk}: upload returned no public_id: {result}"))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"- Post {p.pk}: upload failed: {exc}"))

        self.stdout.write(self.style.SUCCESS("Done."))
