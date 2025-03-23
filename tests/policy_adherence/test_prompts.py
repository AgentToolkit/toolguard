import os
from pathlib import Path

from dotenv import load_dotenv
from policy_adherence.llm.azure_wrapper import AzureLitellm
from policy_adherence.prompts_gen_ai import tool_information_dependencies
from policy_adherence.types import SourceFile

load_dotenv()

current_dir = Path(__file__).parent
domain = SourceFile.load_from(os.path.join(current_dir,"tau_airline_domain.py"))

model = "gpt-4o-2024-08-06"
llm = AzureLitellm(model)

def test_dependencies_passangers():
    policy = """
    The agent must ensure that the total number of passengers in a reservation does not exceed five before invoking the BookReservation tool.
    """
    assert tool_information_dependencies("book_reservation", policy, domain) == []

def test_dependencies_payment_in_user():
    policy = """
    Before invoking the BookReservation tool, the agent must verify that all payment methods used are already present in the user's profile. 
    Each reservation can use at most one travel certificate, one credit card, and three gift cards. 
    """
    assert tool_information_dependencies("book_reservation", policy, domain) == ["get_user_details"]

def test_dependencies_payment_in_args():
    policy = """
    Each reservation can use at most one travel certificate, one credit card, and three gift cards. 
    """
    assert tool_information_dependencies("book_reservation", policy, domain) == ["get_user_details"]