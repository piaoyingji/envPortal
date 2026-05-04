from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

import legacy_server as legacy

from . import __version__
from .ai import summarize_vpn_workflow_with_ai
from .auth import ROLE_ADMINS, ROLE_USERS, SESSION_COOKIE, authenticate, change_own_password, create_password_reset, create_session, create_user, delete_session, get_user, list_users, reset_password_by_token, reset_user_password, set_user_disabled, update_avatar, update_own_profile, update_user, user_from_session
from .cache import get_json, set_json
from .db import all_tags, attach_file_to_vpn_guide, audit, create_environment, create_organization, create_vpn_import_job, delete_environment, file_objects_by_ids, get_organization, get_vpn_guide, get_vpn_import_job, init_db, organizations_with_environments, save_file_object, save_vpn_guide_raw, summarize_vpn_workflow, update_app_servers, update_environment_details, update_environment_vpn, update_organization, update_vpn_guide_file_metadata, update_vpn_guide_workflow, update_vpn_import_job, vpn_guide_source_files
from .mail import send_password_reset_mail
from .settings import APP_NAME, BASE_DIR, HERMES_TIMEOUT_SECONDS, HERMES_URL, MINIO_BUCKET, PUBLIC_URL, UPLOAD_MAX_FILE_MB, UPLOAD_MAX_JOB_MB, UPLOAD_REJECT_EXTENSIONS, VERSION
from .storage import ensure_bucket, get_object_bytes, put_bytes_if_missing


app = FastAPI(title=APP_NAME, version=VERSION)


PUBLIC_API_PATHS = {
    "/api/config",
    "/api/auth/me",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
}

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
READ_ALLOWED_POSTS = {
    "/api/rdp/file",
    "/api/rdp/connect",
    "/api/guacamole/connect",
}
SELF_SERVICE_WRITE_PATHS = {
    "/api/auth/me/password",
    "/api/auth/me/profile",
    "/api/auth/me/avatar",
}


def current_user(request: Request) -> dict[str, Any] | None:
    cached = getattr(request.state, "user", None)
    if cached is not None:
        return cached
    user = user_from_session(request.cookies.get(SESSION_COOKIE))
    request.state.user = user
    return user


