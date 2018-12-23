#!/usr/bin/python3
import logging
import sys
import time
from lib import Account
from lib import EventLightweightPush
import os
import xml.etree.ElementTree
import signal
import base64

# Global list of accounts to handle.
accounts = list()
events = dict()

def make_path(input_location: str) -> str:
    """
    Function creates a path location for the given user input.

    :param input_location: Path to sanitize.
    :return: Sanitized path.
    """

    # Do nothing if the given location is an absolute path.
    if input_location[0] == "/":
        return input_location
    # Replace ~ with the home directory.
    elif input_location[0] == "~":
        return os.environ["HOME"] + input_location[1:]
    # Assume we have a given relative path.
    return os.path.dirname(os.path.abspath(__file__)) + "/" + input_location


def sigterm_handler(signum, frame):
    """
    Signal handler for sigterm to gracefully shutdown threads.

    :param signum:
    :param frame:
    """

    logging.info("Shutting down threads.")
    for account in accounts:
        account.exit()
    logging.info("Waiting for threads to exit.")
    time.sleep(2)


if __name__ == '__main__':

    # Register sigterm handler to gracefully shutdown the service.
    signal.signal(signal.SIGTERM, sigterm_handler)

    # Parse log settings from file.
    config_root = None
    try:
        config_root = xml.etree.ElementTree.parse(make_path("config/config.xml")).getroot()

        log_file = make_path(config_root.find("general").attrib["logFile"])
        temp_loglevel = config_root.find("general").attrib["logLevel"].upper()
        if temp_loglevel == "DEBUG":
            log_level = logging.DEBUG
        elif temp_loglevel == "INFO":
            log_level = logging.INFO
        elif temp_loglevel == "WARNING":
            log_level = logging.WARNING
        elif temp_loglevel == "ERROR":
            log_level = logging.ERROR
        elif temp_loglevel == "CRITICAL":
            log_level = logging.CRITICAL
        else:
            raise ValueError("Unknown log level '%s'." % temp_loglevel)

        # Initialize logging.
        logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s",
                            datefmt="%m/%d/%Y %H:%M:%S",
                            filename=log_file,
                            level=log_level)
    except Exception as e:
        print(e)
        sys.exit(1)

    # Parse config file.
    try:
        check_interval = int(config_root.find("general").attrib["checkInterval"])
        if check_interval <= 0:
            raise ValueError("Check interval has to be larger than 0.")

        # Parse events.
        for item in config_root.find("events").iterfind("event"):
            id = int(item.attrib["id"])
            event_type = item.attrib["type"]

            event = None

            # Parse lightweightpush Event.
            if event_type.upper() == "LIGHTWEIGHTPUSH":

                username = item.attrib["username"]
                password = item.attrib["password"]
                shared_secret = item.attrib["sharedSecret"]
                channel = item.attrib["channel"]

                event = EventLightweightPush(id, username, password, shared_secret, channel)

            # Unknown event type reached.
            else:
                raise ValueError("Unknown event type '%s'." % event_type)

            # Check if the event id is unique.
            if event.id in events.keys():
                raise ValueError("Event id '%d' not unique." % event.id)

            events[event.id] = event

        # Parse accounts.
        for item in config_root.find("accounts").iterfind("account"):

            name = item.attrib["name"]
            csv = make_path(item.attrib["csvFile"])
            user = item.attrib["user"]
            if item.attrib["passwordType"].upper() == "PLAIN":
                password = item.attrib["password"]
            elif item.attrib["passwordType"].upper() == "BASE64":
                password = base64.b64decode(item.attrib["password"].encode("utf-8")).decode('utf-8')
            else:
                raise ValueError("Unknown password type '%s'." % item.attrib["passwordType"])
            iban = item.attrib["iban"].strip().replace(" ", "")
            blz = item.attrib["blz"]
            url = item.attrib["fintsURL"]

            if os.path.isfile(csv):
                raise ValueError("No file '%s'." % csv)

            account = Account(name, user, password, blz, iban, url, csv)

            # Register all events.
            for event_xml in item.iterfind("event"):
                event_id = int(event_xml.text)
                if event_id not in events.keys():
                    raise ValueError("Event id '%d' does not exist." % event_id)
                account.register_event(events[event_id])

            accounts.append(account)

    except Exception as e:
        logging.exception("Not able to parse config file.")
        sys.exit(1)

    # Start monitoring of accounts.
    while True:

        logging.debug("Starting new processing round.")

        for account in accounts:
            logging.debug("Checking account '%s' with IBAN '%s'." % (account.name, account.iban))
            try:
                account.check()
                account.clean_up()
            except Exception as e:
                logging.exception("Not able to process account '%s' with IBAN '%s'." % (account.name, account.iban))

        logging.debug("Waiting %d seconds until next processing round." % check_interval)
        time.sleep(check_interval)
