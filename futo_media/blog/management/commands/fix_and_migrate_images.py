import os
import urllib.parse
from django.core.management.base import BaseCommand
from django.conf import settings
from blog.models import Post
import cloudinary.uploader

class Command(BaseCommand):
    help = "Fix improperly stored image URLs and upload local media to Cloudinary"

    def handle(self, *args, **options):
        migrated = 0
        fixed = 0
        skipped = 0
        errors = 0

        for post in Post.objects.all():
            try:
                # get name and url safely
                name = getattr(post.image, 'name', '') or ''
                try:
                    url = getattr(post.image, 'url', '') or ''
                except Exception:
                    url = ''

                self.stdout.write(f"Post {post.pk}: name='{name}' url='{url[:120]}'")

                # 1) If url already absolute Cloudinary -> ensure stored as that url
                if url.startswith(('http://', 'https://')) and 'res.cloudinary.com' in url:
                    # stored as proper Cloudinary URL, make sure image field equals url
                    if name != url:
                        post.image = url
                        post.save(update_fields=['image'])
                        fixed += 1
                        self.stdout.write(self.style.SUCCESS(f" -> Fixed stored value to Cloudinary URL"))
                    else:
                        self.stdout.write(" -> Already Cloudinary, nothing to do")
                    continue

                # 2) If url contains encoded cloudinary e.g. 'https%3A' or '/media/https%3A' -> decode
                if 'https%3A' in url or 'http%253A' in url or '/media/https:' in url or '/media/http:' in url:
                    decoded = urllib.parse.unquote(url)
                    # remove accidental /media/ prefix(s)
                    # e.g. '/media/https://res.cloudinary.com/...' -> 'https://res.cloudinary.com/...'
                    decoded = decoded.lstrip('/')
                    if decoded.startswith('media/'):
                        decoded = decoded[len('media/'):]
                    # also remove any repeated 'media/http...' variants
                    if decoded.startswith('http://') or decoded.startswith('https://'):
                        post.image = decoded
                        post.save(update_fields=['image'])
                        migrated += 1
                        self.stdout.write(self.style.SUCCESS(f" -> Decoded & fixed to {decoded[:80]}"))
                        continue
                    # otherwise keep going to next checks

                # 3) If url starts with http but not Cloudinary (likely localhost media)
                if url.startswith(('http://', 'https://')):
                    # Try to detect local media path and upload the file
                    # look for '/media/' in the URL
                    idx = url.find('/media/')
                    if idx != -1:
                        rel = url[idx + len('/media/'):]  # e.g. post_images/...
                        local_path = os.path.join(settings.MEDIA_ROOT, rel)
                        if os.path.exists(local_path):
                            self.stdout.write(f" -> Found local file {local_path}, uploading to Cloudinary...")
                            res = cloudinary.uploader.upload(local_path, folder="futo_media/posts")
                            secure = res.get("secure_url")
                            if secure:
                                post.image = secure
                                post.save(update_fields=['image'])
                                migrated += 1
                                self.stdout.write(self.style.SUCCESS(f" -> Uploaded & set {secure[:80]}"))
                                continue
                            else:
                                errors += 1
                                self.stdout.write(self.style.ERROR(f" -> Upload returned no secure_url: {res}"))
                                continue
                        else:
                            # no local file found, but url is not Cloudinary: skip
                            skipped += 1
                            self.stdout.write(self.style.WARNING(f" -> Local file not found for URL, skipping"))
                            continue
                    else:
                        # URL is external but not cloudinary and no /media seg -> skip
                        skipped += 1
                        self.stdout.write(self.style.WARNING(" -> External non-cloudinary URL, skipping"))
                        continue

                # 4) If url is empty but name present (relative path stored) -> upload file
                if name:
                    # If name is already an absolute http stored in name (rare) decode
                    if name.startswith('http://') or name.startswith('https://'):
                        if 'res.cloudinary.com' in name:
                            post.image = name
                            post.save(update_fields=['image'])
                            fixed += 1
                            self.stdout.write(self.style.SUCCESS(" -> Name was Cloudinary URL, fixed"))
                            continue
                        else:
                            # name is some other absolute path; try to extract local file after /media/
                            idx = name.find('/media/')
                            if idx != -1:
                                rel = name[idx + len('/media/'):]
                                local_path = os.path.join(settings.MEDIA_ROOT, rel)
                            else:
                                local_path = os.path.join(settings.MEDIA_ROOT, name)
                    else:
                        local_path = os.path.join(settings.MEDIA_ROOT, name)

                    if os.path.exists(local_path):
                        self.stdout.write(f" -> Uploading local file {local_path} to Cloudinary...")
                        try:
                            res = cloudinary.uploader.upload(local_path, folder="futo_media/posts")
                            secure = res.get("secure_url")
                            if secure:
                                post.image = secure
                                post.save(update_fields=['image'])
                                migrated += 1
                                self.stdout.write(self.style.SUCCESS(f" -> Uploaded & set {secure[:80]}"))
                                continue
                            else:
                                errors += 1
                                self.stdout.write(self.style.ERROR(f" -> Upload failed, no secure_url returned: {res}"))
                                continue
                        except Exception as e:
                            errors += 1
                            self.stdout.write(self.style.ERROR(f" -> Upload exception: {e}"))
                            continue
                    else:
                        skipped += 1
                        self.stdout.write(self.style.WARNING(f" -> Local file not found at {local_path}, skipping"))
                        continue

                # 5) Nothing we can do
                skipped += 1
                self.stdout.write(" -> Nothing to do (no name/url usable)")

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(f"Post {post.pk}: unexpected error: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done: migrated={migrated}, fixed={fixed}, skipped={skipped}, errors={errors}"))
