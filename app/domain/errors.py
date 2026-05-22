class DomainError(Exception):
    code = "domain_error"
    public_message = "The request could not be completed."
    status_code = 400


class NotFoundError(DomainError):
    code = "not_found"
    public_message = "The requested resource was not found."
    status_code = 404


class PermissionDenied(DomainError):
    code = "permission_denied"
    public_message = "You do not have permission to perform this action."
    status_code = 403


class ToolFailure(DomainError):
    code = "tool_failure"
    public_message = "A chatbot tool is temporarily unavailable."
    status_code = 503

