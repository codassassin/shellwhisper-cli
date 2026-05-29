from textual.widgets import Header, Footer, Input, Label, RichLog, Button
from textual.screen import Screen
from textual.containers import Vertical, Horizontal

from rich.markup import escape

from src.events import NewWhisperReceived
from src.components.sidebar import Sidebar
from src.screens.room_action_screen import RoomActionScreen
from src.screens.security_screen import SecurityScreen
from src.screens.private_whisper_screen import PrivateWhisperPromptScreen

import json
import base64
import os

from datetime import datetime

class ChatScreen(Screen):
    TITLE = "ShellWhisper"
    BINDINGS = [
        ("ctrl+l", "logout", "Logout"),
        ("ctrl+d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def compose(self):
        yield Header()

        with Horizontal():
            yield Sidebar(id="sidebar")

            with Vertical(id="chat-view-container"):
                yield Label("Select a room to start whispering...", id="empty-view")

                with Vertical(id="chat-view"):
                    yield RichLog(id="chat_log", highlight=True, markup=True)
                    yield Input(
                        placeholder="Type a whisper or @help for commands...",
                        id="chat_input",
                    )

        yield Footer()

    async def on_mount(self) -> None:
        self.sub_title = f"Logged in as {self.app.current_user}"
        self._current_subscription_id = None
        self.current_room_messages = []
        self._pending_room_data = None
        self.rooms = []

        self.app.connect_websocket()
        self.set_interval(5.0, self.refresh_rooms)
        self.run_worker(self._load_rooms_worker, thread=True)

    # --- Sidebar / room loading --- #

    def _load_rooms_worker(self) -> None:
        rooms = self.fetch_user_rooms()
        self.rooms = rooms
        self.app.call_from_thread(self.update_sidebar_data, rooms)

    def refresh_rooms(self) -> None:
        self.run_worker(self._load_rooms_worker, thread=True)

    def update_sidebar_data(self, rooms) -> None:
        sidebar = self.query_one("#sidebar")
        self.app.run_worker(sidebar.update_rooms(rooms))

    ### BUTTON HANDLING ###

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_room_mgmt":
            self.app.push_screen(RoomActionScreen(), self._on_room_action_dismissed)
        elif event.button.id == "btn_private":
            self.app.push_screen(PrivateWhisperPromptScreen(), self._on_private_chat_dismissed)
        elif event.button.id == "logout_btn":
            self.logout_process()
        elif "room-link" in event.button.classes:
            room_id = event.button.id.replace("room_", "")
            self.switch_to_room(room_id)

    # --- Private whisper flow --- #

    def _on_private_chat_dismissed(self, target_username: str | None) -> None:
        if not target_username:
            return

        self.run_worker(lambda: self._start_private_chat_worker(target_username), thread=True)

    def _start_private_chat_worker(self, target_username: str) -> None:
        try:
            response = self.app.api.start_private_chat(target_username)

            if response.status_code in (200, 201):
                room_data = response.json()

                self.app.call_from_thread(
                    self.app.notify,
                    f"Private channel open with {escape(target_username)}!",
                    severity="success",
                )

                rooms = self.fetch_user_rooms()
                self.rooms = rooms
                self.app.call_from_thread(self.update_sidebar_data, rooms)
                self.app.call_from_thread(self._auto_switch_to_room, room_data.get("id"))

            elif response.status_code == 404:
                self.app.call_from_thread(
                    self.app.notify,
                    f"User '{escape(target_username)}' not found!",
                    severity="error"
                )
            else:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Action failed ({response.status_code}): {escape(response.text)}",
                    severity="error",
                )
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify,
                f"Network error: {escape(str(e))}",
                severity="error",
            )

    ### RoomActionScreen ###

    def _on_room_action_dismissed(self, data: dict | None) -> None:
        if not data:
            return

        self._pending_room_data = data
        self.app.push_screen(
            SecurityScreen(action=data["action"], room_name=data["name"]),
            self._on_security_action_dismissed,
        )

    def _on_security_action_dismissed(self, security_key: str | None) -> None:
        if not security_key or not self._pending_room_data:
            return

        action = self._pending_room_data["action"]
        room_name = self._pending_room_data["name"]
        self._pending_room_data = None

        if action == "create_btn":
            self._do_create_room(room_name, security_key)
        elif action == "join_btn":
            self._do_join_room(room_name, security_key)

    ### CREATE ROOM ###

    def _do_create_room(self, room_name: str, security_key: str) -> None:
        response = self.app.api.create_room(room_name, security_key)

        if response.status_code == 201:
            room_data = response.json()
            self.app.notify(f"Room '{escape(room_name)}' created!", severity="success")
            self.refresh_rooms()
            self.call_after_refresh(self._auto_switch_to_room, room_data.get("id"))
        elif response.status_code == 400:
            self.app.notify(
                escape(response.text) or "A room with that name already exists.",
                severity="error",
            )
        elif response.status_code == 404:
            self.app.notify("User account not found on server.", severity="error")
        else:
            self.app.notify(
                f"Failed to create room ({response.status_code}): {escape(response.text)}",
                severity="error",
            )

    ### JOIN ROOM ###

    def _do_join_room(self, room_name: str, security_key: str) -> None:
        response = self.app.api.join_room(room_name, security_key)

        if response.status_code == 200:
            room_data = response.json()
            self.app.notify(f"Joined '{escape(room_name)}'!", severity="success")
            self.refresh_rooms()
            self.call_after_refresh(self._auto_switch_to_room, room_data.get("id"))
        elif response.status_code == 401:
            self.app.notify("Wrong security key - try again.", severity="error")
        elif response.status_code == 404:
            self.app.notify(
                f"Room '{escape(room_name)}' not found. Check the name and try again.",
                severity="error",
            )
        else:
            self.app.notify(
                f"Failed to join room ({response.status_code}): {escape(response.text)}",
                severity="error",
            )

    ### DELETE ROOM ###

    def _do_delete_room(self, room_id: str, security_str: str = "") -> None:
        room = next((r for r in self.rooms if r["id"] == room_id), None)
        room_name = room["roomName"] if room else room_id

        try:
            response = self.app.api.delete_room(room_id, security_str)

            if response.status_code == 200:
                # self.app.notify(f"Room '{escape(room_name)}' deleted successfully.", severity="success")
                self._stomp_unsubscribe()
                self.app.current_room_id = None
                self.current_room_messages = []
                self.app.file_cache.clear()
                self._clear_to_empty_viewport()
                self.refresh_rooms()
            elif response.status_code == 403:
                self.app.notify("You don't have permission to delete this room.", severity="error")
            elif response.status_code == 404:
                self.app.notify("Room not found.", severity="error")
            else:
                self.app.notify(
                    f"Failed to delete room ({response.status_code}): {escape(response.text)}",
                    severity="error"
                )
        except Exception as e:
            self.app.notify(f"Network error: {escape(str(e))}", severity="error")

    ### LEAVE ROOM ###

    def _do_leave_room(self, room_id: str) -> None:
        room = next((r for r in self.rooms if r["id"] == room_id), None)
        room_name = room["roomName"] if room else room_id

        try:
            response = self.app.api.leave_room(room_id)

            if response.status_code == 200:
                self.app.notify(f"Left '{escape(room_name)}'.", severity="success")
                self._stomp_unsubscribe()
                self.app.current_room_id = None
                self.current_room_messages = []
                self.app.file_cache.clear()
                self._clear_to_empty_viewport()
                self.refresh_rooms()
            elif response.status_code == 404:
                self.app.notify("Room not found.", severity="error")
            else:
                self.app.notify(
                    f"Failed to leave room ({response.status_code}):  "
                )
        except Exception as e:
            self.app.notify(f"Network error: {escape(str(e))}", severity="error")

    ### AUTO SWITCH ROOM ###

    def _auto_switch_to_room(self, room_id: str | None) -> None:
        if not room_id:
            return

        room = next((r for r in self.rooms if r["id"] == room_id), None)
        if room:
            self.switch_to_room(room_id)
        else:
            rooms = self.fetch_user_rooms()
            self.rooms = rooms
            self.call_after_refresh(self.switch_to_room, room_id)

    ### ROOM SWITCHING ###

    def switch_to_room(self, room_id: str) -> None:
        self._stomp_unsubscribe()
        self.app.file_cache.clear()
        self.current_room_messages = []

        self.app.current_room_id = room_id
        room = next((r for r in self.rooms if r["id"] == room_id), None)

        if not room:
            self.app.notify("Room details not found", severity="error")
            return

        self._set_active_room_button(room_id)
        self._stomp_subscribe(room_id)

        self.query_one("#chat-view").styles.display = "block"
        self.query_one("#empty-view").styles.display = "none"
        self.query_one("#chat_log").clear()

        self.run_worker(lambda: self._fetch_messages_worker(room_id), thread=True)

    def _fetch_messages_worker(self, room_id: str) -> None:
        try:
            response = self.app.api.fetch_messages(room_id)

            if response.status_code == 200:
                messages = response.json()
                self.current_room_messages = messages

                self.app.call_from_thread(self._render_messages, messages)
            else:
                self.app.call_from_thread(
                    self.app.notify,
                    f"Failed to load message history",
                    severity="error"
                )
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify,
                f"Error fetching messages: {escape(str(e))}",
                severity="error"
            )

    def _render_messages(self, messages: list) -> None:
        chat_log = self.query_one("#chat_log", RichLog)
        for msg in messages:
            self._write_message(chat_log, msg)

    # --- STOMP Subscribe / Unsubscribe --- #

    def _stomp_subscribe(self, room_id: str) -> None:
        if self.app.stomp_conn and self.app.stomp_conn.sock:
            self._current_subscription_id = room_id
            subscribe_frame = (
                f"SUBSCRIBE\n"
                f"id:sub-{room_id}\n"
                f"destination:/topic/room/{room_id}\n"
                f"ack:auto\n\n\x00"
            )
            try:
                self.app.stomp_conn.send(subscribe_frame)
            except Exception as e:
                self.app.notify(
                    f"Subscribe failed: {escape(str(e))}",
                    severity="error",
                )

    def _stomp_unsubscribe(self) -> None:
        if self._current_subscription_id and self.app.stomp_conn and self.app.stomp_conn.sock:
            unsubscribe_frame = (
                f"UNSUBSCRIBE\n"
                f"id:sub-{self._current_subscription_id}\n\n\x00"
            )
            try:
                self.app.stomp_conn.send(unsubscribe_frame)
            except Exception:
                pass
            finally:
                self._current_subscription_id = None

    def _set_active_room_button(self, room_id: str) -> None:
        try:
            for btn in self.query(".room-link").results(Button):
                btn.remove_class("active")
            self.query_one(f"#room_{room_id}").add_class("active")
        except Exception:
            pass

    ### MESSAGE DISPLAY ###

    def _write_message(self, chat_log: RichLog, msg: dict) -> None:
        sender = msg.get("sender", "System")
        content = msg.get("content", "")

        #Timestamp
        ts_raw = msg.get("timeStamp") or msg.get("messageTime", "")
        ts_str = ""

        if ts_raw:
            try:
                dt = datetime.fromisoformat(str(ts_raw))

                if dt.date() == datetime.now().date():
                    ts_str = f" [dim]{dt.strftime('%H:%M')}[/]"
                else:
                    ts_str = f" [dim]{dt.strftime('%d %b, %H:%M')}[/]"
            except Exception:
                pass

        # File message
        if content.startswith("FILE:"):
            try:
                parts = content.split(":", 2)
                if len(parts) >= 2:
                    filename = parts[1]
                    encoded_data = parts[2] if len(parts) > 2 else ""

                    if encoded_data:
                        self.app.file_cache[filename] = encoded_data

                    try:
                        size_kb = round(len(base64.b64decode(encoded_data)) / 1024, 1)
                    except Exception:
                        size_kb = 0.0

                    safe_filename = escape(filename)
                    display_content = (
                        f"📄 [bold]{safe_filename}[/] [dim]({size_kb} KB)[/] "
                        f"[@click=app.download_file('{safe_filename}')][underline cyan][ download ][/]"
                    )
                else:
                    display_content = "📄 [italic][Malformed File Whisper][/]"
            except Exception:
                display_content = "📄 [italic][Error processing File Whisper][/]"
        else:
            display_content = escape(content)

        safe_sender = escape(sender)
        if sender == self.app.current_user:
            chat_log.write(f"[bold cyan]You:[/]{ts_str} {display_content}")
        else:
            chat_log.write(f"[bold green]{safe_sender}:[/]{ts_str} {display_content}")

    ### CLEAR VIEWPORT ###

    def _clear_to_empty_viewport(self) -> None:
        try:
            self.query_one("#chat-view").styles.display = "none"
            self.query_one("#empty-view").styles.display = "block"
            self.query_one("#chat_log").clear()
            self.current_room_messages = []
        except Exception:
            pass

    ### DATA FETCHERS ###

    def fetch_user_rooms(self) -> list:
        try:
            response = self.app.api.fetch_rooms()
            if response.status_code == 200:
                return response.json()
            else:
                self.app.notify(
                    f"Failed to load rooms ({response.status_code})",
                    severity="error",
                )
        except Exception as e:
            self.app.notify(
                f"Failed to load rooms {escape(str(e))}",
                severity="error",
            )

        return []

    ### INPUT / SEND ###

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        self.query_one('#chat_input').value = ""

        if not raw:
            return

        if raw.lower() == "@help":
            self._show_help()
            return

        if not self.app.current_room_id:
            self.app.notify("Select a room first.", severity="warning")
            return

        if raw.startswith("@"):
            self._handle_command(raw)
        else:
            self._send_message(raw)

    def _show_help(self) -> None:
        try:
            chat_log = self.query_one("#chat_log", RichLog)
            if self.query_one("#chat_log").styles.display == "none":
                raise Exception("chat not visible")
        except Exception:
            self.app.notify(
                "@copy:/path send file | @get:name download | @delete delete room | @leave leave room",
                severity="information"
            )
            return

        chat_log.write("[bold yellow]-- ShellWhisper Commands --[/]")
        chat_log.write(" [cyan]@copy:/path/to/file[/]  send any file to this room")
        chat_log.write(" [cyan]@get:filename[/]        download a file from room history")
        chat_log.write(" [cyan]@save:filename[/]       alias for @get")
        chat_log.write(" [cyan]@delete[/]              delete the current room")
        chat_log.write(" [cyan]@leave[/]               leave the current room")
        chat_log.write(" [cyan]@help[/]                show this message")

    def _handle_command(self, raw: str) -> None:
        chat_log = self.query_one("#chat_log", RichLog)

        if raw.lower().startswith("@copy:"):
            file_path = os.path.expanduser(raw[6:].strip())

            if not file_path:
                self.app.notify("Usage: @copy:/path/to/file", severity="warning")
                return
            if not os.path.isfile(file_path):
                self.app.notify(f"File not found: {escape(file_path)}", severity="error")
                return

            try:
                with open(file_path, "rb") as f:
                    binary_data = f.read()

                if len(binary_data) > 5 * 1024 * 1024:
                    self.app.notify("File too large - 5 MB maximum.", severity="error")
                    return

                encoded = base64.b64encode(binary_data).decode("utf-8")
                filename = os.path.basename(file_path)
                size_kb = round(len(binary_data) / 1024, 1)

                chat_log.write(f"[dim]Sending:[/] [bold]{escape(filename)}[/] [dim]({size_kb} KB)[/]")
                self._send_message(f"FILE:{filename}:{encoded}", filename=filename, is_file=True)

            except Exception as e:
                self.app.notify(f"@copy failed: {escape(str(e))}", severity="error")

        elif raw.lower().startswith("@get:") or raw.lower().startswith("@save:"):
            prefix_len = 5 if raw.lower().startswith("@get:") else 6
            target = raw[prefix_len:].strip()

            if not target:
                self.app.notify("Usage: @get:filename", severity="warning")
                return

            if target in self.app.file_cache:
                self.app.action_download_file(target)
                return

            found = False
            for msg in reversed(self.current_room_messages):
                c = msg.get("content", "")

                if c.startswith(f"FILE:{target}:"):
                    _, filename, data = c.split(":", 2)
                    self.app.file_cache[filename] = data
                    self.app.action_download_file(filename)
                    found = True
                    break

            if not found:
                self.app.notify(f"File '{escape(target)}' not found in whispers", severity="warning")

        elif raw.lower() == "@delete":
            room_id = self.app.current_room_id
            if not room_id:
                self.app.notify("Select an active room first.", severity="warning")
                return

            room = next((r for r in self.rooms if r["id"] == self.app.current_room_id), None)
            if not room:
                return

            if room.get("type") == "PRIVATE":
                self._do_delete_room(room_id, "")
            else:
                self._pending_room_data = {
                    "name": room["roomName"],
                    "action": "chat_command_delete",
                    "id": room_id
                }
                self.app.push_screen(
                    SecurityScreen(action="chat_command_delete", room_name=room["roomName"]),
                    self._on_delete_security_dismissed,
                )

        elif raw.lower() == "@leave":
            room_id = self.app.current_room_id
            if not room_id:
                self.app.notify("No active room selected.", severity="warning")
                return
            self._do_leave_room(room_id)

        elif raw.lower() == "@help":
            self._show_help()

        else:
            self.app.notify(
                f"Unknown command '{escape(raw)}'. Type @help for available commands.",
                severity="warning",
            )

    def _on_delete_security_dismissed(self, security_key: str | None) -> None:
        if not security_key or not self._pending_room_data:
            return

        room_id = self._pending_room_data.get("id")
        self._pending_room_data = None

        if room_id:
            self._do_delete_room(room_id, security_key)

    def _on_chat_command_security_dismissed(self, security_key: str | None) -> None:
        if not security_key or not self._pending_room_data:
            return

        action = self._pending_room_data["action"]
        room_id = self._pending_room_data.get("id")
        self._pending_room_data = None

        if action == "chat_command_delete" and room_id:
            self._do_delete_room(room_id, security_key)

    def _send_message(self, message_text: str) -> None:
        payload = {
            "sender": self.app.current_user,
            "content": message_text,
            "roomId": self.app.current_room_id,
            "messageTime": datetime.now().isoformat(),
        }

        frame = (
            f"SEND\n"
            f"destination:/app/sendMessage\n"
            f"content-type:application/json\n\n"
            f"{json.dumps(payload)}\x00"
        )

        if self.app.stomp_conn and self.app.stomp_conn.sock:
            try:
                self.app.stomp_conn.send(frame)
            except Exception as e:
                self.app.notify(
                    f"Failed to send message: {escape(str(e))}",
                    severity="error"
                )
        else:
            self.app.notify(
                f"Not connected - message not sent.",
                severity="error"
            )

    ### INCOMING REAL-TIME MESSAGES ###

    def on_new_whisper_received(self, event: NewWhisperReceived) -> None:
        data = event.data
        self.current_room_messages.append(data)
        chat_log = self.query_one("#chat_log", RichLog)
        self._write_message(chat_log, data)

    ### LOGOUT ###

    def action_logout(self) -> None:
        self.logout_process()

    def logout_process(self) -> None:
        from src.screens.login import LoginScreen

        self._stomp_unsubscribe()
        self.app._disconnect_websocket()
        self.app.access_token = None
        self.app.current_user = None
        self.app.current_room_id = None
        self.app.file_cache.clear()

        self.app.notify("Logged out successfully", severity="information")
        self.app.switch_screen(LoginScreen())
