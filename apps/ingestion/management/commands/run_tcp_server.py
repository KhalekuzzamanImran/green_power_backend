from django.core.management.base import BaseCommand

from apps.ingestion.tcp_server import main


class Command(BaseCommand):
    help = "Run the TCP socket server for solar device ingestion."

    def handle(self, *args, **options):
        main()
