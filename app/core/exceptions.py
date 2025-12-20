
class RedirectException(Exception):
    def __init__(self, url: str = "/auth", status_code: int = 307):
        self.url = url
        self.status_code = status_code
