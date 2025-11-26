from __future__ import annotations

from functools import wraps
from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template,
    request,
    url_for,
    session,
    redirect,
)

from api import get_api_endpoints
from store import store

app = Flask(__name__)
app.secret_key = "your-secret-key-change-in-production"

GITHUB_RELEASE_URL = "https://github.com/KnopMops/secure_stream/releases/tag/v1.0.0-release"


@app.context_processor
def inject_user():
    current_user = None
    token = session.get("access_token")
    if token:
        user = store.get_user_by_token(token)
        if user:
            current_user = user.to_dict()
    return dict(current_user=current_user)


def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        
        if not token:
            token = request.args.get("access_token")
        
        if not token and request.is_json:
            payload = request.get_json(silent=True) or {}
            token = payload.get("access_token")
        
        if not token:
            return jsonify({"error": "Требуется access_token"}), 401
        
        user = store.get_user_by_token(token)
        if not user:
            return jsonify({"error": "Неверный или истёкший токен"}), 401
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token[7:]
        else:
            token = request.args.get("access_token") or (request.get_json(silent=True) or {}).get("access_token")
        
        if not token:
            return jsonify({"error": "Требуется access_token"}), 401
        
        user = store.get_user_by_token(token)
        if not user:
            return jsonify({"error": "Неверный или истёкший токен"}), 401
        
        if user.role != "admin":
            return jsonify({"error": "Требуются права администратора"}), 403
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def landing_page():
    return render_template("index.html", github_release_url=GITHUB_RELEASE_URL)


@app.route("/login")
def login_page():
    return render_template("login.html", github_release_url=GITHUB_RELEASE_URL)


@app.route("/register")
def register_page():
    return render_template("register.html", github_release_url=GITHUB_RELEASE_URL)


@app.route("/admin")
def admin_page():
    token = session.get("access_token")
    if not token:
        return redirect(url_for("login_page"))
    
    user = store.get_user_by_token(token)
    if not user or user.role != "admin":
        return redirect(url_for("login_page"))
    
    stats = store.get_statistics()
    all_rooms = store.list_rooms("all")
    all_users = store.get_all_users()
    
    return render_template(
        "admin.html",
        github_release_url=GITHUB_RELEASE_URL,
        stats=stats,
        rooms=all_rooms,
        users=all_users,
        current_user=user.to_dict(),
    )


@app.route("/docs")
def docs_page():
    endpoints = get_api_endpoints()
    return render_template(
        "docs.html",
        github_release_url=GITHUB_RELEASE_URL,
        api_endpoints=endpoints,
    )


@app.route("/viewer/<room_id>")
def viewer_page(room_id: str):
    frame_endpoint = url_for("get_room_frame", room_id=room_id)
    return render_template(
        "viewer.html",
        github_release_url=GITHUB_RELEASE_URL,
        room_id=room_id,
        frame_endpoint=frame_endpoint,
    )


@app.route("/uploader/<room_id>")
def uploader_page(room_id: str):
    upload_endpoint = url_for("api_push_frame")
    audio_devices_endpoint = url_for("api_report_audio_devices")
    audio_chunk_endpoint = url_for("api_push_audio_chunk")
    return render_template(
        "uploader.html",
        github_release_url=GITHUB_RELEASE_URL,
        room_id=room_id,
        upload_endpoint=upload_endpoint,
        audio_chunk_endpoint=audio_chunk_endpoint,
        audio_devices_endpoint=audio_devices_endpoint,
    )


@app.post("/api/auth/register")
def api_register():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password")
    
    if not username:
        return jsonify({"error": "Укажите имя пользователя"}), 400
    if not password:
        return jsonify({"error": "Укажите пароль"}), 400
    
    try:
        user = store.create_user(username, password)
        token = user.generate_token()
        store.users_by_token[token] = user.user_id
        return jsonify({
            "access_token": token,
            "user": user.to_dict(),
        }), 201
    except ValueError as err:
        return jsonify({"error": str(err)}), 400


@app.post("/api/auth/login")
def api_login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password")
    
    if not username or not password:
        return jsonify({"error": "Укажите имя пользователя и пароль"}), 400
    
    user = store.authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Неверное имя пользователя или пароль"}), 401
    
    token = user.access_token
    session["access_token"] = token
    
    return jsonify({
        "access_token": token,
        "user": user.to_dict(),
    })


@app.post("/api/auth/logout")
def api_logout():
    token = session.get("access_token")
    if token and token in store.users_by_token:
        del store.users_by_token[token]
    session.pop("access_token", None)
    return jsonify({"status": "ok"})


