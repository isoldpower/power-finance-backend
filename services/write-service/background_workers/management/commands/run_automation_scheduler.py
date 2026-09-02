import asyncio

from django.core.management.base import BaseCommand

from background_workers.services.automation_schedule import (
    get_automation_schedule_settings,
    run_schedule_sweeps,
)


class Command(BaseCommand):
    help = "Run user-authored rules whose trigger is a schedule."

    def handle(self, *args, **options):
        asyncio.run(run_schedule_sweeps(get_automation_schedule_settings()))
