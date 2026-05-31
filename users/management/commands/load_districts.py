import json
from pathlib import Path

from django.core.management.base import BaseCommand

from users.models import District

DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "disctrict.json"


class Command(BaseCommand):
    help = "Load Kerala districts from data/disctrict.json into the database"

    def handle(self, *args, **options):
        data = json.loads(DATA_FILE.read_text())
        created = updated = 0
        for entry in data["districts"]:
            _, was_created = District.objects.get_or_create(name=entry["name"])
            if was_created:
                created += 1
            else:
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"Done — {created} created, {updated} already existed.")
        )
