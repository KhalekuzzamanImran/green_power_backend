from django.apps import AppConfig
from config.mongodb import MongoDBClient

class GridConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.grid'

    def ready(self):
        MongoDBClient.connect()
