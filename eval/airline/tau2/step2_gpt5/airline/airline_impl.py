# Auto-generated class
from typing import *
from airline.i_airline import I_Airline
from airline.airline_types import *

from abc import ABC, abstractmethod
class IToolInvoker(ABC):
    T = TypeVar("T")
    @abstractmethod
    def invoke(self, toolname: str, arguments: Dict[str, Any], model: Type[T])->T:
        ...

class Airlineimpl(I_Airline):

    def __init__(self, delegate: IToolInvoker):
        self._delegate = delegate
    
    def book_reservation(self, user_id: str, origin: str, destination: str, flight_type: Literal['round_trip', 'one_way'], cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo], passengers: list[Passenger| dict], payment_methods: list[Payment| dict], total_baggages: int, nonfree_baggages: int, insurance: Literal['yes', 'no']) -> Reservation:
        """
        Book a reservation.

        Args:
            user_id: The ID of the user to book the reservation such as 'sara_doe_496'`.
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

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('book_reservation', args)


    def calculate(self, expression: str) -> str:
        """
        Calculate the result of a mathematical expression.

        Args:
            expression: The mathematical expression to calculate, such as '2 + 2'. The expression can contain numbers, operators (+, -, *, /), parentheses, and spaces.

        Returns:
            The result of the mathematical expression.

        Raises:
            ValueError: If the expression is invalid.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('calculate', args)


    def cancel_reservation(self, reservation_id: str) -> Reservation:
        """
        Cancel the whole reservation.

        Args:
            reservation_id: The reservation ID, such as 'ZFA04Y'.

        Returns:
            The updated reservation.

        Raises:
            ValueError: If the reservation is not found.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('cancel_reservation', args)


    def get_flight_instance(self, flight_number: str, date: str) -> Union[FlightDateStatusAvailable, FlightDateStatusLanded, FlightDateStatusCancelled, FlightDateStatusDelayed, FlightDataStatusFlying, FlightDataStatusOnTime]:
        """
        Get the flight.

        Args:
            flight_number: The flight number.
            date: The date of the flight.

        Returns:
            The flight.

        Raises:
            ValueError: If the flight is not found.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('get_flight_instance', args)


    def get_flight_status(self, flight_number: str, date: str) -> Literal['available', 'on time', 'flying', 'cancelled', 'delayed', 'landed']:
        """
        Get the status of a flight.

        Args:
            flight_number: The flight number.
            date: The date of the flight.

        Returns:
            The status of the flight.

        Raises:
            ValueError: If the flight is not found.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('get_flight_status', args)


    def get_reservation_details(self, reservation_id: str) -> Reservation:
        """
        Get the details of a reservation.

        Args:
            reservation_id: The reservation ID, such as '8JX2WO'.

        Returns:
            The reservation details.

        Raises:
            ValueError: If the reservation is not found.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('get_reservation_details', args)


    def get_scheduled_flight(self, flight_number: str) -> Flight:
        """
        Get the flight schedule.

        Args:
            flight_number: The flight number.

        Returns:
            The flight schedule

        Raises:
            ValueError: If the flight is not found.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('get_scheduled_flight', args)


    def get_user_details(self, user_id: str) -> User:
        """
        Get the details of a user, including their reservations.

        Args:
            user_id: The user ID, such as 'sara_doe_496'.

        Returns:
            The user details.

        Raises:
            ValueError: If the user is not found.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('get_user_details', args)


    def list_all_airports(self) -> list[AirportCode]:
        """
Returns a list of all available airports.

        Returns:
            A dictionary mapping IATA codes to AirportInfo objects.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('list_all_airports', args)


    def search_direct_flight(self, origin: str, destination: str, date: str) -> list[DirectFlight]:
        """
        Search for direct flights between two cities on a specific date.

        Args:
            origin: The origin city airport in three letters, such as 'JFK'.
            destination: The destination city airport in three letters, such as 'LAX'.
            date: The date of the flight in the format 'YYYY-MM-DD', such as '2024-01-01'.

        Returns:
            The direct flights between the two cities on the specific date.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('search_direct_flight', args)


    def search_onestop_flight(self, origin: str, destination: str, date: str) -> list[tuple[DirectFlight, DirectFlight]]:
        """
        Search for one-stop flights between two cities on a specific date.

        Args:
            origin: The origin city airport in three letters, such as 'JFK'.
            destination: The destination city airport in three letters, such as 'LAX'.
            date: The date of the flight in the format 'YYYY-MM-DD', such as '2024-05-01'.

        Returns:
            A list of pairs of DirectFlight objects.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('search_onestop_flight', args)


    def send_certificate(self, user_id: str, amount: int) -> str:
        """
        Send a certificate to a user. Be careful!

        Args:
            user_id: The ID of the user to book the reservation, such as 'sara_doe_496'.
            amount: The amount of the certificate to send.

        Returns:
            A message indicating the certificate was sent.

        Raises:
            ValueError: If the user is not found.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('send_certificate', args)


    def transfer_to_human_agents(self, summary: str) -> str:
        """
        Transfer the user to a human agent, with a summary of the user's issue.
        Only transfer if
         -  the user explicitly asks for a human agent
         -  given the policy and the available tools, you cannot solve the user's issue.

        Args:
            summary: A summary of the user's issue.

        Returns:
            A message indicating the user has been transferred to a human agent.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('transfer_to_human_agents', args)


    def update_reservation_baggages(self, reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str) -> Reservation:
        """
        Update the baggage information of a reservation.

        Args:
            reservation_id: The reservation ID, such as 'ZFA04Y'
            total_baggages: The updated total number of baggage items included in the reservation.
            nonfree_baggages: The updated number of non-free baggage items included in the reservation.
            payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.

        Returns:
            The updated reservation.

        Raises:
            ValueError: If the reservation is not found.
            ValueError: If the user is not found.
            ValueError: If the payment method is not found.
            ValueError: If the certificate cannot be used to update reservation.
            ValueError: If the gift card balance is not enough.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('update_reservation_baggages', args)


    def update_reservation_flights(self, reservation_id: str, cabin: Literal['business', 'economy', 'basic_economy'], flights: list[FlightInfo| dict], payment_id: str) -> Reservation:
        """
        Update the flight information of a reservation.


        Args:
            reservation_id: The reservation ID, such as 'ZFA04Y'.
            cabin: The cabin class of the reservation
            flights: An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
            payment_id: The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.

        Returns:
            The updated reservation.

        Raises:
            ValueError: If the reservation is not found.
            ValueError: If the user is not found.
            ValueError: If the payment method is not found.
            ValueError: If the certificate cannot be used to update reservation.
            ValueError: If the gift card balance is not enough.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('update_reservation_flights', args)


    def update_reservation_passengers(self, reservation_id: str, passengers: list[Passenger| dict]) -> Reservation:
        """
        Update the passenger information of a reservation.

        Args:
            reservation_id: The reservation ID, such as 'ZFA04Y'.
            passengers: An array of objects containing details about each passenger.

        Returns:
            The updated reservation.

        Raises:
            ValueError: If the reservation is not found.
            ValueError: If the number of passengers does not match.
        
        """

        args = locals().copy()
        args.pop("self", None)
        return self._delegate.invoke('update_reservation_passengers', args)

