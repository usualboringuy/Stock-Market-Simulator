class DBError(Exception):
    pass


class InvalidOrderError(DBError):
    pass


class InsufficientFundsError(DBError):
    pass


class InsufficientQuantityError(DBError):
    pass


class TransactionUnsupportedError(DBError):
    pass
