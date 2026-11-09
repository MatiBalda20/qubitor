"""Errores de la integración con GitHub y Clerk, con el código HTTP que devuelve la API.

No se usa 401 para los problemas con GitHub: el frontend interpreta un 401 como
que venció la sesión de Qubitor y manda al login, aunque la sesión esté bien.
"""


class GitHubError(Exception):
    """Base de los errores de la integración. `status_code` es lo que responde la API."""

    status_code = 502

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class GitHubNotLinked(GitHubError):
    """El usuario no tiene una cuenta de GitHub conectada en Clerk, o su token venció."""

    status_code = 409


class GitHubForbidden(GitHubError):
    """El token no tiene permiso para ese recurso (scopes, SSO de la organización)."""

    status_code = 403


class GitHubNotFound(GitHubError):
    """El repo no existe o el usuario no lo puede ver."""

    status_code = 404


class GitHubRateLimited(GitHubError):
    """Se agotó la cuota de la API de GitHub para ese token."""

    status_code = 429


class GitHubUnavailable(GitHubError):
    """GitHub o Clerk no respondieron, o la integración no está configurada."""

    status_code = 503