def require_auth(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(request: Request) -> dict[str, Any]:
    user = require_auth(request)
    if user.get("role") != ROLE_ADMINS:
        raise HTTPException(status_code=403, detail="Admin role is required")
    return user


def require_write_access(request: Request) -> dict[str, Any]:
    user = require_auth(request)
    if user.get("role") != ROLE_ADMINS:
        raise HTTPException(status_code=403, detail="Read-only users cannot modify data")
    return user


def audit_as(request: Request, action: str, target_type: str, target_id: Any | None = None, payload: dict[str, Any] | None = None) -> None:
    user = current_user(request)
    actor = str((user or {}).get("username") or "system")
    audit(action, target_type, target_id, payload=payload or {}, actor=actor)


@app.middleware("http")
async def auth_gate(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path not in PUBLIC_API_PATHS and not request.url.path.startswith("/api/auth/avatar/"):
        user = current_user(request)
        if not user:
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        if request.method in WRITE_METHODS and request.url.path not in READ_ALLOWED_POSTS and request.url.path not in SELF_SERVICE_WRITE_PATHS and user.get("role") != ROLE_ADMINS:
            return JSONResponse({"detail": "Read-only users cannot modify data"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def no_store_frontend_assets(request: Request, call_next):
    response = await call_next(request)
    if request.url.path in {"/", "/index.html", "/admin.html", "/rdp.html"} or request.url.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def frontend_dist() -> Path:
    return BASE_DIR / "frontend" / "dist"


@app.on_event("startup")
def startup() -> None:
    init_db()
    ensure_bucket()
    legacy.cleanup_guacamole_drive_sessions(force=True)


@app.get("/api/config")
def api_config(request: Request) -> dict[str, Any]:
    status = legacy.guacamole_status()
    return {
        "appName": APP_NAME,
        "version": __version__,
        "guacamoleEnabled": bool(legacy.GUACAMOLE_URL),
        "guacamoleAvailable": status["available"],
        "guacamoleStatus": status["message"],
        "guacamoleUrl": "/guacamole_auto_login.jsp" if legacy.GUACAMOLE_USERNAME and legacy.GUACAMOLE_PASSWORD else legacy.public_guacamole_url(request.headers.get("host", "")),
        "guacamoleAutoLogin": bool(legacy.GUACAMOLE_URL and legacy.GUACAMOLE_USERNAME and legacy.GUACAMOLE_PASSWORD),
    }


@app.get("/api/auth/me")
def api_auth_me(request: Request) -> dict[str, Any]:
    user = current_user(request)
    return {"authenticated": bool(user), "user": user}


@app.post("/api/auth/login")
async def api_auth_login(request: Request) -> JSONResponse:
    payload = await request.json()
    user = authenticate(str(payload.get("username") or ""), str(payload.get("password") or ""))
    if not user:
        return JSONResponse({"detail": "Invalid username or password"}, status_code=401)
    token = create_session(user["id"])
    response = JSONResponse({"user": user})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=7 * 24 * 3600, path="/")
    return response


@app.post("/api/auth/logout")
def api_auth_logout(request: Request) -> JSONResponse:
    delete_session(request.cookies.get(SESSION_COOKIE))
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.post("/api/auth/forgot-password")
async def api_auth_forgot_password(request: Request) -> dict[str, Any]:
    payload = await request.json()
    user, token = create_password_reset(str(payload.get("usernameOrEmail") or ""))
    if user and token and user.get("email"):
        reset_url = f"{PUBLIC_URL.rstrip('/')}/index.html?resetToken={urllib.parse.quote(token)}"
        send_password_reset_mail(user["email"], user["username"], reset_url)
    return {"ok": True}


@app.post("/api/auth/reset-password")
async def api_auth_reset_password(request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        user = reset_password_by_token(str(payload.get("token") or ""), str(payload.get("newPassword") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "user": user}


@app.patch("/api/auth/me/password")
async def api_auth_change_password(request: Request) -> dict[str, Any]:
    user = require_auth(request)
    payload = await request.json()
    try:
        change_own_password(user["id"], str(payload.get("currentPassword") or ""), str(payload.get("newPassword") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    delete_session(request.cookies.get(SESSION_COOKIE))
    return {"ok": True}


@app.patch("/api/auth/me/profile")
async def api_auth_profile(request: Request) -> dict[str, Any]:
    user = require_auth(request)
    payload = await request.json()
    return update_own_profile(user["id"], payload)


@app.post("/api/auth/me/avatar")
async def api_auth_avatar(request: Request, avatar: UploadFile = File(...)) -> dict[str, Any]:
    user = require_auth(request)
    payload = await avatar.read()
    if len(payload) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Avatar is larger than 2MB")
    digest = hashlib.sha256(payload).hexdigest()
    content_type = avatar.content_type or mimetypes.guess_type(avatar.filename or "")[0] or "application/octet-stream"
    object_key = f"avatars/{user['id']}/{digest}"
    put_bytes_if_missing(object_key, payload, content_type=content_type, metadata={"category": "avatar"})
    return update_avatar(user["id"], object_key)


@app.get("/api/auth/avatar/{user_id}")
def api_auth_avatar_get(user_id: str) -> Response:
    user = get_user(user_id)
    if not user or not user.get("avatarObjectKey"):
        raise HTTPException(status_code=404, detail="Avatar not found")
    payload = get_object_bytes(user["avatarObjectKey"])
    return Response(payload, media_type=mimetypes.guess_type(user["avatarObjectKey"])[0] or "application/octet-stream")


@app.get("/api/users")
def api_users(request: Request) -> dict[str, Any]:
    require_admin(request)
    return {"users": list_users()}


@app.post("/api/users")
async def api_create_user(request: Request) -> dict[str, Any]:
    require_admin(request)
    payload = await request.json()
    try:
        user = create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_as(request, "create_user", "user", user["id"], {"username": user["username"], "role": user["role"]})
    return user


@app.patch("/api/users/{user_id}")
async def api_update_user(user_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    payload = await request.json()
    try:
        user = update_user(user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit_as(request, "update_user", "user", user_id, {"username": user["username"], "role": user["role"]})
    return user


@app.post("/api/users/{user_id}/reset-password")
async def api_reset_user_password(user_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    payload = await request.json()
    try:
        user = reset_user_password(user_id, str(payload.get("password") or "") or None)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit_as(request, "reset_user_password", "user", user_id, {"username": user["username"]})
    return user


@app.post("/api/users/{user_id}/disable")
def api_disable_user(user_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    user = set_user_disabled(user_id, True)
    audit_as(request, "disable_user", "user", user_id, {"username": user["username"]})
    return user


@app.post("/api/users/{user_id}/enable")
def api_enable_user(user_id: str, request: Request) -> dict[str, Any]:
    require_admin(request)
    user = set_user_disabled(user_id, False)
    audit_as(request, "enable_user", "user", user_id, {"username": user["username"]})
    return user


@app.get("/api/organizations")
def api_organizations() -> dict[str, Any]:
    return {"organizations": organizations_with_environments(), "tags": all_tags()}


@app.post("/api/organizations")
async def api_create_organization(request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        result = create_organization(str(payload.get("code") or ""), str(payload.get("name") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_as(request, "create_organization", "organization", result["id"], payload={"code": result["code"], "name": result["name"]})
    return result


@app.patch("/api/organizations/{organization_id}")
async def api_update_organization(organization_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        result = update_organization(organization_id, str(payload.get("code") or ""), str(payload.get("name") or ""))
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    audit_as(request, "update_organization", "organization", organization_id, payload={"code": result["code"], "name": result["name"]})
    return result


@app.get("/api/tags")
def api_tags() -> dict[str, Any]:
    return {"tags": all_tags()}


@app.get("/api/files/{file_id}/download")
def api_file_download(file_id: str) -> Response:
    files = file_objects_by_ids([file_id])
    if not files:
        raise HTTPException(status_code=404, detail="File not found")
    file = files[0]
    object_key = str(file.get("objectKey") or "")
    if not object_key:
        raise HTTPException(status_code=404, detail="File object is missing")
    try:
        payload = get_object_bytes(object_key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"File object is not available: {exc}") from exc
    filename = str(file.get("filename") or file.get("storedFilename") or "download.bin")
    quoted = urllib.parse.quote(filename)
    return Response(
        payload,
        media_type=str(file.get("contentType") or "application/octet-stream"),
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )


@app.post("/api/organizations/{organization_id}/environments")
async def api_create_environment(organization_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    raw_tags = payload.get("tags") or []
    tags = raw_tags if isinstance(raw_tags, list) else []
    try:
        result = create_environment(
            organization_id,
            str(payload.get("title") or ""),
            [str(tag) for tag in tags],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_as(request, "create_environment", "organization", organization_id, payload={"environment_id": result["id"], "title": result["title"]})
    return result


@app.delete("/api/environments/{environment_id}")
async def api_delete_environment(environment_id: str) -> dict[str, Any]:
    return delete_environment_response(environment_id, request)


@app.post("/api/environments/{environment_id}/delete")
async def api_post_delete_environment(environment_id: str) -> dict[str, Any]:
    return delete_environment_response(environment_id, request)


def delete_environment_response(environment_id: str, request: Request | None = None) -> dict[str, Any]:
    try:
        result = delete_environment(environment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        if request:
            audit_as(request, "delete_environment", "environment", environment_id, payload={"title": result["title"], "organization_id": result["organization_id"], "deleted": result.get("deleted", {})})
        else:
            audit("delete_environment", "environment", environment_id, payload={"title": result["title"], "organization_id": result["organization_id"], "deleted": result.get("deleted", {})})
    except Exception as exc:
        print(f"delete audit failed for environment {environment_id}: {exc}")
    return {"ok": True, "id": environment_id, "deleted": result.get("deleted", {})}


def analyze_vpn_guide_task(guide_id: str, organization_id: str, raw_text: str) -> None:
    if not raw_text.strip():
        update_vpn_guide_workflow(guide_id, [], "none", status="ready")
        return
    workflow_source = "ai"
    try:
        workflow = summarize_vpn_workflow_with_ai(raw_text)
    except Exception as exc:
        workflow_source = "rule"
        workflow = summarize_vpn_workflow(raw_text)
        print(f"AI VPN workflow generation failed, using local fallback: {exc}")
    guide = update_vpn_guide_workflow(
        guide_id,
        workflow=workflow,
        source=workflow_source,
        status="ready",
    )
    audit(
        "analyze_vpn_guide",
        "organization",
        organization_id,
        payload={"name": guide.get("name") if guide else "", "steps": len(guide.get("workflow", [])) if guide else 0, "source": workflow_source},
    )


def reject_upload_filename(filename: str) -> None:
    lowered = (filename or "").lower()
    for extension in UPLOAD_REJECT_EXTENSIONS:
        if extension and lowered.endswith(extension):
            raise HTTPException(status_code=400, detail=f"Rejected file type: {extension}")


def merge_vpn_raw_text(manual_text: str, generated_text: str) -> str:
    pieces = []
    if manual_text.strip():
        pieces.append(manual_text.strip())
    if generated_text.strip():
        pieces.append(generated_text.strip())
    return "\n\n".join(pieces)


def clean_vpn_raw_text(raw_text: str, organization: dict[str, Any] | None) -> str:
    if not organization:
        return raw_text
    code = str(organization.get("code") or "").strip()
    name = str(organization.get("name") or "").strip()
    if not code and not name:
        return raw_text
    redundant_values = {value for value in [code, name] if value}
    redundant_labels = {
        "機関コード", "機関名", "顧客コード", "顧客名", "客户编码", "客户名称",
        "客户代码", "客户名", "組織コード", "組織名", "组织编码", "组织名称",
    }
    low_value_labels = {
        "更新情報", "顧客別情報参照", "関係者外秘", "【関係者外秘】", "備考（リモート接続以外の情報）",
        "サーバ更改時期", "pcAnywhere暗号化設定変更（2012/2）", "pcAnywhereパッチ適用（2012/2）",
    }
    relevant_tokens = [
        "vpn", "リモート", "遠隔", "remote", "接続", "laplink", "pcanywhere", "rdp", "ssh",
        "サーバ", "server", "db", "ap", "ip", "アドレス", "電話", "連絡", "依頼", "申請", "許可",
        "ユーザ", "ユーザー", "user", "administrator", "id", "pw", "password", "pass", "パスワード",
        "事前共有鍵", "認証", "保守", "メンテ", "oracle", "windows", "アナログ",
        "以降", "以前", "以後", "から", "まで", "新", "旧", "追加", "補足", "差分", "変更",
        "経由", "踏み台", "中継", "ジャンプ", "jump", "bastion", "gateway", "proxy",
    ]

    def relevant(text: str) -> bool:
        lowered = text.lower()
        return any(token.lower() in lowered for token in relevant_tokens)

    def credentialish(text: str) -> bool:
        lowered = text.lower()
        return any(token in lowered for token in ["administrator", "ユーザ", "user", "id", "pw", "password", "pass", "パスワード"])

    cleaned_lines: list[str] = []
    carry_value_lines = 0
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        if (
            stripped.startswith("===== Source:")
            or re.match(r"^\d+\.\s+role=", stripped)
            or stripped.startswith("Source role:")
            or stripped.startswith("Client modified:")
            or stripped.startswith("Date hints:")
            or stripped.startswith("Type:")
            or stripped.startswith("[Sheet:")
        ):
            continue
        if stripped.startswith("Path context:"):
            carry_value_lines = 0
            continue
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|")]
            kept = [
                cell
                for cell in cells
                if cell and cell not in redundant_values and cell not in redundant_labels and cell not in low_value_labels
            ]
            compact = " | ".join(kept)
            if kept and relevant(compact):
                cleaned_lines.append(compact)
                carry_value_lines = 1
            continue
        if stripped in redundant_values or stripped in redundant_labels or stripped in low_value_labels:
            continue
        line = re.sub(
            r"^(?:機関コード|顧客コード|客户编码|客户代码|組織コード|组织编码)\s*[:：]\s*" + re.escape(code) + r"\s*$",
            "",
            line,
        ) if code else line
        line = re.sub(
            r"^(?:機関名|顧客名|客户名称|客户名|組織名|组织名称)\s*[:：]\s*" + re.escape(name) + r"\s*$",
            "",
            line,
        ) if name else line
        stripped = line.strip()
        if stripped and (relevant(stripped) or carry_value_lines > 0):
            cleaned_lines.append(line)
            carry_value_lines = 1 if relevant(stripped) else max(0, carry_value_lines - 1)
        else:
            carry_value_lines = 0
    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def parse_file_meta(file_meta: str) -> list[dict[str, Any]]:
    if not file_meta.strip():
        return []
    try:
        value = json.loads(file_meta)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def file_meta_for_index(items: list[dict[str, Any]], index: int, filename: str) -> dict[str, Any]:
    item = items[index] if index < len(items) and isinstance(items[index], dict) else {}
    relative_path = str(item.get("relativePath") or filename).replace("\\", "/").strip("/")
    return {
        "filename": str(item.get("filename") or Path(filename).name or filename),
        "relativePath": relative_path or filename,
        "clientModifiedAt": str(item.get("clientModifiedAt") or ""),
    }


async def store_uploaded_vpn_files(guide_id: str, files: list[UploadFile], file_meta: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    max_file_bytes = UPLOAD_MAX_FILE_MB * 1024 * 1024
    max_job_bytes = UPLOAD_MAX_JOB_MB * 1024 * 1024
    total_bytes = 0
    saved_files: list[dict[str, Any]] = []
    meta_items = file_meta or []
    for index, upload in enumerate(files):
        filename = upload.filename or "upload.bin"
        meta = file_meta_for_index(meta_items, index, filename)
        relative_path = meta["relativePath"]
        reject_upload_filename(filename)
        reject_upload_filename(relative_path)
        payload = await upload.read()
        total_bytes += len(payload)
        if len(payload) > max_file_bytes:
            raise HTTPException(status_code=413, detail=f"File is larger than {UPLOAD_MAX_FILE_MB}MB: {filename}")
        if total_bytes > max_job_bytes:
            raise HTTPException(status_code=413, detail=f"Upload batch is larger than {UPLOAD_MAX_JOB_MB}MB")
        digest = hashlib.sha256(payload).hexdigest()
        object_key = f"vpn-sources/sha256/{digest}"
        content_type = upload.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        put_bytes_if_missing(
            object_key,
            payload,
            content_type=content_type,
            metadata={"sha256": digest, "filename": filename, "category": "vpn-source"},
        )
        file_object = save_file_object(
            sha256=digest,
            object_key=object_key,
            filename=filename,
            size_bytes=len(payload),
            content_type=content_type,
            category="vpn-source",
        )
        saved_files.append(
            attach_file_to_vpn_guide(
                str(guide_id),
                str(file_object["id"]),
                filename,
                relative_path=relative_path,
                client_modified_at=meta["clientModifiedAt"],
            )
        )
    return saved_files


def call_hermes_vpn_ingest(files: list[dict[str, Any]]) -> dict[str, Any]:
    if not HERMES_URL:
        raise RuntimeError("Hermes Agent is not configured.")
    payload = json.dumps({
        "bucket": MINIO_BUCKET,
        "files": [
            {
                "id": str(file.get("id") or ""),
                "filename": file.get("filename") or "",
                "objectKey": file.get("objectKey") or "",
                "sha256": file.get("sha256") or "",
                "contentType": file.get("contentType") or "",
                "sizeBytes": file.get("sizeBytes") or 0,
                "relativePath": file.get("relativePath") or file.get("filename") or "",
                "clientModifiedAt": str(file.get("clientModifiedAt") or ""),
                "uploadedAt": str(file.get("uploadedAt") or file.get("createdAt") or ""),
            }
            for file in files
        ],
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{HERMES_URL}/internal/vpn-ingest",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=HERMES_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def run_vpn_import_job(job_id: str, guide_id: str, organization_id: str, manual_text: str | None = None) -> None:
    try:
        update_vpn_import_job(job_id, status="parsing", progress=10)
        files = vpn_guide_source_files(guide_id)
        if not files:
            raise RuntimeError("No source files are associated with this VPN guide.")
        update_vpn_import_job(job_id, source_file_ids=[str(file["id"]) for file in files if file.get("id")])
        hermes_result = call_hermes_vpn_ingest(files)
        source_raw_text = str(hermes_result.get("sourceRawText") or hermes_result.get("rawText") or "")
        fragments = hermes_result.get("fragments") if isinstance(hermes_result.get("fragments"), list) else []
        warnings = hermes_result.get("warnings") if isinstance(hermes_result.get("warnings"), list) else []
        source_meta = hermes_result.get("sourceMeta") if isinstance(hermes_result.get("sourceMeta"), list) else []
        precedence_summary = str(hermes_result.get("precedenceSummary") or "")
        update_vpn_guide_file_metadata(guide_id, source_meta)
        guide = get_vpn_guide(guide_id)
        effective_manual_text = manual_text if manual_text is not None else str((guide or {}).get("manualRawText") or "")
        source_with_precedence = "\n\n".join(part for part in [precedence_summary, source_raw_text] if part.strip())
        analysis_raw_text = clean_vpn_raw_text(
            merge_vpn_raw_text(effective_manual_text, source_with_precedence),
            get_organization(organization_id),
        )
        update_vpn_import_job(
            job_id,
            status="rebuilding",
            progress=65,
            raw_text=analysis_raw_text,
            fragments=fragments,
            warnings=[str(item) for item in warnings],
            source_meta=source_meta,
            precedence_summary=precedence_summary,
        )
        save_vpn_guide_raw(
            organization_id,
            analysis_raw_text,
            guide_id=guide_id,
            status="analyzing",
            source="hermes",
            source_raw_text=source_raw_text,
            manual_raw_text=effective_manual_text,
            analysis_raw_text=analysis_raw_text,
        )
        update_vpn_import_job(job_id, status="analyzing", progress=80)
        analyze_vpn_guide_task(guide_id, organization_id, analysis_raw_text)
        update_vpn_import_job(
            job_id,
            status="analyzed",
            progress=100,
            raw_text=analysis_raw_text,
            fragments=fragments,
            warnings=[str(item) for item in warnings],
            source_meta=source_meta,
            precedence_summary=precedence_summary,
        )
    except Exception as exc:
        update_vpn_import_job(job_id, status="failed", progress=100, error=str(exc))
        update_vpn_guide_workflow(guide_id, [], "hermes", status="failed", error=str(exc))
        print(f"VPN import job failed ({job_id}): {exc}")


@app.post("/api/organizations/{organization_id}/vpn-guide")
async def api_save_vpn_guide(organization_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    raw_text = str(payload.get("rawText", ""))
    name = str(payload.get("name", "VPN"))
    guide_id = payload.get("id")
    guide = save_vpn_guide_raw(
        organization_id,
        raw_text,
        name=name,
        guide_id=str(guide_id) if guide_id else None,
        manual_raw_text=raw_text,
        analysis_raw_text=clean_vpn_raw_text(
            merge_vpn_raw_text(raw_text, str((get_vpn_guide(str(guide_id)) or {}).get("sourceRawText") or "")) if guide_id else raw_text,
            get_organization(organization_id),
        ),
    )
    guide_sources = vpn_guide_source_files(str(guide["id"]))
    if guide_sources:
        job = create_vpn_import_job(organization_id, str(guide["id"]), guide_sources, mode="rebuild")
        threading.Thread(
            target=run_vpn_import_job,
            args=(str(job["id"]), str(guide["id"]), organization_id, raw_text),
            daemon=True,
            name=f"vpn-guide-rebuild-{guide['id']}",
        ).start()
    elif raw_text.strip():
        threading.Thread(
            target=analyze_vpn_guide_task,
            args=(str(guide["id"]), organization_id, raw_text),
            daemon=True,
            name=f"vpn-guide-ai-{guide['id']}",
        ).start()
    audit(
        "save_vpn_guide_raw",
        "organization",
        organization_id,
        payload={"name": guide.get("name"), "hasText": bool(raw_text.strip()), "status": guide.get("workflowStatus")},
    )
    return guide


@app.post("/api/organizations/{organization_id}/vpn-guide/import")
async def api_import_vpn_guide(
    organization_id: str,
    name: str = Form("VPN"),
    rawText: str = Form(""),
    guideId: str = Form(""),
    fileMeta: str = Form(""),
    files: list[UploadFile] = File(default=[]),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="At least one source file is required.")
    guide = save_vpn_guide_raw(
        organization_id,
        rawText,
        name=name,
        guide_id=guideId or None,
        status="analyzing",
        source="hermes",
        manual_raw_text=rawText,
        analysis_raw_text=rawText,
    )
    await store_uploaded_vpn_files(str(guide["id"]), files, parse_file_meta(fileMeta))
    all_source_files = vpn_guide_source_files(str(guide["id"]))
    job = create_vpn_import_job(organization_id, str(guide["id"]), all_source_files, mode="rebuild")
    guide["sourceFiles"] = all_source_files
    threading.Thread(
        target=run_vpn_import_job,
        args=(str(job["id"]), str(guide["id"]), organization_id, rawText),
        daemon=True,
        name=f"vpn-import-{job['id']}",
    ).start()
    audit(
        "import_vpn_guide_files",
        "organization",
        organization_id,
        payload={"guideId": guide.get("id"), "jobId": job.get("id"), "files": len(all_source_files), "mode": "rebuild"},
    )
    return {"guide": guide, "job": job}


@app.post("/api/organizations/{organization_id}/vpn-guide/{guide_id}/reanalyze")
def api_reanalyze_vpn_guide(organization_id: str, guide_id: str, request: Request) -> dict[str, Any]:
    guide = get_vpn_guide(guide_id)
    if not guide or str(guide.get("organization_id")) != organization_id:
        raise HTTPException(status_code=404, detail="VPN guide not found")
    manual_text = str(guide.get("manualRawText") or "")
    source_text = str(guide.get("sourceRawText") or "")
    current_text = str(guide.get("analysisRawText") or guide.get("rawText") or "")
    analysis_raw_text = clean_vpn_raw_text(
        merge_vpn_raw_text(manual_text, source_text) if (manual_text.strip() or source_text.strip()) else current_text,
        get_organization(organization_id),
    )
    pending = save_vpn_guide_raw(
        organization_id,
        analysis_raw_text,
        guide_id=guide_id,
        status="analyzing",
        source="ai",
        analysis_raw_text=analysis_raw_text,
    )
    threading.Thread(
        target=analyze_vpn_guide_task,
        args=(guide_id, organization_id, analysis_raw_text),
        daemon=True,
        name=f"vpn-guide-reanalyze-ai-{guide_id}",
    ).start()
    audit_as(request, "reanalyze_vpn_guide", "organization", organization_id, payload={"guideId": guide_id, "sources": 0})
    return {"guide": pending}


@app.get("/api/vpn-import-jobs/{job_id}")
def api_vpn_import_job(job_id: str) -> dict[str, Any]:
    job = get_vpn_import_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="VPN import job not found")
    return job


@app.post("/api/vpn-import-jobs/{job_id}/retry")
def api_retry_vpn_import_job(job_id: str) -> dict[str, Any]:
    job = get_vpn_import_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="VPN import job not found")
    files = vpn_guide_source_files(str(job["guideId"]))
    if not files:
        raise HTTPException(status_code=400, detail="No source files are associated with this job.")
    retry = update_vpn_import_job(job_id, status="queued", progress=0, error="")
    threading.Thread(
        target=run_vpn_import_job,
        args=(str(job["id"]), str(job["guideId"]), str(job["organizationId"]), None),
        daemon=True,
        name=f"vpn-import-retry-{job['id']}",
    ).start()
    return retry or job


@app.post("/api/ai/vpn-workflow/preview")
async def api_preview_vpn_workflow(request: Request) -> dict[str, Any]:
    payload = await request.json()
    raw_text = str(payload.get("rawText", ""))
    source = "ai"
    try:
        workflow = summarize_vpn_workflow_with_ai(raw_text)
    except Exception as exc:
        source = "rule"
        workflow = summarize_vpn_workflow(raw_text)
        print(f"AI VPN workflow preview failed, using local fallback: {exc}")
    return {"source": source, "workflow": workflow}


@app.patch("/api/environments/{environment_id}/vpn")
async def api_update_environment_vpn(environment_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        result = update_environment_vpn(
            environment_id,
            bool(payload.get("vpnRequired", False)),
            str(payload.get("vpnGuideId")) if payload.get("vpnGuideId") else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_as(request, "update_environment_vpn", "environment", environment_id, payload=result)
    return result


@app.patch("/api/environments/{environment_id}/details")
async def api_update_environment_details(environment_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        result = update_environment_details(environment_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_as(request, "update_environment_details", "environment", environment_id, payload=strip_secret(payload))
    return result


@app.patch("/api/environments/{environment_id}/app-servers")
async def api_update_app_servers(environment_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    try:
        servers = update_app_servers(environment_id, list(payload.get("servers") or []))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    audit_as(request, "update_app_servers", "environment", environment_id, payload={"count": len(servers)})
    return {"servers": servers}


@app.get("/api/env-check")
def api_env_check(url: str) -> dict[str, Any]:
    key = f"env-check:{url}"
    cached = get_json(key)
    if cached:
        return cached
    result = legacy.env_check(url)
    set_json(key, result, 60)
    return result


@app.post("/api/db-probe")
async def api_db_probe(request: Request) -> dict[str, Any]:
    payload = await request.json()
    db_name = payload.get("dbName") or build_db_name(payload)
    result = legacy.probe_database(db_name, payload.get("dbUser", ""), payload.get("dbPwd", ""))
    audit_as(request, "probe", "database", payload=strip_secret(payload) | {"result": result})
    return result


def build_db_name(payload: dict[str, Any]) -> str:
    host = payload.get("dbHost", "")
    port = payload.get("dbPort", "")
    name = payload.get("dbName", "")
    if host and port and name:
        sep = "/" if str(port) == "5432" else ":"
        return f"{host}:{port}{sep}{name}"
    return payload.get("dbName", "")


def strip_secret(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: ("***" if "password" in key.lower() or "pwd" in key.lower() else value) for key, value in payload.items()}


@app.post("/api/rdp/file")
async def api_rdp_file(request: Request) -> Response:
    form = await request.form()
    target = str(form.get("target", ""))
    if not target.strip():
        raise HTTPException(status_code=400, detail="Missing RDP target")
    org = legacy.safe_filename(str(form.get("org", "")))
    env = legacy.safe_filename(str(form.get("env", "")))
    filename_base = legacy.safe_filename("_".join(part for part in [org, env] if part), "remote")
    legacy.save_rdp_credential(target, str(form.get("user", "")), str(form.get("password", "")))
    payload = legacy.build_rdp_file(target, str(form.get("user", "")), str(form.get("password", "")))
    payload = legacy.sign_rdp_payload(payload, filename_base)
    audit_as(request, "download_rdp", "remote", payload={"target": target, "org": org, "env": env})
    return Response(
        payload,
        media_type="application/x-rdp",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename_base)}.rdp"},
    )


@app.post("/api/rdp/connect")
async def api_rdp_connect(request: Request) -> JSONResponse:
    form = await request.form()
    target = str(form.get("target", ""))
    if not target.strip():
        return JSONResponse({"ok": False, "message": "Missing RDP target"}, status_code=400)
    legacy.save_rdp_credential(target, str(form.get("user", "")), str(form.get("password", "")))
    ok, message = legacy.launch_mstsc(target)
    audit_as(request, "connect_rdp", "remote", payload={"target": target, "ok": ok})
    return JSONResponse({"ok": ok, "message": message}, status_code=200 if ok else 500)


@app.post("/api/guacamole/connect")
async def api_guacamole_connect(request: Request) -> JSONResponse:
    form = await request.form()
    target = str(form.get("target", ""))
    if not target.strip():
        return JSONResponse({"ok": False, "message": "Missing RDP target"}, status_code=400)
    result = legacy.guacamole_quickconnect(
        target,
        str(form.get("user", "")),
        str(form.get("password", "")),
        legacy.public_guacamole_url(request.headers.get("host", "")),
    )
    audit_as(request, "connect_guacamole", "remote", payload={"target": target, "ok": result.get("ok")})
    return JSONResponse(result, status_code=200 if result.get("ok") else 500)


@app.post("/auth.jsp")
async def legacy_auth(pwd: str = Form("")) -> Response:
    return Response(b"OK" if pwd == legacy.AUTH_PASSWORD else b"NG")


@app.post("/db_probe.jsp")
async def legacy_db_probe(dbName: str = Form(""), dbUser: str = Form(""), dbPwd: str = Form("")) -> dict[str, Any]:
    return legacy.probe_database(dbName, dbUser, dbPwd)


@app.get("/ping.jsp")
def legacy_ping(url: str = "") -> Response:
    result = legacy.env_check(url)
    return Response(str(result["status"]))


@app.get("/env_check.jsp")
def legacy_env_check(url: str = "") -> dict[str, Any]:
    return legacy.env_check(url)


@app.get("/portal_config.jsp")
def legacy_portal_config(request: Request) -> dict[str, Any]:
    return api_config(request)


@app.get("/guacamole_auto_login.jsp")
def legacy_guacamole_auto_login(request: Request) -> Response:
    public_url = legacy.public_guacamole_url(request.headers.get("host", ""))
    if not public_url:
        return Response("Guacamole is not configured.", status_code=404)
    if not legacy.GUACAMOLE_USERNAME or not legacy.GUACAMOLE_PASSWORD:
        return RedirectResponse(public_url)
    query = urllib.parse.urlencode({"username": legacy.GUACAMOLE_USERNAME, "password": legacy.GUACAMOLE_PASSWORD})
    return RedirectResponse(public_url + "/#/" + "?" + query)


@app.get("/rdp_signing_cert.cer")
def legacy_rdp_cert() -> Response:
    payload = legacy.export_rdp_cert()
    if not payload:
        return Response("RDP signing certificate is not available on this platform.", status_code=404)
    return Response(payload, media_type="application/pkix-cert", headers={"Content-Disposition": "attachment; filename=OneCRM_RDP_Signing.cer"})


@app.post("/rdp_file.jsp")
async def legacy_rdp_file(request: Request) -> Response:
    return await api_rdp_file(request)


@app.post("/rdp_connect.jsp")
async def legacy_rdp_connect(request: Request) -> JSONResponse:
    return await api_rdp_connect(request)


@app.post("/guacamole_connect.jsp")
async def legacy_guacamole_connect(request: Request) -> JSONResponse:
    return await api_guacamole_connect(request)


@app.post("/update_csv.jsp")
@app.post("/update_rdp.jsp")
@app.post("/update_tags.jsp")
async def legacy_file_update(request: Request) -> Response:
    require_write_access(request)
    path_map = {
        "/update_csv.jsp": "data.csv",
        "/update_rdp.jsp": "rdp.csv",
        "/update_tags.jsp": "tags.json",
    }
    body = await request.body()
    filename = path_map.get(request.url.path)
    if not filename:
        return Response("Not Found", status_code=404)
    (BASE_DIR / filename).write_bytes(body)
    audit_as(request, "legacy_file_update", "file", payload={"file": filename})
    return Response("success")


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/admin.html", response_class=HTMLResponse)
@app.get("/rdp.html", response_class=HTMLResponse)
def react_entry() -> Response:
    index_path = frontend_dist() / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>OneCRM frontend is not built yet.</h1><p>Run npm install and npm run build in frontend/.</p>", status_code=503)


dist = frontend_dist()
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

images = BASE_DIR / "images"
if images.exists():
    app.mount("/images", StaticFiles(directory=images), name="images")
