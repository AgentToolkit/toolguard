from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from airline.airline_types import *
from airline.i_airline import I_Airline
from airline.update_reservation_baggages.guard_update_reservation_baggages import guard_update_reservation_baggages
from rt_toolguard.data_types import PolicyViolationException


class TestGuardAddOnlyCheckedBaggages(unittest.TestCase):
    reserv_id = "res1"

    def normal_story(self, num_of_payed_bags:int):
        # Mocking the API response
        user = User.model_construct(
            user_id = "abc",
            membership = "gold",
            payment_methods={
                'cc': CreditCard(id="cc", source='credit_card', brand='Visa', last_four='1234'),
            },
        )
        reservation = Reservation(
            reservation_id=self.reserv_id,
            user_id="abc",
            origin="JFK",
            destination="SFO",
            flight_type="one_way",
            insurance="yes",
            created_at=(datetime.now() - timedelta(hours=50)).strftime("%Y-%m-%d %H:%M:%S"),
            total_baggages=1,
            nonfree_baggages=num_of_payed_bags,
            cabin="business",
            payment_history=[
                Payment(payment_id='cc', amount=50*num_of_payed_bags)
            ],
            passengers=[
                Passenger(first_name="John", last_name="Doe", dob="1990-01-01")
            ],
            flights=[
                ReservationFlight(flight_number="ANOTHER ONE", date="2025-02-28", origin= "DFW", destination = "LAX", price= 883),
            ],
            status=None
        )
        
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mocking the API
        api = MagicMock()
        api.get_reservation_details.side_effect = lambda resrv_id: reservation if resrv_id == reservation.reservation_id else None
        api.get_user_details.side_effect =  lambda u_id: user if u_id == user.user_id else None
        return history, api, reservation, user
        
    def test_gold_business_from_1_to_4(self):
        """
        Test case: Updating the reservation by increasing total checked baggages from 1 to 4.
        """
        history, api, reservation, user = self.normal_story(1)

        guard_update_reservation_baggages(history, api,
            reservation_id=self.reserv_id,
            total_baggages=4,
            nonfree_baggages=1,
            payment_id='cc')

    def test_gold_basic_economy_from_1_to_3(self):
        """
        Test case: Updating the reservation by increasing total checked baggages from 3 to 5.
        """
        history, api, reservation, user = self.normal_story(1)
        reservation.cabin = "basic_economy"
        guard_update_reservation_baggages(history, api, 
            reservation_id=self.reserv_id,
            total_baggages=3,
            nonfree_baggages=1,
            payment_id='cc')

    def test_decrease_from_3_to_2_raises_exception(self):
        history, api, reservation, user = self.normal_story(0)

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_baggages(history, api, 
            reservation_id=self.reserv_id,
            total_baggages=0,
            nonfree_baggages=0,
            payment_id='cc')

    def test_test_payment_method_not_in_user(self):
        history, api, reservation, user = self.normal_story(1)

        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_baggages(history, api, 
            reservation_id=self.reserv_id,
            total_baggages=4,
            nonfree_baggages=1,
            payment_id='1212')


if __name__ == '__main__':
    unittest.main()
