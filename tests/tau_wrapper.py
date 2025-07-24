import inspect
import json
from typing import Any, Dict, List, Literal
from tau_bench.envs.airline.tools.book_reservation import BookReservation
from tau_bench.envs.airline.tools.calculate import Calculate
from tau_bench.envs.airline.tools.cancel_reservation import CancelReservation
from tau_bench.envs.airline.tools.get_reservation_details import GetReservationDetails
from tau_bench.envs.airline.tools.get_user_details import GetUserDetails
from tau_bench.envs.airline.tools.get_flight_details import GetFlightDetails
from tau_bench.envs.airline.tools.get_flight_on_date_details import GetFlightOnDateDetails
from tau_bench.envs.airline.tools.list_all_airports import ListAllAirports
from tau_bench.envs.airline.tools.search_direct_flight import SearchDirectFlight
from tau_bench.envs.airline.tools.search_onestop_flight import SearchOnestopFlight
from tau_bench.envs.airline.tools.send_certificate import SendCertificate
from tau_bench.envs.airline.tools.think import Think
from tau_bench.envs.airline.tools.transfer_to_human_agents import TransferToHumanAgents
from tau_bench.envs.airline.tools.update_reservation_baggages import UpdateReservationBaggages
from tau_bench.envs.airline.tools.update_reservation_flights import UpdateReservationFlights
from tau_bench.envs.airline.tools.update_reservation_passengers import UpdateReservationPassengers

