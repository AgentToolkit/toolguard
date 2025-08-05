import sys

out_folder = "eval/airline/output/last"
sys.path.append(out_folder)
import rt_toolguard
app_guards = rt_toolguard.load(out_folder)

llm = rt_toolguard.Litellm(model_name="ASASA", custom_provider="azure") #example
app_guards.use_llm(llm)

messages = []
app_guards.check_tool_call("book_reservation", {
    "user_id":"user_123",
    "origin": "SFO",
    "destination": "JFK",
    "flight_type": "one_way",
    "cabin": "business",
    "flights": [{"flight_number": "HAT001", "date": "2024-05-01"}],
    "passengers": [{"first_name": "John", "last_name": "Doe", "dob": "1990-01-01"}],
    "payment_methods": [{"payment_id": "credit_card_123", "amount": 1000.0}],
    "total_baggages": 2,
    "nonfree_baggages": 0,
    "insurance": "no"
    },
    messages)