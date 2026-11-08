"""Custom exceptions for VALKYRIE."""


class VALKYRIEError(Exception):
    """Base exception for all VALKYRIE errors."""

    pass


class PhysicsViolationError(VALKYRIEError):
    """Raised when a design violates fundamental physics constraints."""

    pass


class ConvergenceError(VALKYRIEError):
    """Raised when iterative sizing loop fails to converge."""

    pass


class InvalidRequirementError(VALKYRIEError):
    """Raised when mission requirements are invalid or contradictory."""

    pass


class ComponentNotFoundError(VALKYRIEError):
    """Raised when a required component cannot be found in the database."""

    pass


class InsufficientDataError(VALKYRIEError):
    """Raised when insufficient data is available for analysis."""

    pass
