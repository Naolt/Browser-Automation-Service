from datetime import datetime, timedelta
from typing import TypedDict
from dateutil import parser
import phonenumbers

# Reservation error messages
class ReservationErrorDict(TypedDict):
    invalid_page: str
    popup_missing_book: str
    book_button_disabled: str
    confirmation_missing: str
    done_button_disabled: str
    time_not_available: str
    date_not_available: str
    party_size_not_available: str
    unexpected_error: str
    invalid_phone_number: str
    reservation_system_not_supported: str
    reservation_system_not_available: str
    credit_card_info_required: str


class ReservationSuccessDict(TypedDict):
    party_size_selected: str
    date_selected: str
    time_selected: str


class PhoneParserResult(TypedDict):
    iso_country_code: None | str
    country_prefix: None | str
    national_number: None | str
    error: None | str


RESERVATION_ERRORS: ReservationErrorDict = {
    "invalid_page": "Invalid page. URL must start with the expected reservation prefix",
    "popup_missing_book": "Book button not found after Continue",
    "book_button_disabled": "Book button is disabled",
    "confirmation_missing": "Booking confirmation not found",
    "done_button_disabled": "Done button is disabled",
    "time_not_available": "Time not available",
    "date_not_available": "Date not available",
    "party_size_not_available": "Party size not available",
    "unexpected_error": "Unexpected error during reservation",
    "invalid_phone_number": "Phone number is invalid",
    "reservation_system_not_supported": "Reservation system not supported",
    "reservation_system_not_available": "Reservation system is not available",
    "credit_card_info_required": "Credit card info is required",
    "wrong_page": "Wrong page, please make sure it's google reservation page with prefix like:{self.url_prefixes}",
}


RESERVATION_SUCCESSES: ReservationSuccessDict = {
    "party_size_selected": "Party size selected successfully",
    "date_selected": "Date selected successfully",
    "time_selected": "Time selected successfully",
    "reservation_complete": "Reservation complete and booked. Here are the reservation details: Party size: {party_size}, Date: {date}, Time: {time_24h}",
}



PROVIDER_URL_PREFIXES = {
    "seven_rooms": "https://www.sevenrooms.com/",
    "google": "https://www.google.com/maps/reserve",
}

def build_reservation_failure_message(key_or_custom: str) -> str:
    """
    Returns a strong, standardized failure message for reservation errors.
    Accepts either a predefined key or a custom string.
    """
    message = RESERVATION_ERRORS.get(key_or_custom, key_or_custom)
    return f"❌ [FATAL] Reservation failed: {message}. Do not retry."

def build_reservation_success_message(key_or_custom: str) -> str:
    """
    Returns a strong, standardized success message for reservation actions.
    Accepts either a predefined key or a custom string.
    """
    message = RESERVATION_SUCCESSES.get(key_or_custom, key_or_custom)
    return f"✅ [SUCCESS] {message}"

# Helper to round up to the next :00 or :30
def round_up_to_next_half_hour(dt: datetime) -> datetime:
    minute = dt.minute
    if minute == 0 or minute == 30:
        return dt.replace(second=0, microsecond=0)
    elif minute < 30:
        return dt.replace(minute=30, second=0, microsecond=0)
    else:
        return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

# Formats datetime to HH:MM (24-hour format)
def to_time_string(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def parse_phone_number(phone_str: str) -> PhoneParserResult:
    """
    Parse phone number and return a dictionary with:
      - iso_country_code: e.g., 'AX'
      - country_prefix: e.g., '+358'
      - national_number: e.g., '401234567'
      - error: error message if parsing fails, else None
    """
    result = {
        "iso_country_code": None,
        "country_prefix": None,
        "national_number": None,
        "error": None,
    }
    try:
        phone_str = phone_str.strip()
        if not phone_str.startswith('+'):
            result["error"] = f"No country code found in phone number: {phone_str}"
            return result

        parsed = phonenumbers.parse(phone_str)
        result["iso_country_code"] = phonenumbers.region_code_for_number(parsed)
        result["country_prefix"] = f"+{parsed.country_code}"
        result["national_number"] = str(parsed.national_number)
        return result

    except phonenumbers.NumberParseException as e:
        result["error"] = f"Failed to parse phone number '{phone_str}': {str(e)}"
        return result
    except Exception as e:
        result["error"] = f"Unexpected error parsing phone number '{phone_str}': {str(e)}"
        return result 
    

def parse_date(date_str: str) -> datetime:
    """
    Parse date string in various formats including:
    - "2025-07-22" (YYYY-MM-DD)
    - "July 28, 2025" (human readable)
    - "28/07/2025" (DD/MM/YYYY)
    """
    print(f"Parsing date: {date_str}")
    try:
        # First try the expected format
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        try:
            # Use dateutil.parser for flexible parsing
            return parser.parse(date_str)
        except Exception as e:
            raise ValueError(f"Could not parse date '{date_str}': {str(e)}")

