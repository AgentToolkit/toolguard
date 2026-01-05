from flask import Flask, jsonify, request
import json


app = Flask(__name__)
POLICIES_FILE = "/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final copy 4/BookReservation.json"


def load_policies():
    try:
        with open(POLICIES_FILE, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_policies(policies):
    with open(POLICIES_FILE, "w") as file:
        json.dump(policies, file, indent=4)


@app.route("/api/policies", methods=["GET"])
def get_policies():
    return jsonify(load_policies())


@app.route("/api/policies", methods=["POST"])
def save_policy():
    policies = request.json
    save_policies(policies)
    return jsonify({"message": "Policies saved successfully"})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
