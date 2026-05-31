import json
from pathlib import Path

from django.core.management.base import BaseCommand

from users.models import Department, Minister


class Command(BaseCommand):
    help = "Load ministers and departments from data/ministers.json"

    def handle(self, *args, **options):
        data_path = Path(__file__).resolve().parents[3] / "data" / "ministers.json"
        with open(data_path) as f:
            ministers_data = json.load(f)

        created_ministers = 0
        created_depts = 0
        skipped = 0

        for entry in ministers_data:
            name = entry["name"]
            departments = entry["departments"]
            designation = entry.get("designation", "")
            primary_dept = departments[0] if departments else ""

            minister, m_created = Minister.objects.get_or_create(
                name=name,
                defaults={
                    "dept": primary_dept,
                    "constituency": "",
                },
            )
            if m_created:
                created_ministers += 1
            else:
                skipped += 1

            for dept_name in departments:
                dept, d_created = Department.objects.get_or_create(
                    name=dept_name,
                    defaults={"minister": minister},
                )
                if d_created:
                    created_depts += 1
                elif dept.minister != minister:
                    dept.minister = minister
                    dept.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — {created_ministers} ministers created, {skipped} skipped, "
                f"{created_depts} departments created."
            )
        )
