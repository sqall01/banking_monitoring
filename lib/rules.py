import csv
import threading
import hashlib
import time
import logging
from .transaction import AllowedTransaction, SimpleTransaction


class Rules(threading.Thread):
    """
    Manages the rules for an account and checks for changes in the file.
    """

    def __init__(self, file_location: str):
        """

        :param file_location: file location for the csv file.
        """
        threading.Thread.__init__(self)
        self.file_location = file_location
        self.allowed_transactions = set()
        self._lock = threading.Lock()

        # Flag to tell thread to exit.
        self._exit = False

        # Hash to check if the file has changed.
        self.file_hash = self._create_hash()

        self.import_csv()

    def _create_hash(self) -> str:
        """
        Creates md5 hash of the corresponding managed csv file.

        :return: md5 hash string of the csv file.
        """
        md5 = hashlib.md5()
        with open(self.file_location, 'rb') as fp:
            while True:
                data = fp.read(4096)
                if not data:
                    break
                md5.update(data)

        return md5.hexdigest()

    def check_allowed(self, transaction: SimpleTransaction) -> bool:
        """
        Checks if the given transaction is whitelisted by the rules.

        :param transaction: transaction object to check.
        :return: True if the given transaction is known.
        """
        with self._lock:
            return any(map(lambda x: x.check_allowed(transaction), self.allowed_transactions))

    def exit(self):
        """
        Signals the thread to exit.
        """
        self._exit = True

    def import_csv(self):
        """
        Imports the csv file for this rules and deletes all old rules.
        """

        transactions = set()
        try:
            with open(self.file_location, 'r') as fp:
                csv_reader = csv.reader(fp, quoting=csv.QUOTE_MINIMAL)
                is_header = True
                for row in csv_reader:
                    if is_header:
                        is_header = False
                        continue

                    desc = row[0]
                    iban = row[1].strip().replace(" ","")
                    amount = float(row[2].replace(",", "."))
                    currency = row[3].strip().replace(" ","")
                    start_day = int(row[4])
                    end_day = int(row[5])

                    transaction = AllowedTransaction(desc, iban, amount, currency, start_day, end_day)
                    transactions.add(transaction)

            # Replace old transactions.
            with self._lock:
                self.allowed_transactions = transactions

        except Exception as e:
            logging.exception("Parsing rules file '%s' failed." % self.file_location)

    def run(self):
        """
        Checks regularly if the csv file has changed and reloads it if it has.
        """
        while True:

            logging.debug("Checking rules file '%s'." % self.file_location)

            # Read file if the hash has changed.
            new_hash = self._create_hash()
            if new_hash != self.file_hash:

                logging.info("Reloading rules from file '%s'." % self.file_location)

                self.import_csv()
                self.file_hash = new_hash

            # Wait 60 seconds before checking file again.
            for _ in range(60):
                if self._exit:
                    logging.info("Exiting rules thread.")
                    return
                time.sleep(1)