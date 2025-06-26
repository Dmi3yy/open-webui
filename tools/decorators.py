"""Utility decorators for custom tools."""


def deprecated(func):
    """Mark a tool function as deprecated.

    Deprecated tools are excluded from the generated OpenAI spec.
    """
    setattr(func, "__deprecated__", True)
    return func
