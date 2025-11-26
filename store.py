from __future__ import annotations

import base64
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from werkzeug.security import generate_password_hash, check_password_hash

import database


@dataclass
class User:
    user_id: str
    username: str
    password_hash: str
    role: str = "user"
    created_at: datetime = field(default_factory=datetime.utcnow)
    access_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def generate_token(self) -> str:
        token = secrets.token_urlsafe(32)
        self.access_token = token
        self.token_expires_at = datetime.utcnow() + timedelta(days=30)
        return token

    def is_token_valid(self, token: str) -> bool:
        if not self.access_token or self.access_token != token:
            return False
        if self.token_expires_at and datetime.utcnow() > self.token_expires_at:
            return False
        return True


@dataclass
class Room:
    room_id: str
    room_name: str
    room_type: str
    password: Optional[str] = None
    media_source: str = "camera"
    audio_device_id: Optional[str] = None
    audio_device_label: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    participants: Dict[str, str] = field(default_factory=dict)
    latest_frame: Optional[bytes] = None
    latest_frame_mime: str = "image/jpeg"
    latest_audio_chunk: Optional[bytes] = None
    latest_audio_mime: str = "audio/webm"

    def to_dict(self) -> Dict[str, object]:
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "room_type": self.room_type,
            "has_password": self.password is not None,
            "media_source": self.media_source,
            "audio_device_id": self.audio_device_id,
            "audio_device_label": self.audio_device_label,
            "participants_count": len(self.participants),
            "created_at": self.created_at.isoformat(),
        }


