import requests

class APIClient:
    BASE_URL = "http://localhost:8080/api/v1"

    def __init__(self, app):
        self.app = app

    def _get_headers(self):
        return {"Authorization": f"Bearer {self.app.access_token}"}
    
    def login(self, username, password):
        return requests.post(f"{self.BASE_URL}/auth/login", json={"username": username, "password": password})
    
    def fetch_rooms(self):
        return requests.get(f"{self.BASE_URL}/room/my-rooms", headers=self._get_headers())

    def fetch_messages(self, room_id: str):
        return requests.get(f"{self.BASE_URL}/messages/{room_id}", headers=self._get_headers())