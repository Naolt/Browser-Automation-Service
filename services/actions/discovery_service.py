import re
from typing import List, Optional
from playwright.async_api import Page
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ReservationMethod(Enum):
    GOOGLE_RESERVE = "google_reserve"  # "Reserve a table" button
    FIND_TABLE_BUTTON = "find_table_button"  # "Find a table" button (opens modal)
    FIND_TABLE_LINK = "find_table_link"  # "Find a table" direct link
    DIRECT_PROVIDER = "direct_provider"  # Direct link to provider
    NO_RESERVATION = "no_reservation"  # No reservation options found


class ProviderType(Enum):
    GOOGLE = "google"
    SEVENROOMS = "sevenrooms"
    OPENTABLE = "opentable"
    RESY = "resy"
    ZOMATO = "zomato"
    EAZYDINER = "eazydiner"
    UNKNOWN = "unknown"


class ReservationOption(BaseModel):
    """Represents a single reservation option found on the page."""
    method: ReservationMethod
    provider: Optional[ProviderType] = None
    element_text: str
    href: Optional[str] = None
    is_button: bool = False
    is_link: bool = False
    confidence: float = 0.0  # How confident we are this is a reservation option
    available_providers: Optional[List[ProviderType]] = None  # Providers available in modal (for Find Table buttons)


class ReservationDiscoveryResult(BaseModel):
    """Result of analyzing a Google Maps page for reservation options."""
    restaurant_name: str
    available_options: List[ReservationOption]
    recommended_option: Optional[ReservationOption] = None
    has_google_reserve: bool = False
    has_find_table: bool = False
    has_direct_providers: bool = False
    error_message: Optional[str] = None


