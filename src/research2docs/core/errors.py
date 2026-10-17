"""Safe typed failures; exceptions never contain source material or SQL parameters."""


class Research2DocsError(Exception):
    """An application failure safe to display as plain text."""


class ConfigurationError(Research2DocsError):
    pass


class StorageError(Research2DocsError):
    pass


class SchemaError(StorageError):
    pass


class ProjectNotFound(Research2DocsError):
    pass


class RevisionConflict(Research2DocsError):
    pass


class InputError(Research2DocsError):
    pass


class OllamaError(Research2DocsError):
    pass


class IngestionError(Research2DocsError):
    def __init__(
        self,
        reason: str,
        message: str = "Unable to process this document. Review the file and try again.",
    ) -> None:
        super().__init__(message)
        self.reason = reason


class GenerationError(Research2DocsError):
    pass


class VerificationError(Research2DocsError):
    pass


class ExportError(Research2DocsError):
    pass
