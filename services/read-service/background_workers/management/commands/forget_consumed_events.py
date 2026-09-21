import sys

from data_read_core.shared.kafka_dedupe import KafkaConsumedEvent
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Forget that a consumer group has processed the given events, so a replay "
        "of them is applied instead of rejected by dedupe. Reads event ids from "
        "stdin, one per line. Only events this group SKIPPED should be listed: "
        "forgetting one it actually applied lets a replay apply it twice."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--group-id",
            default=settings.KAFKA["READ_GROUP_ID"],
            help=f"Consumer group to forget for (default: {settings.KAFKA['READ_GROUP_ID']}).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be forgotten and delete nothing.",
        )

    def handle(self, *args, **options) -> None:
        event_ids = [line.strip() for line in sys.stdin if line.strip()]
        if not event_ids:
            raise CommandError("No event ids on stdin.")

        group_id = options["group_id"]
        known = KafkaConsumedEvent.objects.filter(
            consumer_group=group_id,
            event_id__in=event_ids,
        )
        matched = known.count()

        if options["dry_run"]:
            self.stdout.write(f"would forget {matched} of {len(event_ids)} event(s) for {group_id}")

            return

        known.delete()
        self.stdout.write(
            self.style.SUCCESS(f"forgot {matched} of {len(event_ids)} event(s) for {group_id}")
        )
