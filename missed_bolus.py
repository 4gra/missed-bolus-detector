#!/usr/bin/env python3
"""
This checks your (or any) Nightscout instance for carb entries, and warns when
there's no insulin delivered nearby.  Catches the odd bolus failure and plain old forgetfulness.

It assumes that carbs and insulin never coexist in a single entry -- this is true for one 
particular (Loop iOS, MDT, Libre) implementation and doesn't mean it is true for yours so
PLEASE CHECK!

This is not a therapeutic device, cannot be relied upon, et cetera.
You *really* use it at your own risk.

Copyright (C) 2024, https://github.com/4gra/missed-bolus-detector
This program comes with ABSOLUTELY NO WARRANTY; for details see included LICENCE.
This is free software, and you are welcome to redistribute it under certain
conditions; view the included file LICENCE for details.

Requires:
The 'requests' module (what doesn't): python-requests.org
Requires Nightscout to work at all: https://nightscout.github.io
Requires a Pushover account for nice notifications (and, really, everyone should have one).
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import socket
import time

# Set your Nightscout API URL and token
BASE_URL = "https://nightscout.example/api/v1"
NS_TOKEN = None
# Set your pushover App Token and User Key
PUSHOVER_TOKEN = None
PUSHOVER_KEY = None
# Some preferences
IGNORE_CARBS = 15  # ignore carb entries EQUAL TO OR LOWER than this
HOSTNAME = socket.gethostname()
APP_NAME = "missed-bolus-detector"
BOLUS_BEFORE = 240  # bolus within 4 minutes of carbing! See also loop time.
LOOP_TIME = 240 # loop time. max delay is therefore ~8mins.
# Other parameters to tweak involve the number of carb and insulin entries to search.
# These are set in main() - you could also search a time period instead of a count.


def fetch_data(filters, count=3):
    """
    Function to fetch data from the Nightscout API

    so silly, I'll fix this nicely later
    should be urlencoded and permit [][], but I won't bother for two keys
    """
    filters = {
        f"find[{key}]": (str(value).replace(" ", "+")) for key, value in filters.items()
    }
    filters["count"] = count
    filters["token"] = NS_TOKEN
    url = f"{BASE_URL}/treatments.json?" + "&".join(
        [f"{key}={value}" for key, value in filters.items()]
    )
    # print(f">> {url}")
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching {filters} data: {response.status_code}")
        return []


def check_missed_boluses(carb_data, insulin_data):
    """
    Function to check for missed boluses
    """
    for carb_entry in carb_data:
        carb_time = datetime.fromisoformat(carb_entry["timestamp"][:-1])
        matched = False
        print(f"Found carbs at {carb_entry['timestamp']}...")

        # Check insulin entries for a corresponding bolus within NN minutes
        for insulin_entry in insulin_data:
            insulin_time = datetime.fromisoformat(insulin_entry["timestamp"][:-1])
            if 0 <= (insulin_time - carb_time).total_seconds() <= BOLUS_BEFORE:
                print(f"-- Found matching insulin at {insulin_entry['timestamp']}.")
                matched = True # useless but might use later.
                break

        # No bolus yet; but check enough time has elapsed to worry
        if 0 < ( datetime.now() - carb_time ).total_seconds() <= BOLUS_BEFORE:
            break # too recent! just ignore.

        # Alert if no matching bolus found
        if not matched:
            print(f"Missed bolus detected for carb entry at {carb_time}.")
            send_alert(carb_entry)
            # Don't look for more trouble; avoid alert floods.
            break


def already_alerted(carb_data):
    """
    Checks to see if the alert has already been issued.
    """
    notes = fetch_data({"enteredBy": APP_NAME})
    for entry in notes:
        if entry["timestamp"] == carb_data["timestamp"]:
            print(f"-- Already alerted at {entry['timestamp']}...")
            return True
    return False


def send_alert(carb_entry, repeat=False):
    """
    Sends an alert, assuming one has not been sent before.
    """
    if not repeat:
        if not already_alerted(carb_entry):
            repeat = True

    if repeat:
        send_po_alert(carb_entry)
        send_ns_alert(carb_entry)


def send_ns_alert(carb_entry):
    """
    Alert using nightscout's own API.
    Not very useful in itself, but stores a note that prevents repeats.
    You could change the careportal type to avoid double-notification.
    TODO: localise timezone, this will all by UTC...
    """
    message = f"Missed bolus for {carb_entry['carbs']}g carbs at {carb_entry['timestamp']} UTC"
    data = {
        "enteredBy": APP_NAME,  # Identifier for the alert source
        "eventType": "Question",  # Device status event
        "notes": message,
        "created_at": datetime.utcnow().isoformat() + "Z",  # current time
        "timestamp": carb_entry["timestamp"],  # Time of the carb entry
        "device": HOSTNAME,
        "token": TOKEN,
    }

    url = f"{BASE_URL}/treatments?token={TOKEN}"
    # print(f">> {url} {data}")
    response = requests.post(url, data=data)

    if response.status_code == 200:
        print(f"Nightscout alert sent: {message}")
    else:
        print(f"Failed to send Nightscout alert: {response.status_code}")


def send_po_alert(carb_entry):
    """
    Function to send an alert via pushover
    """
    message = (
        f"Missed bolus for {carb_entry['carbs']}g carbs at {carb_entry['timestamp']}?"
    )
    data = {
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_KEY,
        "message": message,
        "title": "Missed Bolus??",
        "priority": 1,
    }
    response = requests.post("https://api.pushover.net/1/messages.json", data=data)
    if response.status_code == 200:
        print(f"Alert sent: {message}")
    else:
        print(f"Failed to send alert: {response.status_code}")
        # TODO: escalate and back off


def main():
    """
    Main loop, best approach for systemd.
    """
    while True:
        carb_data = fetch_data({"eventType": "Carb Correction", "carbs][%24gt": IGNORE_CARBS}, 5)
        insulin_data = fetch_data({"eventType": "Correction Bolus"}, 10)

        if carb_data and insulin_data:
            check_missed_boluses(carb_data, insulin_data)
        else:
            print("No data or error in fetching")

        time.sleep(LOOP_TIME)


if __name__ == "__main__":
    main()
