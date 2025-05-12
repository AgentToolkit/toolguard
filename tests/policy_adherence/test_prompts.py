import os
from pathlib import Path

from dotenv import load_dotenv
from policy_adherence.llm.litellm_model import LitellmModel
from policy_adherence.prompts import tool_information_dependencies
from policy_adherence.data_types import SourceFile

load_dotenv()

current_dir = str(Path(__file__).parent)
domain = SourceFile.load_from(current_dir, "_tau_airline_domain.py")

model = "gpt-4o-2024-08-06"
llm = LitellmModel(model)

def test_dependencies_passangers():
    policy = """
    The total number of passengers in a reservation does not exceed five.
    """
    assert tool_information_dependencies("book_reservation", policy, domain) == []

def test_dependencies_payment_in_user():
    policy = """
    All payment methods used are already present in the user's profile. 
    Each reservation can use at most one travel certificate, one credit card, and three gift cards. 
    """
    assert tool_information_dependencies("book_reservation", policy, domain) == ["get_user_details"]

def test_dependencies_payment_in_args():
    policy = """
    Each reservation can use at most one travel certificate, one credit card, and three gift cards. 
    """
    assert tool_information_dependencies("book_reservation", policy, domain) == ["get_user_details"]


def test_dependencies_membership():
    policy = """
    If the booking user is a regular member, 0 free checked bag for each basic economy passenger, 1 free checked bag for each economy passenger, and 2 free checked bags for each business passenger. 
    If the booking user is a silver member, 1 free checked bag for each basic economy passenger, 2 free checked bag for each economy passenger, and 3 free checked bags for each business passenger. 
    If the booking user is a gold member, 2 free checked bag for each basic economy passenger, 3 free checked bag for each economy passenger, and 3 free checked bags for each business passenger.
    """
    assert tool_information_dependencies("book_reservation", policy, domain) == ["get_user_details"]

def test_dependencies_flight_status():
    policy = """
     "The agent must ensure that the flight status is 'available' before booking.
     Flights with status 'delayed', 'on time', or 'flying' cannot be booked.
    """
    assert tool_information_dependencies("book_reservation", policy, domain) == ["get_flight_instance"]
    