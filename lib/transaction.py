import datetime
from typing import Any


class SimpleTransaction(object):
    """
    Contains a single transaction in a simplified form.
    """

    def __init__(self, name: str, iban: str, amount: float, currency: str, date: datetime.date, subject: str):
        self.currency = currency.upper()
        self.amount = amount
        self.name = name
        self.iban = iban.upper()
        self.date = date
        self.subject = subject

    def __eq__(self, other: Any) -> bool:
        if type(self) != type(other):
            return False
        if (self.currency == other.currency
           and self.amount == other.amount
           and self.name == other.name
           and self.iban == other.iban
           and self.date == other.date
           and self.subject == other.subject):
            return True
        else:
            return False

    def __hash__(self) -> int:
        return hash((self.currency, self.amount, self.name, self.iban, self.date, self.subject))

    def __str__(self) -> str:
        date_str = self.date.strftime("%Y-%m-%d")
        final_str = "%s: " % date_str
        if self.amount < 0:
            final_str = "%s: %.2f %s to %s (%s) with subject '%s'" % (date_str,
                                                                    self.amount * (-1),
                                                                    self.currency,
                                                                    self.iban,
                                                                    self.name,
                                                                    self.subject)
        else:
            final_str = "%s: %.2f %s from %s (%s) with subject '%s'" % (date_str,
                                                                      self.amount,
                                                                      self.currency,
                                                                      self.iban,
                                                                      self.name,
                                                                      self.subject)

        return final_str


class AllowedTransaction(object):
    """
    A whitelisted transaction (or rule).
    """

    def __init__(self, desc: str, iban: str, amount: float, currency: str, start_d: int, end_d: int):
        self.description = desc
        self.currency = currency.upper()
        self.amount = amount
        self.iban = iban.upper()
        self.start_day = start_d
        self.end_day = end_d

    def __eq__(self, other: Any) -> bool:
        if type(self) != type(other):
            return False
        if (self.currency == other.currency
           and self.description == other.description
           and self.amount == other.amount
           and self.iban == other.iban
           and self.start_day == other.start_day
           and self.end_day == other.end_day):
            return True
        return False

    def __hash__(self) -> int:
        return hash((self.description,
                     self.iban,
                     self.amount,
                     self.currency,
                     self.start_day,
                     self.end_day))

    def check_allowed(self, transaction: SimpleTransaction) -> bool:
        """
        Checks if the given transaction object fits to this rule.

        :param transaction: transaction object to check.
        :return: True if the given transaction fits to this rule.
        """

        year = datetime.date.today().year
        month = datetime.date.today().month
        start_date = datetime.date(year, month, self.start_day)
        end_date = datetime.date(year, month, self.end_day)

        if (start_date <= transaction.date <= end_date
           and self.amount == transaction.amount
           and self.currency == transaction.currency
           and self.iban == transaction.iban):
            return True
        return False


