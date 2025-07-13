from django.apps import AppConfig
from green_power_backend.mongodb import MongoDBClient

class GridConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'grid'

    def ready(self):
        MongoDBClient.connect()
