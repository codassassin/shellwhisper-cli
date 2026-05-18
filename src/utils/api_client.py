import requests

class APIClient:
    BASE_URL = "http://localhost:8080/api/v1"

    def __init__(self, app):
        self.app = app

    def _get_headers(self):
        return {"Authorization": f"Bearer {self.app.access_token}"}

    def start_private_chat(self, target_username: str):
        return requests.post(
            f"{self.BASE_URL}/room/private/{target_username}",
            headers=self._get_headers(),
            timeout=5,
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

    def fetch_rooms(self):
        return requests.get(
            f"{self.BASE_URL}/room/my-rooms",
            headers=self._get_headers(),
            timeout=5,
        )

    def fetch_messages(self, room_id: str):
        return requests.get(
            f"{self.BASE_URL}/messages/{room_id}",
            headers=self._get_headers(),
            timeout=5,
        )

    def create_room(self, room_name: str, security_string: str):
        return requests.post(
            f"{self.BASE_URL}/room/new",
            json={"roomName": room_name, "rawSecurityString": security_string},
            headers=self._get_headers(),
            timeout=5,
        )

    def join_room(self, room_name: str, security_string: str):
        return requests.post(
            f"{self.BASE_URL}/room/join",
            json={"roomName": room_name, "rawSecurityString": security_string},
            headers=self._get_headers(),
            timeout=5,
        )
