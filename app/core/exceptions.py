class ClinicAIError(Exception):
    """Base exception for AI service."""


class LLMServiceError(ClinicAIError):
    """Raised when Ollama/LLM call fails."""


class BackendClientError(ClinicAIError):
    """Raised when clinic-backend API call fails."""
