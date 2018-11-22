from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class StarkConfig(AppConfig):
    name = 'stark'

    # 这个ready方法是固定不变的
    def ready(self):
        autodiscover_modules('stark')
