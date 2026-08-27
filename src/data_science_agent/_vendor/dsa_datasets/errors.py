class DatasetError(ValueError):
    pass


class ValidationError(DatasetError):
    pass


class UnsupportedFormatError(DatasetError):
    pass


class FileTooLargeError(DatasetError):
    pass
