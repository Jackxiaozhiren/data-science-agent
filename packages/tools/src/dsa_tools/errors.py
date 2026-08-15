class ToolError(ValueError):
    pass


class ToolValidationError(ToolError):
    pass


class ToolExecutionError(ToolError):
    pass


class ToolNotFoundError(ToolError):
    pass