class ReservationDiscoveryService:
    """Discovers and analyzes reservation options on Google Maps pages."""
    
    # Currently supported providers (only SevenRooms for now)
    SUPPORTED_PROVIDERS = {
        ProviderType.GOOGLE,
        ProviderType.OPENTABLE,
        ProviderType.SEVENROOMS,
    }
    
    @classmethod
    def add_supported_provider(cls, provider: ProviderType):
        """Add a new supported provider."""
        cls.SUPPORTED_PROVIDERS.add(provider)
        print(f"[ReservationDiscoveryService] Added {provider.value} as supported provider")
    
    @classmethod
    def remove_supported_provider(cls, provider: ProviderType):
        """Remove a supported provider."""
        cls.SUPPORTED_PROVIDERS.discard(provider)
        print(f"[ReservationDiscoveryService] Removed {provider.value} from supported providers")
    
    @classmethod
    def get_supported_providers(cls) -> set[ProviderType]:
        """Get the list of currently supported providers."""
        return cls.SUPPORTED_PROVIDERS.copy()
    
    # Common provider patterns
    PROVIDER_PATTERNS = {
        "sevenrooms": [
            r"sevenrooms\.com",
            r"seven\s*rooms",
            r"7rooms"
        ],
        "opentable": [
            r"opentable\.com",
            r"opentable\.ae",
            r"open\s*table"
        ],
    }
    
    @staticmethod
    async def discover_reservation_options(page: Page, restaurant_name: str) -> ReservationDiscoveryResult:
        """Analyze the Google Maps page and find all available reservation options."""

        print("########################################################")
        print(f"[ReservationDiscoveryService] Starting to discover reservation options...")
        print(f"[ReservationDiscoveryService] Restaurant name: {restaurant_name}")
        print("########################################################")
        
        try:
            # Wait for page to load
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)  # Allow dynamic content to load
            
            available_options = []
            
            # 1. Look for "Reserve a table" (Google's native reservation)
            google_reserve_option = await ReservationDiscoveryService._find_google_reserve(page)
            if google_reserve_option:
                available_options.append(google_reserve_option)
            
            # 2. Look for "Find a table" options
            find_table_options = await ReservationDiscoveryService._find_find_table_options(page)
            available_options.extend(find_table_options)
            
            # 3. Look for direct provider links
            direct_provider_options = await ReservationDiscoveryService._find_direct_provider_links(page)
            available_options.extend(direct_provider_options)
            
            # 4. Filter to only supported providers
            available_options = ReservationDiscoveryService._filter_supported_options(available_options)
            
            # 5. Determine recommended option
            recommended_option = ReservationDiscoveryService._select_recommended_option(available_options)

            print("########################################################")
            print(f"[ReservationDiscoveryService] Recommended option: {recommended_option}")
            print("########################################################")
            
            return ReservationDiscoveryResult(
                restaurant_name=restaurant_name,
                available_options=available_options,
                recommended_option=recommended_option,
                has_google_reserve=any(opt.method == ReservationMethod.GOOGLE_RESERVE for opt in available_options),
                has_find_table=any(opt.method in [ReservationMethod.FIND_TABLE_BUTTON, ReservationMethod.FIND_TABLE_LINK] for opt in available_options),
                has_direct_providers=any(opt.method == ReservationMethod.DIRECT_PROVIDER for opt in available_options)
            )
            
        except Exception as e:
            return ReservationDiscoveryResult(
                restaurant_name=restaurant_name,
                available_options=[],
                error_message=f"Error discovering reservation options: {str(e)}"
            )
    
    @staticmethod
    async def _find_google_reserve(page: Page) -> Optional[ReservationOption]:
        """Find the 'Reserve a table' button for Google's native reservation."""
        try:
            # Look for "Reserve a table" button/link
            reserve_button = page.locator('a:has-text("Reserve a table")')
            if await reserve_button.count() > 0:
                return ReservationOption(
                    method=ReservationMethod.GOOGLE_RESERVE,
                    provider=ProviderType.GOOGLE,
                    element_text="Reserve a table",
                    href=await reserve_button.get_attribute("href"),
                    is_link=True,
                    confidence=0.95
                )
            
            # Also check for button version
            reserve_button_alt = page.locator('button:has-text("Reserve a table")')
            if await reserve_button_alt.count() > 0:
                return ReservationOption(
                    method=ReservationMethod.GOOGLE_RESERVE,
                    provider=ProviderType.GOOGLE,
                    element_text="Reserve a table",
                    is_button=True,
                    confidence=0.95
                )
                
        except Exception as e:
            print(f"Error finding Google reserve option: {e}")
        
        return None
    
    @staticmethod
    async def _find_find_table_options(page: Page) -> List[ReservationOption]:
        """Find 'Find a table' buttons and links, and extract available providers from modal."""
        options = []
        
        try:
            # Look for "Find a table" elements
            find_table_elements = page.locator('text="Find a table"')
            
            for i in range(await find_table_elements.count()):
                element = find_table_elements.nth(i)
                
                # Get the parent element (button or link)
                parent = element.locator("xpath=ancestor::a | ancestor::button")
                
                if await parent.count() > 0:
                    tag_name = await parent.evaluate("el => el.tagName.toLowerCase()")
                    element_text = await element.inner_text()
                    href = await parent.get_attribute("href") if tag_name == "a" else None
                    
                    # For buttons, try to extract available providers from the modal
                    available_providers = []
                    if tag_name == "button":
                        available_providers = await ReservationDiscoveryService._extract_modal_providers(page, parent)
                    
                    option = ReservationOption(
                        method=ReservationMethod.FIND_TABLE_BUTTON if tag_name == "button" else ReservationMethod.FIND_TABLE_LINK,
                        element_text=element_text,
                        href=href,
                        is_button=(tag_name == "button"),
                        is_link=(tag_name == "a"),
                        confidence=0.9,
                        available_providers=available_providers if available_providers else None
                    )
                    options.append(option)
                    
        except Exception as e:
            print(f"Error finding Find a table options: {e}")
        
        return options
    
    @staticmethod
    async def _find_direct_provider_links(page: Page) -> List[ReservationOption]:
        """Find direct links to reservation providers."""
        options = []
        
        try:
            # Look for all links on the page
            all_links = page.locator('a[href]')
            
            for i in range(await all_links.count()):
                link = all_links.nth(i)
                href = await link.get_attribute("href")
                text = await link.inner_text()
                
                if href and text:
                    # Check if this looks like a reservation link
                    provider = ReservationDiscoveryService._identify_provider(href, text)
                    if provider and provider != ProviderType.UNKNOWN:
                        option = ReservationOption(
                            method=ReservationMethod.DIRECT_PROVIDER,
                            provider=provider,
                            element_text=text,
                            href=href,
                            is_link=True,
                            confidence=0.8
                        )
                        options.append(option)
                        
        except Exception as e:
            print(f"Error finding direct provider links: {e}")
        
        return options
    
    @staticmethod
    def _identify_provider(href: str, text: str) -> Optional[ProviderType]:
        """Identify which provider a link belongs to."""
        combined_text = f"{href} {text}".lower()
        
        for provider_name, patterns in ReservationDiscoveryService.PROVIDER_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return ProviderType(provider_name)
        
        return ProviderType.UNKNOWN
    
    @staticmethod
    def _filter_supported_options(options: List[ReservationOption]) -> List[ReservationOption]:
        """Filter options to only include supported providers."""
        supported_options = []
        unsupported_providers = set()
        
        for option in options:
            # For Find Table buttons, check if they have supported providers in the modal
            if option.method == ReservationMethod.FIND_TABLE_BUTTON and option.available_providers:
                # Check if any of the available providers in the modal are supported
                modal_supported = [p for p in option.available_providers if p in ReservationDiscoveryService.SUPPORTED_PROVIDERS]
                if modal_supported:
                    supported_options.append(option)
                    print(f"[ReservationDiscoveryService] Find Table button has supported providers: {[p.value for p in modal_supported]}")
                else:
                    unsupported_in_modal = [p.value for p in option.available_providers if p != ProviderType.UNKNOWN]
                    if unsupported_in_modal:
                        unsupported_providers.update(unsupported_in_modal)
            # For Google Reserve and Find Table links, we need to check if they lead to supported providers
            elif option.method in [ReservationMethod.GOOGLE_RESERVE, ReservationMethod.FIND_TABLE_LINK]:
                # These methods might lead to different providers, so we'll include them
                # The actual provider filtering will happen when the modal/page opens
                supported_options.append(option)
            elif option.provider and option.provider in ReservationDiscoveryService.SUPPORTED_PROVIDERS:
                # Direct provider option that we support
                supported_options.append(option)
            elif option.provider and option.provider != ProviderType.UNKNOWN:
                # Track unsupported providers for logging
                unsupported_providers.add(option.provider.value)
        
        if unsupported_providers:
            provider_list = ", ".join(sorted(unsupported_providers))
            print(f"[ReservationDiscoveryService] Filtered out unsupported providers: {provider_list}")
        
        print(f"[ReservationDiscoveryService] Found {len(supported_options)} supported options out of {len(options)} total options")
        return supported_options
    
    @staticmethod
    async def _extract_modal_providers(page: Page, find_table_button) -> List[ProviderType]:
        """Extract available providers from the Find a table modal."""
        providers = []
        
        try:
            # Click the Find a table button to open the modal
            await find_table_button.click()
            await page.wait_for_timeout(2000)  # Wait for modal to open
            
            # Look for SevenRooms links in the modal
            seven_rooms_links = page.locator('a[href*="sevenrooms.com"]')
            if await seven_rooms_links.count() > 0:
                providers.append(ProviderType.SEVENROOMS)
                print("[ReservationDiscoveryService] Found SevenRooms in Find Table modal")
                
            # Close the modal by clicking outside or pressing Escape
            try:
                # Try clicking outside the modal
                await page.click('body', position={'x': 0, 'y': 0})
            except:
                # If that fails, try pressing Escape
                await page.keyboard.press('Escape')
            
            await page.wait_for_timeout(500)  # Wait for modal to close
            
        except Exception as e:
            print(f"[ReservationDiscoveryService] Error extracting modal providers: {e}")
            # Try to close modal if it's still open
            try:
                await page.keyboard.press('Escape')
            except:
                pass
        
        return providers
    
    @staticmethod
    def _select_recommended_option(options: List[ReservationOption]) -> Optional[ReservationOption]:
        """Select the best reservation option based on priority."""
        if not options:
            return None
        
        # Priority order: Direct Provider (SevenRooms) > Find Table Button > Find Table Link > Google Reserve
        # We prioritize direct SevenRooms links over other methods
        priority_order = [
            ReservationMethod.GOOGLE_RESERVE,
            ReservationMethod.DIRECT_PROVIDER,  # Direct SevenRooms links first
            ReservationMethod.FIND_TABLE_LINK,
            ReservationMethod.FIND_TABLE_BUTTON,
        ]
        
        for method in priority_order:
            for option in options:
                if option.method == method:
                    # For direct provider, ensure it's a supported provider
                    if method == ReservationMethod.DIRECT_PROVIDER:
                        if option.provider and option.provider in ReservationDiscoveryService.SUPPORTED_PROVIDERS:
                            return option
                    else:
                        return option
        
        # Fallback to highest confidence option
        return max(options, key=lambda x: x.confidence) 