class RoomStore:
    def __init__(self) -> None:
        database.init_database()
        
        self.rooms: Dict[str, Room] = {}
        self.remote_servers: Dict[str, Dict[str, object]] = {}
        self.users: Dict[str, User] = {}
        self.users_by_username: Dict[str, str] = {}
        self.users_by_token: Dict[str, str] = {}
        
        self._load_users_from_db()
        self._load_rooms_from_db()
        self._load_remote_servers_from_db()
        
        self._create_default_admin()

    def _load_users_from_db(self) -> None:
        users_data = database.load_users()
        for user_data in users_data.values():
            user = User(
                user_id=user_data["user_id"],
                username=user_data["username"],
                password_hash=user_data["password_hash"],
                role=user_data["role"],
                created_at=datetime.fromisoformat(user_data["created_at"]) if isinstance(user_data["created_at"], str) else user_data["created_at"],
                access_token=user_data.get("access_token"),
                token_expires_at=datetime.fromisoformat(user_data["token_expires_at"]) if user_data.get("token_expires_at") and isinstance(user_data["token_expires_at"], str) else user_data.get("token_expires_at"),
            )
            self.users[user.user_id] = user
            self.users_by_username[user.username] = user.user_id
            if user.access_token:
                self.users_by_token[user.access_token] = user.user_id
    
    def _load_rooms_from_db(self) -> None:
        rooms_data = database.load_rooms()
        for room_data in rooms_data.values():
            room = Room(
                room_id=room_data["room_id"],
                room_name=room_data["room_name"],
                room_type=room_data["room_type"],
                password=room_data.get("password"),
                media_source=room_data.get("media_source", "camera"),
                audio_device_id=room_data.get("audio_device_id"),
                audio_device_label=room_data.get("audio_device_label"),
                created_at=datetime.fromisoformat(room_data["created_at"]) if isinstance(room_data["created_at"], str) else room_data["created_at"],
                participants=room_data.get("participants", {}),
                latest_frame=room_data.get("latest_frame"),
                latest_frame_mime=room_data.get("latest_frame_mime", "image/jpeg"),
                latest_audio_chunk=room_data.get("latest_audio_chunk"),
                latest_audio_mime=room_data.get("latest_audio_mime", "audio/webm"),
            )
            self.rooms[room.room_id] = room
    
    def _load_remote_servers_from_db(self) -> None:
        self.remote_servers = database.load_remote_servers()
    
    def _save_user_to_db(self, user: User) -> None:
        user_data = {
            "user_id": user.user_id,
            "username": user.username,
            "password_hash": user.password_hash,
            "role": user.role,
            "created_at": user.created_at,
            "access_token": user.access_token,
            "token_expires_at": user.token_expires_at,
        }
        database.save_user(user_data)
    
    def _save_room_to_db(self, room: Room) -> None:
        room_data = {
            "room_id": room.room_id,
            "room_name": room.room_name,
            "room_type": room.room_type,
            "password": room.password,
            "media_source": room.media_source,
            "audio_device_id": room.audio_device_id,
            "audio_device_label": room.audio_device_label,
            "created_at": room.created_at,
            "participants": room.participants,
            "latest_frame": room.latest_frame,
            "latest_frame_mime": room.latest_frame_mime,
            "latest_audio_chunk": room.latest_audio_chunk,
            "latest_audio_mime": room.latest_audio_mime,
        }
        database.save_room(room_data)
    
    def _save_remote_server_to_db(self, room_id: str, server_data: Dict[str, object]) -> None:
        database.save_remote_server(room_id, server_data)
    
    def _create_default_admin(self) -> None:
        admin_username = "admin"
        if admin_username not in self.users_by_username:
            admin = User(
                user_id=str(uuid.uuid4()),
                username=admin_username,
                password_hash=generate_password_hash("admin"),
                role="admin",
            )
            self.users[admin.user_id] = admin
            self.users_by_username[admin_username] = admin.user_id
            self._save_user_to_db(admin)

    def create_user(self, username: str, password: str, role: str = "user") -> User:
        username = username.strip().lower()
        if not username:
            raise ValueError("Имя пользователя не может быть пустым")
        if not password:
            raise ValueError("Пароль не может быть пустым")
        if username in self.users_by_username:
            raise ValueError("Пользователь с таким именем уже существует")
        if role not in {"user", "admin"}:
            raise ValueError("Роль должна быть 'user' или 'admin'")

        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
        )
        self.users[user.user_id] = user
        self.users_by_username[username] = user.user_id
        self._save_user_to_db(user)
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        username = username.strip().lower()
        user_id = self.users_by_username.get(username)
        if user_id:
            return self.users.get(user_id)
        
        users_data = database.load_users()
        for user_data in users_data.values():
            if user_data.get("username", "").lower() == username:
                user_id = user_data["user_id"]
                return self.reload_user_from_db(user_id)
        
        return None

    def get_user_by_token(self, token: str) -> Optional[User]:
        user_id = self.users_by_token.get(token)
        if user_id:
            user = self.users.get(user_id)
            if user and user.is_token_valid(token):
                user_data = database.load_users().get(user_id)
                if user_data:
                    user.role = user_data["role"]
                return user
            del self.users_by_token[token]
        
        users_data = database.load_users()
        for user_data in users_data.values():
            if user_data.get("access_token") == token:
                user_id = user_data["user_id"]
                user = self.reload_user_from_db(user_id)
                if user and user.is_token_valid(token):
                    return user
        
        return None
    
    def reload_user_from_db(self, user_id: str) -> Optional[User]:
        user_data = database.load_users().get(user_id)
        if not user_data:
            return None
        
        user = User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            password_hash=user_data["password_hash"],
            role=user_data["role"],
            created_at=datetime.fromisoformat(user_data["created_at"]) if isinstance(user_data["created_at"], str) else user_data["created_at"],
            access_token=user_data.get("access_token"),
            token_expires_at=datetime.fromisoformat(user_data["token_expires_at"]) if user_data.get("token_expires_at") and isinstance(user_data["token_expires_at"], str) else user_data.get("token_expires_at"),
        )
        self.users[user.user_id] = user
        self.users_by_username[user.username] = user.user_id
        if user.access_token:
            self.users_by_token[user.access_token] = user.user_id
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if not user or not user.check_password(password):
            return None
        token = user.generate_token()
        self.users_by_token[token] = user.user_id
        self._save_user_to_db(user)
        return user

    def get_all_users(self) -> List[Dict[str, object]]:
        return [user.to_dict() for user in self.users.values()]

    def get_statistics(self) -> Dict[str, object]:
        total_users = len(self.users)
        admin_count = sum(1 for u in self.users.values() if u.role == "admin")
        user_count = total_users - admin_count
        total_rooms = len(self.rooms)
        active_rooms = sum(1 for r in self.rooms.values() if len(r.participants) > 0)
        total_participants = sum(len(r.participants) for r in self.rooms.values())
        return {
            "total_users": total_users,
            "admin_count": admin_count,
            "user_count": user_count,
            "total_rooms": total_rooms,
            "active_rooms": active_rooms,
            "total_participants": total_participants,
        }

    def create_room(
        self,
        room_name: str,
        room_type: str = "remote",
        password: Optional[str] = None,
        media_source: str = "camera",
        audio_device_id: Optional[str] = None,
        audio_device_label: Optional[str] = None,
    ) -> Room:
        room_id = str(uuid.uuid4())
        room = Room(
            room_id=room_id,
            room_name=room_name,
            room_type=room_type,
            password=password,
            media_source=media_source,
            audio_device_id=audio_device_id,
            audio_device_label=audio_device_label,
        )
        self.rooms[room_id] = room
        self._save_room_to_db(room)
        return room

    def list_rooms(self, room_type: Optional[str] = None) -> List[Dict[str, object]]:
        rooms = list(self.rooms.values())
        if room_type and room_type != "all":
            rooms = [room for room in rooms if room.room_type == room_type]
        return [room.to_dict() for room in rooms]

    def join_room(self, room_id: str, username: str, password: Optional[str]) -> Dict[str, str]:
        room = self.rooms.get(room_id)
        if not room:
            raise ValueError("Комната не найдена")
        if room.password and room.password != password:
            raise PermissionError("Неверный пароль")
        participant_id = str(uuid.uuid4())
        room.participants[participant_id] = username
        self._save_room_to_db(room)
        return {"participant_id": participant_id, "room_id": room_id}

    def start_remote_server(self, room_id: str, port: int, audio_enabled: bool) -> Dict[str, object]:
        room = self.rooms.get(room_id)
        if not room:
            raise ValueError("Комната не найдена")
        self.remote_servers[room_id] = {
            "port": port,
            "audio_enabled": audio_enabled,
            "started_at": datetime.utcnow().isoformat(),
        }
        self._save_remote_server_to_db(room_id, self.remote_servers[room_id])
        return {"room_id": room_id, **self.remote_servers[room_id]}

    def save_frame(self, room_id: str, frame_b64: str, mime: str = "image/jpeg") -> None:
        room = self.rooms.get(room_id)
        if not room:
            raise ValueError("Комната не найдена")
        try:
            if "," in frame_b64:
                frame_b64 = frame_b64.split(",", 1)[1]
            room.latest_frame = base64.b64decode(frame_b64)
            room.latest_frame_mime = mime
            self._save_room_to_db(room)
        except base64.binascii.Error as exc:
            raise ValueError("Некорректный формат кадра") from exc

    def save_audio_chunk(self, room_id: str, chunk_b64: str, mime: str = "audio/webm") -> None:
        room = self.rooms.get(room_id)
        if not room:
            raise ValueError("Комната не найдена")
        try:
            if "," in chunk_b64:
                chunk_b64 = chunk_b64.split(",", 1)[1]
            room.latest_audio_chunk = base64.b64decode(chunk_b64)
            room.latest_audio_mime = mime
            self._save_room_to_db(room)
        except base64.binascii.Error as exc:
            raise ValueError("Некорректный формат аудио") from exc

    def get_latest_frame(self, room_id: str) -> Optional[Dict[str, object]]:
        room = self.rooms.get(room_id)
        if not room or not room.latest_frame:
            return None
        return {
            "room_id": room.room_id,
            "mime": room.latest_frame_mime,
            "payload": room.latest_frame,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_latest_audio_chunk(self, room_id: str) -> Optional[Dict[str, object]]:
        room = self.rooms.get(room_id)
        if not room or not room.latest_audio_chunk:
            return None
        return {
            "room_id": room.room_id,
            "mime": room.latest_audio_mime,
            "payload": room.latest_audio_chunk,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def save_audio_devices(self, room_id: str, devices: List[Dict[str, object]]) -> List[Dict[str, object]]:
        if room_id not in self.rooms:
            raise ValueError("Комната не найдена")
        if not isinstance(devices, list):
            raise ValueError("devices должен быть списком")
        sanitized = [
            {
                "device_id": item.get("device_id") or item.get("deviceId"),
                "label": item.get("label"),
                "kind": item.get("kind", "audioinput"),
            }
            for item in devices
        ]
        state = self.remote_servers.setdefault(room_id, {})
        state["audio_devices"] = sanitized
        self._save_remote_server_to_db(room_id, state)
        return sanitized

    def get_audio_devices(self, room_id: str) -> List[Dict[str, object]]:
        return self.remote_servers.get(room_id, {}).get("audio_devices", [])


store = RoomStore()

__all__ = ["store"]
