from fints.client import FinTS3PinTanClient
from .rules import Rules
from .transaction import SimpleTransaction
from .event import Event
import datetime
import logging


class Account(object):
    """
    Manages one account that is monitored.
    """

    def __init__(self, name: str, user: str, password: str, blz: str, iban: str, url: str, csv_file: str):
        """

        :param name: name of this account.
        :param user: user used to login to the bank.
        :param password: password used to login to the bank
        :param blz: blz of this account (used in Germany, do not know what banks outside Germany use here)
        :param iban: iban of the account.
        :param url: url to the FinTS access point.
        :param csv_file: file location of the rules for this account for whitelisted transactions.
        """
        self.name = name
        self.user = user
        self.password = password
        self.blz = blz
        self.iban = iban.strip().replace(" ", "").upper()
        self.url = url

        # The transactions of the last x days are fetched from the server.
        self.delta_days = 5

        # Start rules daemon.
        self.rules = Rules(csv_file)
        self.rules.daemon = True
        self.rules.start()

        # A set of transactions that already triggered an event.
        self.triggered_transactions = set()

        # List of events that are triggered when an unknown transaction is discovered.
        self.events = list()

    def exit(self):
        """
        Exits the threads of the account object.
        """

        self.rules.exit()

    def check(self):
        """
        Fetches the last transactions from the account and checks if they are unknown.
        """

        fints_client = FinTS3PinTanClient(self.blz, self.user, self.password, self.url)
        accounts = fints_client.get_sepa_accounts()

        # Extract account.
        account = None
        for temp_account in accounts:
            if temp_account.iban.upper() == self.iban:
                account = temp_account
                break
        if account is None:
            raise ValueError("Account '%s' with IBAN '%s' not found." % (self.name, self.iban))

        # Get all transaction from the last 5 days.
        start_date = datetime.date.today() - datetime.timedelta(days=self.delta_days)
        transactions = fints_client.get_transactions(account,
                                                     start_date,
                                                     datetime.date.today())

        for transaction in transactions:
            currency = str(transaction.data["currency"])
            amount = float(transaction.data["amount"].amount)
            date = transaction.data["date"]
            if not isinstance(date, datetime.date):
                raise ValueError("Account '%s' with IBAN '%s' contains "
                    % (self.name, self.iban)
                    + "illegal data")
            subject = str(transaction.data["purpose"])
            rcpt_name = str(transaction.data["applicant_name"])
            rcpt_iban = str(transaction.data["applicant_iban"])
            obj = SimpleTransaction(rcpt_name,
                                    rcpt_iban,
                                    amount,
                                    currency,
                                    date,
                                    subject)

            if obj in self.triggered_transactions:
                continue

            if not self.rules.check_allowed(obj):

                logging.debug("Transaction '%s' not whitelisted. Triggering event." % str(obj))

                # Trigger events.
                for event in self.events:
                    event.trigger(self, obj)

                self.triggered_transactions.add(obj)

    def clean_up(self):
        """
        Cleans up the account object (e.g., deletes old processed transactions).
        """

        oldest_date = datetime.date.today() - datetime.timedelta(days=(self.delta_days + 10))
        for obj in list(self.triggered_transactions):
            if obj.date < oldest_date:

                logging.debug("Removing '%s' from triggered list." % str(obj))

                self.triggered_transactions.remove(obj)

    def register_event(self, event: Event):
        """
        Registers an event that is triggered as soon as an unknown transaction is found.

        :param event: event object to register.
        """
        self.events.append(event)