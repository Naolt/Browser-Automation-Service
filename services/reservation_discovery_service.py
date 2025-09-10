from typing import List, Optional
from playwright.async_api import Page

from models.reservation_models import ProviderType, ReservationMethod, ReservationOption
from services.actions.provider.base_provider import BaseReservationProvider

class ReservationDiscoveryService:
    def __init__(self, providers: List[BaseReservationProvider]):
        self.providers = providers

    async def discover_all_options(self, page: Page) -> List[ReservationOption]:
        options = []
        for provider in self.providers:
            try:
                option = await provider.discover_reservation_option(page)
                if option:
                    options.append(option)
            except Exception as e:
                print(f"[ReservationDiscoveryService] Error discovering with {provider.provider_type}: {e}")
        return options


    def select_best_option(self,options: List[ReservationOption]) -> Optional[ReservationOption]:
        priority_order = [
            (ProviderType.GOOGLE),
            (ProviderType.SEVENROOMS),
            (ProviderType.OPENTABLE),
        ]

        for provider_type in priority_order:
            for option in options:
                if option.provider == provider_type:
                    return option

        # Fallback: just return the first available option
        return options[0] if options else None