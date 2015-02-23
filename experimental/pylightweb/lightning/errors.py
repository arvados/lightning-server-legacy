class MissingLocusError(Exception):
    """
        Raised when the query given is valid, but no loci were found to match it
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class LocusOutOfRangeException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class InvalidGenomeError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class StatisticsException(Exception):
    pass

class MissingStatisticsError(StatisticsException):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ExistingStatisticsError(StatisticsException):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class EmptyPathError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class TileLibraryValidationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class ParseException(Exception):
    pass

class NoteParseError(ParseException):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
