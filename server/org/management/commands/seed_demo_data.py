from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from org.models import Website


class Command(BaseCommand):
    help = (
        "Seed a demo superuser, organization, and recurring crawl schedules. "
        "Safe to run more than once - every step is get-or-create."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--password", default="admin")
        parser.add_argument("--email", default="admin@example.com")
        parser.add_argument("--org-name", default="OSAT")
        parser.add_argument("--org-url", default="https://example.com")

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username=options["username"],
            defaults={
                "email": options["email"],
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            user.set_password(options["password"])
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created superuser '{user.username}'"))
        else:
            self.stdout.write(f"Superuser '{user.username}' already exists")

        website, created = Website.objects.get_or_create(
            slug=options["org_name"].lower(),
            defaults={"name": options["org_name"], "url": options["org_url"]},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created organization '{website.name}'"))
        else:
            self.stdout.write(f"Organization '{website.name}' already exists")

        website.get_or_add_user(user)

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0", hour="0", day_of_week="*", day_of_month="*", month_of_year="*",
            defaults={"timezone": "UTC"},
        )
        for name, task in (
            ("Lighthouse Crawler", "lighthouse.tasks.lighthouse_crawler"),
            ("Security Crawler", "security.tasks.security_crawler"),
        ):
            _, created = PeriodicTask.objects.get_or_create(
                name=name, defaults={"task": task, "crontab": schedule},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Scheduled '{name}'"))
            else:
                self.stdout.write(f"'{name}' schedule already exists")

        self.stdout.write(self.style.SUCCESS("Done."))
