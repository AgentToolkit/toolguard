from typing import *
from rt_toolguard.data_types import ChatHistory, PolicyViolationException
from airline.airline_types import *
from airline.i_airline import I_Airline


def guard_checked_bag_allowance_by_membership_tier(history: ChatHistory, api: I_Airline, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo | dict], passengers: list[Passenger | dict], payment_methods: list[Payment | dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']):
    """
    Policy to check: The checked bag allowance policy for booking a reservation varies by membership tier and cabin class: 
    1) Regular members have 0 free checked bags for basic economy, 1 for economy, and 2 for business. 
    2) Silver members have 1 free checked bag for basic economy, 2 for economy, and 3 for business. 
    3) Gold members have 2 free checked bags for basic economy, 3 for economy and business. 
    An extra baggage fee of $50 applies for additional luggage.

    Args:
        history (ChatHistory): provide question-answer services over the past chat messages.
        api (I_Airline): api to access other tools.
        user_id: The ID of the user to book the reservation such as 'sara_doe_496'.
        origin: The IATA code for the origin city such as 'SFO'.
        destination: The IATA code for the destination city such as 'JFK'.
        flight_type: The type of flight such as 'one_way' or 'round_trip'.
        cabin: The cabin class such as 'basic_economy', 'economy', or 'business'.
        flights: An array of objects containing details about each piece of flight.
        passengers: An array of objects containing details about each passenger.
        payment_methods: An array of objects containing details about each payment method.
        total_baggages: The total number of baggage items to book the reservation.
        nonfree_baggages: The number of non-free baggage items to book the reservation.
        insurance: Whether the reservation has insurance.
    """
    # Retrieve user details to determine membership tier
    user_details = api.get_user_details(user_id)
    membership_tier = user_details.membership

    # Define free baggage allowance based on membership tier and cabin class
    free_baggage_allowance = {
        'regular': {'basic_economy': 0, 'economy': 1, 'business': 2},
        'silver': {'basic_economy': 1, 'economy': 2, 'business': 3},
        'gold': {'basic_economy': 2, 'economy': 3, 'business': 3}
    }

    # Calculate allowed free baggage
    allowed_free_bags = free_baggage_allowance[membership_tier][cabin]

    # Check if the number of free bags exceeds the allowed limit
    if total_baggages - nonfree_baggages > allowed_free_bags:
        raise PolicyViolationException(f"Exceeded free baggage allowance for {membership_tier} members in {cabin} class.")

    # Check if non-free baggage count matches the expected extra baggage
    expected_nonfree_bags = total_baggages - allowed_free_bags
    if nonfree_baggages != expected_nonfree_bags:
        raise PolicyViolationException("Non-free baggage count does not match the expected extra baggage fee.")

    # Additional check for silver members in basic economy
    if membership_tier == 'silver' and cabin == 'basic_economy' and total_baggages == 1 and nonfree_baggages == 0:
        raise PolicyViolationException("Silver members with one bag in basic economy should be charged for the bag.")