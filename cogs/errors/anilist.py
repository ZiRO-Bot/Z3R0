class Error(Exception):
    pass


class NameNotFound(Error):
    pass


class NameTypeNotFound(Error):
    pass


class IdNotFound(Error):
    pass


class NoResultFound(Error):
    pass