@app.post("/api/rooms")
@require_token
def api_create_room():
    payload = request.get_json(silent=True) or {}
    room_name = (payload.get("room_name") or "").strip()
    room_type = (payload.get("room_type") or "remote").strip()
    password = payload.get("password")
    media_source = (payload.get("media_source") or "camera").strip().lower()
    audio_device_id = (payload.get("audio_device_id") or "").strip() or None
    audio_device_label = (payload.get(
        "audio_device_label") or "").strip() or None
    if not room_name:
        return jsonify({"error": "Укажите название комнаты"}), 400
    if media_source not in {"camera", "screen"}:
        return jsonify({"error": "media_source должен быть camera или screen"}), 400
    room = store.create_room(
        room_name,
        room_type=room_type,
        password=password,
        media_source=media_source,
        audio_device_id=audio_device_id,
        audio_device_label=audio_device_label,
    )
    return jsonify(room.to_dict()), 201


@app.get("/api/rooms")
@require_token
def api_list_rooms():
    room_type = request.args.get("room_type")
    rooms = store.list_rooms(room_type or None)
    return jsonify({"rooms": rooms})


@app.post("/api/rooms/join")
@require_token
def api_join_room():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id")
    username = (payload.get("username") or "").strip() or "Гость"
    password = payload.get("password")
    if not room_id:
        return jsonify({"error": "Укажите room_id"}), 400
    try:
        result = store.join_room(room_id, username=username, password=password)
    except PermissionError as err:
        return jsonify({"error": str(err)}), 403
    except ValueError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify(result)


@app.post("/api/remote/start")
@require_token
def api_start_remote_server():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id")
    port = int(payload.get("port") or 8080)
    audio_enabled = bool(payload.get("audio_enabled", False))
    if not room_id:
        return jsonify({"error": "room_id обязателен"}), 400
    try:
        state = store.start_remote_server(
            room_id, port=port, audio_enabled=audio_enabled)
    except ValueError as err:
        return jsonify({"error": str(err)}), 404
    return jsonify({"status": "running", **state})


@app.post("/api/remote/frame")
def api_push_frame():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id")
    frame = payload.get("frame")
    mime = payload.get("mime") or "image/jpeg"
    source = payload.get("source")
    audio_device_id = payload.get("audio_device_id")
    if not room_id or not frame:
        return jsonify({"error": "room_id и frame обязательны"}), 400
    try:
        store.save_frame(room_id, frame_b64=frame, mime=mime)
        room = store.rooms.get(room_id)
        if room:
            if source:
                room.media_source = source
            if audio_device_id:
                room.audio_device_id = audio_device_id

            if source or audio_device_id:
                store._save_room_to_db(room)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify({"status": "ok"})


@app.get("/api/remote/frame/<room_id>")
def get_room_frame(room_id: str):
    frame = store.get_latest_frame(room_id)
    if not frame:
        abort(404, description="Кадр не найден")
    return Response(frame["payload"], mimetype=frame["mime"])


@app.post("/api/remote/audio")
def api_push_audio_chunk():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id")
    chunk = payload.get("chunk")
    mime = payload.get("mime") or "audio/webm"
    if not room_id or not chunk:
        return jsonify({"error": "room_id и chunk обязательны"}), 400
    try:
        store.save_audio_chunk(room_id, chunk_b64=chunk, mime=mime)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify({"status": "ok"})


@app.get("/api/remote/audio/<room_id>")
def api_get_audio_chunk(room_id: str):
    chunk = store.get_latest_audio_chunk(room_id)
    if not chunk:
        abort(404, description="Аудио не найдено")
    return Response(chunk["payload"], mimetype=chunk["mime"])


@app.post("/api/remote/audio-devices")
def api_report_audio_devices():
    payload = request.get_json(silent=True) or {}
    room_id = payload.get("room_id")
    devices = payload.get("devices", [])
    if not room_id:
        return jsonify({"error": "room_id обязателен"}), 400
    try:
        stored = store.save_audio_devices(room_id, devices)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    return jsonify({"room_id": room_id, "devices": stored})


@app.get("/api/remote/audio-devices/<room_id>")
def api_get_audio_devices(room_id: str):
    devices = store.get_audio_devices(room_id)
    return jsonify({"room_id": room_id, "devices": devices})


@app.get("/api/admin/stats")
@require_admin
def api_admin_stats():
    stats = store.get_statistics()
    return jsonify(stats)


@app.get("/api/admin/rooms")
@require_admin
def api_admin_rooms():
    rooms = store.list_rooms("all")
    return jsonify({"rooms": rooms})


@app.get("/api/admin/users")
@require_admin
def api_admin_users():
    users = store.get_all_users()
    return jsonify({"users": users})


@app.post("/api/admin/promote")
@require_admin
def api_admin_promote():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    
    if not username:
        return jsonify({"error": "Укажите имя пользователя"}), 400
    
    user = store.get_user_by_username(username)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404
    
    if user.role == "admin":
        return jsonify({"error": "Пользователь уже является администратором"}), 400
    
    user.role = "admin"

    store._save_user_to_db(user)

    store.reload_user_from_db(user.user_id)
    return jsonify({
        "status": "ok",
        "message": f"Пользователю {username} выданы права администратора",
        "user": user.to_dict(),
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
