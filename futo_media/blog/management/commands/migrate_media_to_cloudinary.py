# blog/management/commands/fix_encoded_images.py
import os
from urllib.parse import unquote
from django.core.management.base import BaseCommand
from django.conf import settings
from blog.models import Post

def _try_decode(value):
    if not value:
        return None
    decoded = value
    for _ in range(2):
        if "%" in decoded:
            decoded = unquote(decoded)
        else:
            break
    decoded = decoded.lstrip("/")
    if decoded.startswith("media/"):
        decoded = decoded[len("media/"):]
    if decoded.startswith("http://") or decoded.startswith("https://"):
        return decoded
    return None

class Command(BaseCommand):
    help = "Fix encoded / prefixed image values in Post.image"

    def handle(self, *args, **options):
        fixed = 0
        skipped = 0
        errors = 0
        for p in Post.objects.all():
            try:
                try:
                    url = getattr(p.image, "url", "") or ""
                except Exception:
                    url = ""
                name = getattr(p.image, "name", "") or ""
                decoded = _try_decode(url) or _try_decode(name)
                if decoded:
                    p.image = decoded
                    p.save(update_fields=["image"])
                    self.stdout.write(self.style.SUCCESS(f"Fixed Post {p.pk} -> {decoded[:120]}"))
                    fixed += 1
                    continue
                self.stdout.write(f"Post {p.pk}: nothing to fix")
                skipped += 1
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Post {p.pk}: error {e}"))
        self.stdout.write(self.style.SUCCESS(f"Done. fixed={fixed}, skipped={skipped}, errors={errors}"))
