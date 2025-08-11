from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline

def guard_cabin_change_payment_requirement(history: ChatHistory, api: I_Airline, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], payment_id: str):
    """
    Policy to check: ToolX can be used to modify a reservation's cabin class. Ensure a uniform cabin class change across all flights within the reservation. Make sure the user pays the fare difference between the current cabin class and the new cabin class for the entire reservation as partial changes are disallowed.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        reservation_id: The reservation ID, such as 'ZFA04Y'.
        cabin: The cabin class of the reservation
        flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    """
    # 1. Get reservation details
    reservation = api.get_reservation_details(reservation_id)
    original_cabin = reservation.cabin
    original_flights = reservation.flights
    
    # 2. Ensure all flight segments are included in the update
    # Each ReservationFlight must be present in flights
    original_flight_keys = set((f.flight_number, f.date) for f in original_flights)
    update_flight_keys = set()
    for f in flights:
        if isinstance(f, dict):
            flight_number = f.get('flight_number')
            date = f.get('date')
        else:
            flight_number = f.flight_number
            date = f.date
        update_flight_keys.add((flight_number, date))
    if original_flight_keys != update_flight_keys:
        raise PolicyViolationException("All flight segments in the reservation must be included in the cabin change.")

    # 3. Ensure uniform cabin class across all flights
    # The requested cabin must be the same for all flights
    # (This is enforced by the API signature, but we check anyway)
    if not all(cabin in ['business', 'economy', 'basic_economy'] for _ in flights):
        raise PolicyViolationException("Cabin class must be uniform across all flights.")

    # 4. Calculate total fare difference for the entire reservation
    total_new_price = 0
    total_old_price = 0
    for f in flights:
        flight_number = f['flight_number'] if isinstance(f, dict) else f.flight_number
        date = f['date'] if isinstance(f, dict) else f.date
        flight_instance = api.get_flight_instance(flight_number, date)
        # Only available flights have prices
        if hasattr(flight_instance, 'prices') and isinstance(flight_instance.prices, dict):
            # New price for requested cabin
            if cabin not in flight_instance.prices:
                raise PolicyViolationException(f"Requested cabin '{cabin}' not available for flight {flight_number} on {date}.")
            total_new_price += flight_instance.prices[cabin]
            # Old price for original cabin
            if original_cabin not in flight_instance.prices:
                raise PolicyViolationException(f"Original cabin '{original_cabin}' not available for flight {flight_number} on {date}.")
            total_old_price += flight_instance.prices[original_cabin]
        else:
            raise PolicyViolationException(f"Cannot get price for flight {flight_number} on {date}. Flight status is not 'available'.")
    fare_difference = total_new_price - total_old_price
    if fare_difference < 0:
        fare_difference = 0  # No refund, only require payment for upgrade

    # 5. Check payment method covers the fare difference
    user = api.get_user_details(reservation.user_id)
    payment_method = user.payment_methods.get(payment_id)
    if payment_method is None:
        raise PolicyViolationException("Payment method not found in user profile.")
    # Check payment method balance/amount
    # For CreditCard, we cannot check balance, so we assume valid
    # For GiftCard and Certificate, check 'amount' field
    if hasattr(payment_method, 'source'):
        if payment_method.source == 'gift_card' or payment_method.source == 'certificate':
            if not hasattr(payment_method, 'amount'):
                raise PolicyViolationException("Payment method does not have an amount field.")
            if payment_method.amount < fare_difference:
                raise PolicyViolationException("Insufficient balance in payment method to cover fare difference.")
    # For credit card, assume valid (cannot check balance)
    # If payment method is not one of the above, raise error
    elif isinstance(payment_method, dict):
        # If dict, check source and amount
        source = payment_method.get('source')
        if source in ['gift_card', 'certificate']:
            amount = payment_method.get('amount')
            if amount is None or amount < fare_difference:
                raise PolicyViolationException("Insufficient balance in payment method to cover fare difference.")
        # For credit card, assume valid
        elif source == 'credit_card':
            pass
        else:
            raise PolicyViolationException("Unknown payment method type.")
    else:
        raise PolicyViolationException("Unknown payment method type.")
    # If all checks pass, allow the tool call
