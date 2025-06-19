import unittest
from unittest.mock import MagicMock, patch

# Importing necessary modules
from my_app.update_reservation_baggages.guard_update_reservation_baggages import guard_update_reservation_baggages
from my_app.common import *
from my_app.domain import *


class TestGuardAddOnlyCheckedBaggages(unittest.TestCase):

    def normal_story(self, num_of_payed_bags:int):
        # Mocking the API response
        user = GetUserDetailsResponse(
            membership = "gold",
            payment_methods={
                'credit_card_7815826': PaymentMethods(source='credit_card', brand='Visa', last_four='1234'),
            },
        )
        reservation = GetReservationDetailsResponse(
            user_id="abc",
            total_baggages=1,
            nonfree_baggages=1,
            cabin="business",
            payment_history=[
                PaymentHistoryItem2(payment_id='credit_card_7815826', amount=50*num_of_payed_bags)
            ]
        )
        
        history = MagicMock()
        history.ask_bool.return_value = True

        # Mocking the API
        api = MagicMock()
        api.get_reservation_details.return_value = reservation
        api.get_user_details.return_value = user
        return history, api, reservation, user
        
    def test_gold_business_from_1_to_4(self):
        """
        Test case: Updating the reservation by increasing total checked baggages from 3 to 5, ensuring all additional bags are checked bags and complying with policy guidelines.
        """
        history, api, reservation, user = self.normal_story(1)

        # Creating function call arguments
        args = UpdateReservationBaggagesRequest.model_construct(
            reservation_id='ZFA04Y',
            total_baggages=4,
            nonfree_baggages=1,
            payment_id='credit_card_7815826'
        )
        guard_update_reservation_baggages(args, history, api)

    def test_gold_basic_economy_from_1_to_3(self):
        """
        Test case: Updating the reservation by increasing total checked baggages from 3 to 5, ensuring all additional bags are checked bags and complying with policy guidelines.
        """
        history, api, reservation, user = self.normal_story(1)
        reservation.cabin = "basic_economy"
        # Creating function call arguments
        args = UpdateReservationBaggagesRequest.model_construct(
            reservation_id='ZFA04Y',
            total_baggages=3,
            nonfree_baggages=1,
            payment_id='credit_card_7815826'
        )
        guard_update_reservation_baggages(args, history, api)

    def test_decrease_from_3_to_2_raises_exception(self):
        history, api, reservation, user = self.normal_story(0)

        # Creating function call arguments
        args = UpdateReservationBaggagesRequest.model_construct(
            reservation_id='ZFA04Y',
            total_baggages=0,
            nonfree_baggages=0,
            payment_id='credit_card_7815826'
        )
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_baggages(args, history, api)

    def test_test_payment_method_not_in_user(self):
        history, api, reservation, user = self.normal_story(1)

        # Creating function call arguments
        args = UpdateReservationBaggagesRequest.model_construct(
            reservation_id='ZFA04Y',
            total_baggages=4,
            nonfree_baggages=1,
            payment_id='1212'
        )
        with self.assertRaises(PolicyViolationException):
            guard_update_reservation_baggages(args, history, api)


if __name__ == '__main__':
    unittest.main()
