"""Bootstrap the (otherwise empty) university catalog.

    python manage.py add_school "Stanford University" stanford.edu cs.stanford.edu
"""

from django.core.management.base import BaseCommand

from courses.models import University


class Command(BaseCommand):
    help = "Add a university and the email domains that verify it."

    def add_arguments(self, parser):
        parser.add_argument("name", help="University display name.")
        parser.add_argument("domains", nargs="+", help="One or more email domains.")

    def handle(self, *args, **options):
        name = options["name"].strip()
        domains = [domain.strip().lower().lstrip("@") for domain in options["domains"]]

        university, created = University.objects.get_or_create(
            name=name, defaults={"email_domains": domains}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created {university.name} ({university.slug})."))
            return

        merged = sorted(set(university.email_domains) | set(domains))
        if merged != university.email_domains:
            university.email_domains = merged
            university.save(update_fields=["email_domains"])
            self.stdout.write(self.style.SUCCESS(f"Updated {university.name} domains: {merged}."))
        else:
            self.stdout.write(f"{university.name} already has those domains.")
