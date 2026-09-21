import asyncio

from django.core.management.base import BaseCommand

from background_workers.services.action_expiry import (
    get_action_expiry_settings,
    run_expiry_sweeps,
)


class Command(BaseCommand):
    help = "Move pending actions past their expiry to `expired`."

    def handle(self, *args, **options):
        asyncio.run(run_expiry_sweeps(get_action_expiry_settings()))
