from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass(frozen=True)
class ApiEndpoint:
    method: str
    path: str
    title: str
    description: str
    sample_request: Dict[str, Any]
    sample_response: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def create_room_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="POST",
        path="/api/rooms",
        title="Создать комнату",
        description="Поддерживаются пароли, выбор источника (камера/экран) и id аудиоустройства. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={
            "room_name": "Мониторинг-1",
            "room_type": "remote",
            "password": "secret",
            "media_source": "screen",
            "audio_device_id": "usb-mic-1",
            "audio_device_label": "USB Mic",
            "access_token": "<your_access_token>",
        },
        sample_response={
            "room_id": "<uuid>",
            "room_name": "Мониторинг-1",
            "room_type": "remote",
            "media_source": "screen",
            "audio_device_id": "usb-mic-1",
            "audio_device_label": "USB Mic",
        },
    )


def list_rooms_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="GET",
        path="/api/rooms",
        title="Получить список комнат",
        description="Возвращает активные комнаты с признаками источника и аудио. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={"room_type": "all", "access_token": "<your_access_token>"},
        sample_response={
            "rooms": [
                {
                    "room_id": "<uuid>",
                    "room_name": "Серверная",
                    "participants_count": 4,
                    "media_source": "camera",
                    "audio_device_id": "default",
                }
            ]
        },
    )


def join_room_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="POST",
        path="/api/rooms/join",
        title="Подключиться к комнате",
        description="Проверяет пароль и возвращает идентификатор участника. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={"room_id": "<uuid>",
                        "username": "Оператор", "password": "secret", "access_token": "<your_access_token>"},
        sample_response={
            "room_id": "<uuid>",
            "participant_id": "<uuid>",
        },
    )


def start_remote_server_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="POST",
        path="/api/remote/start",
        title="Запустить сервер удалённого доступа",
        description="Поднимает сервер трансляции экрана/аудио и резервирует комнату. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={"port": 8080,
                        "room_id": "<uuid>", "audio_enabled": True, "access_token": "<your_access_token>"},
        sample_response={
            "status": "running",
            "port": 8080,
            "room_id": "<uuid>",
        },
    )


def stream_frame_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="POST",
        path="/api/remote/frame",
        title="Передать изображение",
        description="Отправляет кадр видео/экрана в комнату вместе с метаданными. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={
            "room_id": "<uuid>",
            "frame": "<base64>",
            "timestamp": "2025-11-24T15:00:00Z",
            "source": "screen",
            "audio_device_id": "usb-mic-1",
            "access_token": "<your_access_token>",
        },
        sample_response={"status": "ok"},
    )


def fetch_room_frame_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="GET",
        path="/api/remote/frame/<room_id>",
        title="Получить изображение комнаты",
        description="Возвращает последний доступный кадр трансляции. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={"access_token": "<your_access_token>"},
        sample_response={
            "room_id": "<uuid>",
            "mime": "image/jpeg",
            "binary": "<...>",
            "timestamp": "2025-11-24T15:00:03Z",
        },
    )


def report_audio_devices_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="POST",
        path="/api/remote/audio-devices",
        title="Сообщить аудиоустройства",
        description="Клиент отправляет перечень доступных микрофонов для выбранной комнаты. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={
            "room_id": "<uuid>",
            "devices": [
                {"device_id": "default", "label": "Default Mic", "kind": "audioinput"},
                {"device_id": "usb-mic-1", "label": "USB Mic", "kind": "audioinput"},
            ],
            "access_token": "<your_access_token>",
        },
        sample_response={
            "room_id": "<uuid>",
            "devices": [
                {"device_id": "default", "label": "Default Mic", "kind": "audioinput"},
                {"device_id": "usb-mic-1", "label": "USB Mic", "kind": "audioinput"},
            ],
        },
    )


def list_audio_devices_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="GET",
        path="/api/remote/audio-devices/<room_id>",
        title="Получить аудиоустройства комнаты",
        description="Возвращает последний список аудиоустройств, переданный отправителем. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={"access_token": "<your_access_token>"},
        sample_response={
            "room_id": "<uuid>",
            "devices": [
                {"device_id": "default", "label": "Default Mic", "kind": "audioinput"},
                {"device_id": "usb-mic-1", "label": "USB Mic", "kind": "audioinput"},
            ],
        },
    )


def push_audio_chunk_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="POST",
        path="/api/remote/audio",
        title="Отправить аудиофрагмент",
        description="Принимает Opus/WebM chunk, записанный микрофоном клиента. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={
            "room_id": "<uuid>",
            "chunk": "<base64>",
            "mime": "audio/webm",
            "access_token": "<your_access_token>",
        },
        sample_response={"status": "ok"},
    )


def fetch_audio_chunk_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="GET",
        path="/api/remote/audio/<room_id>",
        title="Получить аудиофрагмент",
        description="Возвращает последний сохранённый аудиофрагмент комнаты. Требуется access_token в заголовке Authorization: Bearer <token> или в параметре access_token.",
        sample_request={"access_token": "<your_access_token>"},
        sample_response={
            "room_id": "<uuid>",
            "mime": "audio/webm",
            "binary": "<...>",
            "timestamp": "2025-11-24T15:00:05Z",
        },
    )


def register_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="POST",
        path="/api/auth/register",
        title="Регистрация пользователя",
        description="Регистрирует нового пользователя и возвращает access_token.",
        sample_request={
            "username": "myuser",
            "password": "mypassword",
        },
        sample_response={
            "access_token": "<your_access_token>",
            "user": {
                "user_id": "<uuid>",
                "username": "myuser",
                "role": "user",
                "created_at": "2025-01-01T00:00:00",
            },
        },
    )


def login_endpoint() -> ApiEndpoint:
    return ApiEndpoint(
        method="POST",
        path="/api/auth/login",
        title="Авторизация пользователя",
        description="Авторизует пользователя и возвращает access_token. Используйте этот токен для доступа к API.",
        sample_request={
            "username": "myuser",
            "password": "mypassword",
        },
        sample_response={
            "access_token": "<your_access_token>",
            "user": {
                "user_id": "<uuid>",
                "username": "myuser",
                "role": "user",
                "created_at": "2025-01-01T00:00:00",
            },
        },
    )


def get_api_endpoints() -> List[Dict[str, Any]]:
    endpoints = [
        register_endpoint(),
        login_endpoint(),
        create_room_endpoint(),
        list_rooms_endpoint(),
        join_room_endpoint(),
        start_remote_server_endpoint(),
        stream_frame_endpoint(),
        fetch_room_frame_endpoint(),
        report_audio_devices_endpoint(),
        list_audio_devices_endpoint(),
        push_audio_chunk_endpoint(),
        fetch_audio_chunk_endpoint(),
    ]
    return [endpoint.to_dict() for endpoint in endpoints]


__all__ = ["get_api_endpoints"]
