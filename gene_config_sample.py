import os
import sys
import json

input_file = "config.json"
output_file = "config.json.sample"

def main():
    # Step1: Read the JSON file
    with open(input_file, "r") as f:
        input_json = json.load(f)

    # Step2: hide confidential information
    input_json["twitter"]["user"] = "******"
    input_json["twitter"]["password"] = "******"
    input_json["mail"]["to"] = "******"
    input_json["mail"]["cc"] = "******"
    input_json["elastic_search"]["host"] = "******"

    # Step3: write the input_json to output_file
    with open(output_file, "w") as f:
        json.dump(input_json, f, indent=4)

main()
