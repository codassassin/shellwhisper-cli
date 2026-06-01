import requests
import os

class APIClient:
    # BASE_URL = "http://localhost:8080/api/v1"
    # BASE_URL = os.getenv(
    #     "SHELLWHISPER_API_URL",
    #     "https://shellwhisper-server.onrender.com/api/v1"
    # )
    # WS_URL = os.getenv(
    #     "SHELLWHISPER_WS_URL",
    #     "wss://shellwhisper-server.onrender.com/chat/websocket"
    # )

    BASE_URL = "https://shellwhisper-server.onrender.com/api/v1"
    WS_URL = "wss://shellwhisper-server.onrender.com/chat/websocket"

    def __init__(self, app):
        self.app = app

    def _get_headers(self):
        return {"Authorization": f"Bearer {self.app.access_token}"}

    def _make_auth_request(self, method, endpoint, **kwargs):
        url = f"{self.BASE_URL}{endpoint}"
        kwargs["headers"] = self._get_headers()
        kwargs.setdefault("timeout", 5)

        response = requests.request(method, url, **kwargs)

        if response.status_code == 401 and getattr(self.app, 'refresh_token', None):
            refresh_res = requests.post(
                f"{self.BASE_URL}/auth/refresh",
                json={"refreshToken": self.app.refresh_token},
                timeout=5
            )

            if refresh_res.status_code == 200:
                data = refresh_res.json()
                self.app.access_token = data.get("token")

                kwargs["headers"] = self._get_headers()

                return requests.request(method, url, **kwargs)
            else:
                self.app.call_from_thread(self.app.action_logout)

        return response


    def fetch_rooms(self):
        return self._make_auth_request(
            "GET",
            "/room/my-rooms",
        )

    def fetch_messages(self, room_id: str):
        return self._make_auth_request(
            "GET",
            f"/messages/{room_id}"
        )

    def create_room(self, room_name: str, security_string: str):
        return self._make_auth_request(
            "POST",
            "/room/new",
            json={"roomName": room_name, "rawSecurityString": security_string}
        )

    def join_room(self, room_name: str, security_string: str):
        return self._make_auth_request(
            "POST",
            "/room/join",
            json={"roomName": room_name, "rawSecurityString": security_string}
        )

    def delete_room(self, room_id: str, security_key: str = ""):
        return self._make_auth_request(
            "DELETE",
            f"/room/delete/{room_id}",
            params={"securityKey": security_key}
        )

    def leave_room(self, room_id: str):
        return self._make_auth_request(
            "DELETE",
            f"/room/{room_id}/leave",
            timeout=10
        )

    def start_private_chat(self, target_username: str):
        return self._make_auth_request(
            "POST",
            f"/room/private/{target_username}"
        )


    def login(self, username: str, password: str):
        return requests.post(
            f"{self.BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )

    def signup(self, username: str, email: str, password: str):
        return requests.post(
            f"{self.BASE_URL}/auth/signup",
            json={"username": username, "email": email, "password": password},
            timeout=5,
        )

    def logout_backend(self):
        if getattr(self.app, 'refresh_token', None):
            requests.post(
                f"{self.BASE_URL}/auth/logout",
                json={"refreshToken": self.app.refresh_token},
                headers=self._get_headers(),
                timeout=5
            )

    def request_password_reset(self, email: str):
        return requests.post(
            f"{self.BASE_URL}/auth/forgot-password",
            json={"email": email},
            timeout=5,
        )

    def confirm_password_reset(self, email: str, token: str, new_password: str):
        return requests.post(
            f"{self.BASE_URL}/auth/reset-password",
            json={"email": email, "token": token, "newPassword": new_password},
            timeout=5,
        )