class AirlineAPI:

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data
    
    def book_reservation(self,
        user_id: str,
        origin: str,
        destination: str,
        flight_type: Literal["one_way", "round_trip"],
        cabin: Literal["basic_economy", "economy", "business"],
        flights: List[Dict[str, str]],
        passengers: List[Dict[str, str]],
        payment_methods: List[Dict[str, float]],
        total_baggages: int,
        nonfree_baggages: int,
        insurance: Literal["yes", "no"]
    ) -> str:
        """
        Book a reservation.

        Returns the created reservation record in JSON format as a string.

        Args:
            user_id (str): The ID of the user to book the reservation, such as 'sara_doe_496'.
            origin (str): The IATA code for the origin city, such as 'SFO'.
            destination (str): The IATA code for the destination city, such as 'JFK'.
            flight_type (Literal): Type of flight, either 'one_way' or 'round_trip'.
            cabin (Literal): Cabin class, one of 'basic_economy', 'economy', or 'business'.
            flights (List[Dict[str, str]]): List of flight segments. Each item should include:
                - flight_number (str): e.g., 'HAT001'
                - date (str): in 'YYYY-MM-DD' format.
            passengers (List[Dict[str, str]]): List of passengers. Each should include:
                - first_name (str): e.g., 'Noah'
                - last_name (str): e.g., 'Brown'
                - dob (str): Date of birth in 'YYYY-MM-DD'.
            payment_methods (List[Dict[str, float]]): Payment methods used. Each item includes:
                - payment_id (str): e.g., 'credit_card_7815826'
                - amount (float): Payment amount.
            total_baggages (int): Total number of baggage items.
            nonfree_baggages (int): Number of non-free baggage items.
            insurance (Literal): Whether insurance is included, 'yes' or 'no'.

        Returns:
            str: JSON string representing the created reservation.

        Example:
            '{"user_id": "mohamed_silva_9265", "origin": "JFK", ... }'
        """
        return BookReservation.invoke(self._data,
            user_id,
            origin,
            destination,
            flight_type,
            cabin,
            flights,
            passengers,
            payment_methods,
            total_baggages,
            nonfree_baggages,
            insurance)

    def calculate(self, expression: str) -> str:
        """
        Calculate the result of a mathematical expression.

        The expression can include numbers, operators (+, -, *, /), parentheses, and spaces.

        Args:
            expression (str): The mathematical expression to evaluate, such as '2 + 2'.

        Returns:
            str: The result of the calculation, formatted as a string. 
                Example: '"16.0"'
        
        Raises:
            ValueError: If the expression is invalid or contains disallowed content.
        """
        return Calculate.invoke(self._data, expression)

    def cancel_reservation(self, reservation_id: str) -> dict:
        """
        Cancel the whole reservation.

        Args:
            reservation_id (str): The reservation ID, such as 'ZFA04Y'.

        Returns:
            str: The cancelled reservation entity in JSON format.
                Example:
                '{"reservation_id": "H9ZU1C", "user_id": "mia_kim_4397", "origin": "MIA", "destination": "EWR", "flight_type": "one_way", "cabin": "economy", "flights": [{"origin": "MIA", "destination": "EWR", "flight_number": "HAT192", "date": "2024-05-24", "price": 174}], "passengers": [{"first_name": "James", "last_name": "Moore", "dob": "1977-02-03"}], "payment_history": [{"payment_id": "gift_card_7359776", "amount": 897}], "created_at": "2024-05-01T04:50:18", "total_baggages": 0, "nonfree_baggages": 0, "insurance": "no", "status": "cancelled"}'
        """
        return json.loads(CancelReservation.invoke(self._data, reservation_id))

    def get_reservation_details(self, reservation_id: str) -> dict:
        """
        Get the details of a reservation.

        Returns the Reservation entity.

        Example of returned value:
        {
            "reservation_id": "H9ZU1C",
            "user_id": "mia_kim_4397",
            "origin": "MIA",
            "destination": "EWR",
            "flight_type": "one_way",
            "cabin": "economy",
            "flights": [
                {
                    "origin": "MIA",
                    "destination": "EWR",
                    "flight_number": "HAT192",
                    "date": "2024-05-24",
                    "price": 174
                }
            ],
            "passengers": [
                {
                    "first_name": "James",
                    "last_name": "Moore",
                    "dob": "1977-02-03"
                }
            ],
            "payment_history": [
                {
                    "payment_id": "gift_card_7359776",
                    "amount": 897
                }
            ],
            "created_at": "2024-05-01T04:50:18",
            "total_baggages": 0,
            "nonfree_baggages": 0,
            "insurance": "no"
        }

        Args:
            reservation_id: The reservation id, such as '8JX2WO'.

        Returns:
            A dictionary containing the reservation details.
        """
        return json.loads(GetReservationDetails.invoke(self._data, reservation_id=reservation_id))

    def get_user_details(self, user_id: str) -> dict:
        """
        Get the details of a user.

        Returns the User entity as a dictionary.

        Example of returned value:
        {
            "name": {
                "first_name": "Aarav",
                "last_name": "Ahmed"
            },
            "address": {
                "address1": "176 Willow Lane",
                "address2": "Suite 431",
                "city": "Jacksonville",
                "country": "USA",
                "province": "FL",
                "zip": "32131"
            },
            "email": "aarav.ahmed6812@example.com",
            "dob": "1981-05-26",
            "payment_methods": {
                "credit_card_9074831": {
                    "source": "credit_card",
                    "brand": "mastercard",
                    "last_four": "7334",
                    "id": "credit_card_9074831"
                },
                "certificate_9645872": {
                    "source": "certificate",
                    "amount": 250,
                    "id": "certificate_9645872"
                },
                "credit_card_4959530": {
                    "source": "credit_card",
                    "brand": "mastercard",
                    "last_four": "5018",
                    "id": "credit_card_4959530"
                }
            },
            "saved_passengers": [
                {
                    "first_name": "Aarav",
                    "last_name": "Patel",
                    "dob": "1980-12-03"
                }
            ],
            "membership": "silver",
            "reservations": ["M20IZO", "N6F783", "IFOYYZ", "NQNU5R"]
        }

        Args:
            user_id: The user ID, such as 'sara_doe_496'.

        Returns:
            A dictionary representing the user details.
        """
        return json.loads(GetUserDetails.invoke(self._data, user_id=user_id))

    def get_flight_details(self, flight_id: str) -> dict:
        """
        Get the details of a flight.

        Args:
            flight_id (str): The flight ID, such as 'HAT001'.

        Returns:
            str: JSON string containing flight details.
                Example:
                '{"flight_number": "HAT039", "origin": "ATL", "destination": "SEA", "scheduled_departure_time_est": "22:00:00", "scheduled_arrival_time_est": "03:00:00+1"}'
        """
        return json.loads(GetFlightDetails.invoke(self._data, flight_id=flight_id))

    def get_flight_on_date_details(self, flight_id: str, date: str) -> dict:
        """
        Get the details of a flight occurrence on a specific date.
        
        Returns the flight status, available seats, and prices.

        Example of returned entity:
        {
            "status": "available",
            "available_seats": {
                "basic_economy": 8,
                "economy": 14,
                "business": 6
            },
            "prices": {
                "basic_economy": 69,
                "economy": 162,
                "business": 364
            }
        }

        Args:
            flight_id: The flight id, such as 'HAT001'.
            date: The date of the flight, such as '2024-05-02'.

        Returns:
            A dictionary with flight status, available seats, and prices.
        """
        return json.loads(GetFlightOnDateDetails.invoke(self._data, flight_id=flight_id, date=date))

    def list_all_airports(self) -> dict:
        """
        List all airports and their cities.

        Returns:
            A dictionary mapping airport codes to city names.

        Example:
            {
                "SFO": "San Francisco",
                "JFK": "New York"
            }
        """
        return json.loads(ListAllAirports.invoke(self._data))

    def search_direct_flight(self, origin: str, destination: str, date: str) -> list[dict]:
        """
        Search direct flights between two cities on a specific date.

        Args:
            origin: The origin city airport in three letters, such as 'JFK'.
            destination: The destination city airport in three letters, such as 'LAX'.
            date: The date of the flight in the format 'YYYY-MM-DD', such as '2024-01-01'.

        Returns:
            A list of available flights.

        Example:
            [
                {
                    "flight_number": "HAT069",
                    "origin": "JFK",
                    "destination": "SEA",
                    "scheduled_departure_time_est": "06:00:00",
                    "scheduled_arrival_time_est": "12:00:00",
                    "status": "available",
                    "available_seats": {
                        "basic_economy": 17,
                        "economy": 12,
                        "business": 3
                    },
                    "prices": {
                        "basic_economy": 51,
                        "economy": 121,
                        "business": 239
                    }
                },
                {
                    "flight_number": "HAT083",
                    "origin": "JFK",
                    "destination": "SEA",
                    "scheduled_departure_time_est": "01:00:00",
                    "scheduled_arrival_time_est": "07:00:00",
                    "status": "available",
                    "available_seats": {
                        "basic_economy": 16,
                        "economy": 7,
                        "business": 3
                    },
                    "prices": {
                        "basic_economy": 87,
                        "economy": 100,
                        "business": 276
                    }
                }
            ]
        """
        return json.loads(SearchDirectFlight.invoke(self._data, origin=origin, destination=destination, date=date))

    def search_onestop_flight(self, origin: str, destination: str, date: str) -> list[dict]:
        """
        Search one-stop flights between two cities on a specific date.

        Args:
            origin: The origin city airport in three letters, such as 'JFK'.
            destination: The destination city airport in three letters, such as 'LAX'.
            date: The date of the flight in the format 'YYYY-MM-DD', such as '2024-05-01'.

        Returns:
            A list of one-stop flight options, each represented as a dictionary.
        """
        return json.loads(SearchOnestopFlight.invoke(self._data, origin=origin, destination=destination, date=date))

    def send_certificate(self, user_id: str, amount: int) -> dict:
        """
        Send a certificate to a user. Be careful!

        Args:
            user_id: The ID of the user to book the reservation, such as 'sara_doe_496'.
            amount: Certificate amount to send.

        Returns:
            A dictionary with the result of the operation.
        """
        return json.loads(SendCertificate.invoke(self._data, user_id=user_id, amount=amount))

    def think(self, thought: str) -> dict:
        """
        Use the tool to think about something.

        It will not obtain new information or change the database, 
        but just append the thought to the log. Use it when complex reasoning is needed.

        Args:
            thought: A thought to think about.

        Returns:
            A dictionary confirming the thought was logged.
        """
        return json.loads(Think.invoke(self._data, thought=thought))

    def transfer_to_human_agents(self, summary: str) -> dict:
        """
        Transfer the user to a human agent.

        Only use this method if the user explicitly asks for a human agent,
        or if the user's issue cannot be resolved by the agent with the available tools.

        Args:
            summary: A summary of the user's issue.

        Returns:
            A dictionary confirming the transfer request.
        """
        return json.loads(TransferToHumanAgents.invoke(self._data, summary=summary))

    def update_reservation_baggages(
        self,
        reservation_id: str,
        total_baggages: int,
        nonfree_baggages: int,
        payment_id: str
    ) -> dict:
        """
        Update the baggage information of a reservation.

        Returns the updated reservation record.

        Example of returned entity:
        {
            "reservation_id": "H9ZU1C",
            "user_id": "mia_kim_4397",
            "origin": "MIA",
            "destination": "EWR",
            "flight_type": "one_way",
            "cabin": "economy",
            "flights": [
                {
                    "origin": "MIA",
                    "destination": "EWR",
                    "flight_number": "HAT192",
                    "date": "2024-05-24",
                    "price": 174
                }
            ],
            "passengers": [
                {
                    "first_name": "James",
                    "last_name": "Moore",
                    "dob": "1977-02-03"
                }
            ],
            "payment_history": [
                {
                    "payment_id": "gift_card_7359776",
                    "amount": 897
                }
            ],
            "created_at": "2024-05-01T04:50:18",
            "total_baggages": 0,
            "nonfree_baggages": 0,
            "insurance": "no"
        }

        Args:
            reservation_id: The reservation ID, such as 'ZFA04Y'.
            total_baggages: The updated total number of baggage items.
            nonfree_baggages: The updated number of non-free baggage items.
            payment_id: The payment ID used, such as 'credit_card_7815826'.

        Returns:
            A dictionary representing the updated reservation.
        """
        return json.loads(UpdateReservationBaggages.invoke(
            self._data,
            reservation_id=reservation_id,
            total_baggages=total_baggages,
            nonfree_baggages=nonfree_baggages,
            payment_id=payment_id
        ))
    
    def update_reservation_flights(
        self,
        reservation_id: str,
        cabin: str,
        flights: list[dict],
        payment_id: str
    ) -> str:
        """
        Update the flight information of a reservation.

        The flights list must contain all segments of the reservation, even if unchanged.

        Args:
            reservation_id: The reservation ID, such as 'ZFA04Y'.
            cabin: The new cabin class, one of 'basic_economy', 'economy', 'business'.
            flights: A list of flight segment dictionaries, each with 'flight_number' and 'date'.
            payment_id: The payment ID used, such as 'credit_card_7815826'.

        Returns:
            A JSON-formatted string representing the updated reservation.

        Example:
            {
                "reservation_id": "H9ZU1C",
                "user_id": "mia_kim_4397",
                "origin": "MIA",
                "destination": "EWR",
                "flight_type": "one_way",
                "cabin": "economy",
                "flights": [
                    {
                        "origin": "MIA",
                        "destination": "EWR",
                        "flight_number": "HAT192",
                        "date": "2024-05-24",
                        "price": 174
                    }
                ],
                "passengers": [
                    {
                        "first_name": "James",
                        "last_name": "Moore",
                        "dob": "1977-02-03"
                    }
                ],
                "payment_history": [
                    {
                        "payment_id": "gift_card_7359776",
                        "amount": 897
                    }
                ],
                "created_at": "2024-05-01T04:50:18",
                "total_baggages": 0,
                "nonfree_baggages": 0,
                "insurance": "no"
            }
        """
        return UpdateReservationFlights.invoke(
            self._data,
            reservation_id=reservation_id,
            cabin=cabin,
            flights=flights,
            payment_id=payment_id
        )

    def update_reservation_passengers(
        self,
        reservation_id: str,
        passengers: list[dict]
    ) -> str:
        """
        Update the passenger information of a reservation.

        Args:
            reservation_id: The reservation ID, such as 'ZFA04Y'.
            passengers: A list of passengers, each a dict with keys:
                - first_name: Passenger's first name, e.g. 'Noah'
                - last_name: Passenger's last name, e.g. 'Brown'
                - dob: Date of birth in 'YYYY-MM-DD' format, e.g. '1990-01-01'

        Returns:
            A JSON-formatted string representing the updated reservation.

        Example returned entity:
        {
            "reservation_id": "H9ZU1C",
            "user_id": "mia_kim_4397",
            "origin": "MIA",
            "destination": "EWR",
            "flight_type": "one_way",
            "cabin": "economy",
            "flights": [
                {
                    "origin": "MIA",
                    "destination": "EWR",
                    "flight_number": "HAT192",
                    "date": "2024-05-24",
                    "price": 174
                }
            ],
            "passengers": [
                {
                    "first_name": "James",
                    "last_name": "Moore",
                    "dob": "1977-02-03"
                }
            ],
            "payment_history": [
                {
                    "payment_id": "gift_card_7359776",
                    "amount": 897
                }
            ],
            "created_at": "2024-05-01T04:50:18",
            "total_baggages": 0,
            "nonfree_baggages": 0,
            "insurance": "no"
        }
        """
        return UpdateReservationPassengers.invoke(
            self._data,
            reservation_id=reservation_id,
            passengers=passengers
        )


ALL_TOOLS = [member for name, member in inspect.getmembers(AirlineAPI, predicate=inspect.isfunction)]