from django.core.management.base import BaseCommand

from apps.ingestion.mqtt.subscriber import main


class Command(BaseCommand):
    help = "Run the MQTT subscriber for realtime ingestion."

    def handle(self, *args, **options):
        main()
