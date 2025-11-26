from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DATABASE_DIR = Path("database")
DATABASE_PATH = DATABASE_DIR / "secure_stream.db"


def ensure_database_dir() -> None:
    DATABASE_DIR.mkdir(exist_ok=True)


def get_db_connection() -> sqlite3.Connection:
    ensure_database_dir()
    conn = sqlite3.connect(str(DATABASE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL,
            access_token TEXT,
            token_expires_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id TEXT PRIMARY KEY,
            room_name TEXT NOT NULL,
            room_type TEXT NOT NULL,
            password TEXT,
            media_source TEXT NOT NULL DEFAULT 'camera',
            audio_device_id TEXT,
            audio_device_label TEXT,
            created_at TEXT NOT NULL,
            participants TEXT NOT NULL DEFAULT '{}',
            latest_frame BLOB,
            latest_frame_mime TEXT DEFAULT 'image/jpeg',
            latest_audio_chunk BLOB,
            latest_audio_mime TEXT DEFAULT 'audio/webm'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS remote_servers (
            room_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_token ON users(access_token)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rooms_type ON rooms(room_type)")
    
    conn.commit()
    conn.close()


def load_users() -> Dict[str, Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = {}
    for row in cursor.fetchall():
        users[row["user_id"]] = dict(row)
    conn.close()
    return users


def save_user(user_data: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO users 
        (user_id, username, password_hash, role, created_at, access_token, token_expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_data["user_id"],
        user_data["username"],
        user_data["password_hash"],
        user_data["role"],
        user_data["created_at"].isoformat() if isinstance(user_data["created_at"], datetime) else user_data["created_at"],
        user_data.get("access_token"),
        user_data["token_expires_at"].isoformat() if user_data.get("token_expires_at") and isinstance(user_data["token_expires_at"], datetime) else user_data.get("token_expires_at"),
    ))
    
    conn.commit()
    conn.close()


def delete_user(user_id: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def load_rooms() -> Dict[str, Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms")
    rooms = {}
    for row in cursor.fetchall():
        room_dict = dict(row)

        if room_dict.get("participants"):
            try:
                room_dict["participants"] = json.loads(room_dict["participants"])
            except (json.JSONDecodeError, TypeError):
                room_dict["participants"] = {}
        else:
            room_dict["participants"] = {}
        rooms[room_dict["room_id"]] = room_dict
    conn.close()
    return rooms


def save_room(room_data: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    participants_json = json.dumps(room_data.get("participants", {}))
    
    cursor.execute("""
        INSERT OR REPLACE INTO rooms 
        (room_id, room_name, room_type, password, media_source, audio_device_id, 
         audio_device_label, created_at, participants, latest_frame, latest_frame_mime,
         latest_audio_chunk, latest_audio_mime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        room_data["room_id"],
        room_data["room_name"],
        room_data["room_type"],
        room_data.get("password"),
        room_data.get("media_source", "camera"),
        room_data.get("audio_device_id"),
        room_data.get("audio_device_label"),
        room_data["created_at"].isoformat() if isinstance(room_data["created_at"], datetime) else room_data["created_at"],
        participants_json,
        room_data.get("latest_frame"),
        room_data.get("latest_frame_mime", "image/jpeg"),
        room_data.get("latest_audio_chunk"),
        room_data.get("latest_audio_mime", "audio/webm"),
    ))
    
    conn.commit()
    conn.close()


def delete_room(room_id: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
    cursor.execute("DELETE FROM remote_servers WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()


def load_remote_servers() -> Dict[str, Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM remote_servers")
    servers = {}
    for row in cursor.fetchall():
        try:
            servers[row["room_id"]] = json.loads(row["data"])
        except (json.JSONDecodeError, TypeError):
            servers[row["room_id"]] = {}
    conn.close()
    return servers


def save_remote_server(room_id: str, server_data: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO remote_servers (room_id, data)
        VALUES (?, ?)
    """, (room_id, json.dumps(server_data)))
    
    conn.commit()
    conn.close()


def delete_remote_server(room_id: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM remote_servers WHERE room_id = ?", (room_id,))
    conn.commit()
    conn.close()


def clear_database() -> None:
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    init_database()


__all__ = [
    "init_database",
    "load_users",
    "save_user",
    "delete_user",
    "load_rooms",
    "save_room",
    "delete_room",
    "load_remote_servers",
    "save_remote_server",
    "delete_remote_server",
    "clear_database",
]

