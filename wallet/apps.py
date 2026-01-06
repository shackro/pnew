from django.apps import AppConfig

def ready(self):
    import wallet.signals


class WalletConfig(AppConfig):
    name = 'wallet'
    