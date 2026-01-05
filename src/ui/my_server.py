import argparse
import os

from flask import Flask, jsonify, request
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)


@app.route("/api/tools", methods=["GET"])
def get_tools():
    return jsonify(fsummary)


@app.route("/api/policies", methods=["GET"])
def get_policies():
    tool_name = request.args.get("tool_name")
    if not tool_name:
        return jsonify({"error": "Missing tool_name parameter"}), 400

    if tool_name in policies_data:
        return jsonify(policies_data[tool_name])
    return jsonify({"error": "Tool not found or has no policies"}), 404


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="parser")
    parser.add_argument(
        "--policy-path",
        type=str,
        default="/Users/naamazwerdling/Documents/OASB/policy_validation/airline/wiki.md",
    )
    parser.add_argument(
        "--functions-schema",
        type=str,
        default="/Users/naamazwerdling/Documents/OASB/policy_validation/airline/fc_schema.json",
    )
    parser.add_argument(
        "--policies-dir",
        type=str,
        default="/Users/naamazwerdling/Documents/OASB/policy_validation/airline/final copy 4",
    )
    args = parser.parse_args()
    policies_dir = args.policies_dir
    functions_schema = args.functions_schema

    with open(functions_schema, "r") as file:
        functions = json.load(file)

    fsummary = {}
    for k, v in functions.items():
        name, ext = os.path.splitext(k)
        camel_case_name = "".join(word.capitalize() for word in name.split("_"))
        fsummary[camel_case_name] = v["description"]

    policies_data = {}
    for filename in os.listdir(policies_dir):
        if filename.endswith(".json"):
            name = filename.replace(".json", "")
            print(name)
            with open(
                os.path.join(policies_dir, filename),
            ) as f:
                data = json.load(f)
                policies_data[name] = data

    print(json.dumps(fsummary))
    print(json.dumps(policies_data))

    app.run(host="0.0.0.0", port=8000)
