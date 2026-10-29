from typing import Any

from fastapi.testclient import TestClient as FastAPITestClient
from httpx2 import Cookies


class TestClient(FastAPITestClient):
    def request(
        self,
        method: str,
        url: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        request_cookies = kwargs.pop("cookies", None)
        if request_cookies is None:
            return super().request(method, url, *args, **kwargs)

        original_cookies = self.cookies
        self.cookies = Cookies(original_cookies)
        self.cookies.update(request_cookies)
        response = None
        try:
            response = super().request(method, url, *args, **kwargs)
            return response
        finally:
            response_cookies = response.cookies if response is not None else None
            self.cookies = original_cookies
            if response_cookies is not None:
                self.cookies.update(response_cookies)
