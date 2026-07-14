"""Runtime exception hierarchy."""

class AnvikshaError(Exception):
    """Base exception for all runtime failures."""

class ConfigurationError(AnvikshaError):
    """Raised when runtime configuration is invalid."""

class PlanningError(AnvikshaError):
    """Raised when no valid execution plan can be created."""

class CapabilityError(AnvikshaError):
    """Raised when a capability cannot complete its work."""

class PolicyViolationError(AnvikshaError):
    """Raised when a policy blocks execution or response delivery."""

class PluginError(AnvikshaError):
    """Raised when a plugin cannot be loaded or validated."""
