"""
Management command to compile translation strings.

Usage: python manage.py compilemessages
"""

from django.core.management.commands.compilemessages import Command as BaseCommand


class Command(BaseCommand):
    help = "Compile message files to .mo format (with custom configuration)"

    def handle(self, *args, **options):
        super().handle(*args, **options)
        self.stdout.write(
            self.style.SUCCESS(
                "Translation files compiled successfully. "
                "Available languages: English, العربية"
            )
        )
