from .transaction import SimpleTransaction
import logging
from lightweightpush import LightweightPush
from lightweightpush import ErrorCodes as LPErrorCodes
import threading


class Event(object):
    """
    Abstract object for events that can be triggered by an unknown transaction.
    """

    def __init__(self, id: int):
        self.id = id

    def trigger(self, account, transaction: SimpleTransaction):
        """
        Triggers the event.

        :param account: account object the transaction belongs to.
        :param transaction: transaction object that triggered the event.
        """
        raise NotImplementedError("Not yet implemented.")


class EventLightweightPush(Event):
    """
    Event that triggers a push notification via the AlertR Push Notification service.
    """

    def __init__(self, id: int, username: str, password: str, shared_secret: str, channel: str):
        """

        :param id: id of the event.
        :param username: username for the lightweight push service.
        :param password: password for the lightweight push service.
        :param shared_secret: shared secret used to encrypt the message.
        :param channel: channel the message is sent to.
        """
        super().__init__(id)

        self.push_service = LightweightPush(username, password, shared_secret)
        self.channel = channel

    def _pretty_iban(self, iban: str) -> str:
        """
        Transforms given IBAN string to a prettified IBAN string.

        :param iban: IBAN string.
        :return: prettified IBAN string.
        """

        new_iban = ""
        for i in range(len(iban)):
            if i % 4 == 0 and i != 0:
                new_iban += " "
            new_iban += iban[i]
        return new_iban

    def _send(self, subject, msg):
        """
        Internal function that sends message to lightweight push server.

        :param subject: subject of the notification.
        :param msg: message body of the notification.
        """
        error_code = self.push_service.send_msg(subject, msg, self.channel)

        if error_code == LPErrorCodes.NO_ERROR:
            pass
        elif error_code == LPErrorCodes.DATABASE_ERROR:
            logging.error("Database error on lightweight push server. Please contact administrator.")
        elif error_code == LPErrorCodes.AUTH_ERROR:
            logging.error("Lightweight push authentication failed. Are the user credentials wrong?")
        elif error_code == LPErrorCodes.ILLEGAL_MSG_ERROR:
            logging.error("Lightweight push message malformed. "
                          + "Please upgrade lightweight push package.")
        elif error_code == LPErrorCodes.VERSION_MISSMATCH:
            logging.error("Version from lightweight push package and server do not match. "
                          + "Please upgrade lightweight push package.")
        elif error_code == LPErrorCodes.CLIENT_CONNECTION_ERROR:
            logging.error("Lightweight push Client could not connect to the server.")
        else:
            logging.error("Sending lightweight push message failed with error code: %d" % error_code)

    def trigger(self, account, transaction: SimpleTransaction):
        """
        Triggers the event by sending a message via lightweight push.

        :param account: account object the transaction belongs to.
        :param transaction: transaction object that triggered the event.
        """

        amount = transaction.amount
        if amount < 0:
            subject = "Transaction: %.2f %s withdrawn." % ((amount * (-1)), transaction.currency)
        else:
            subject = "Transaction: %.2f %s received." % (amount, transaction.currency)

        msg = "Transaction on account %s (%s).\n\n" % (account.name, self._pretty_iban(account.iban))
        msg += "Name: %s\n"  % transaction.name
        msg += "IBAN: %s\n" % self._pretty_iban(transaction.iban)
        msg += "Amount: %.2f %s\n" % (transaction.amount, transaction.currency)
        msg += "Subject: %s\n" % transaction.subject
        date_str = transaction.date.strftime("%Y-%m-%d")
        msg += "Date: %s\n" % date_str

        # Send message via thread to be non-blocking.
        thread = threading.Thread(target=self._send, args=(subject, msg))
        thread.start()
