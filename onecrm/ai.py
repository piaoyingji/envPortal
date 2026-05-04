from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from .crypto import decrypt_text
from .settings import AI_CREDENTIAL_FILE, AI_ENDPOINT, AI_MODEL, AI_TIMEOUT_SECONDS, BASE_DIR


def ai_configured() -> bool:
    return bool(AI_ENDPOINT and AI_CREDENTIAL_FILE and ai_api_key())


def ai_api_key() -> str:
    if not AI_CREDENTIAL_FILE:
        return ""
    path = Path(AI_CREDENTIAL_FILE)
    if not path.is_absolute():
        path = BASE_DIR / path
    if not path.exists():
        return ""
    return decrypt_text(path.read_text(encoding="utf-8").strip())


def ai_chat(messages: list[dict[str, str]]) -> str:
    api_key = ai_api_key()
    if not AI_ENDPOINT or not api_key:
        raise RuntimeError("AI endpoint or credential is not configured.")
    payload = json.dumps({
        "model": AI_MODEL,
        "messages": messages,
        "temperature": 0,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{AI_ENDPOINT}/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=AI_TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    return data["choices"][0]["message"]["content"]


def summarize_vpn_workflow_with_ai(raw_text: str) -> list[dict[str, Any]]:
    text = (raw_text or "").strip()
    if not text:
        return []
    content = ai_chat([
        {
            "role": "system",
            "content": (
                "You convert messy VPN operation notes into a concise operator workflow. "
                "Return only valid JSON. The JSON must be an array. Each item must have "
                "order:number, title:string, description:string, action:string. "
                "Each item may also have details, an array of {label:string,value:string}. "
                "When a step contains one or more servers, hosts, jump hosts, remote desktops, database consoles, VPN portals, or any credentials bound to a host, add credentialGroups. "
                "credentialGroups must be an array of {title,host,address,port,protocol,username,password,note,details:[{label,value}]}. "
                "Every username, password, shared secret, server address, host name, port, and protocol must be placed in the credentialGroups object for the exact server/hop it belongs to. "
                "If the source lists several servers in a table or adjacent rows, create one credentialGroups item per server row and keep the row's username/password paired with that server. "
                "Do not put a list of hosts followed by a separate list of usernames/passwords in generic details; that loses association and is invalid. "
                "For any step that involves sending an email and includes recipients, CC, or BCC, set action to mail and include "
                "mailTemplate:{to:string,cc:string,bcc:string,subject:string,body:string}. "
                "The mailTemplate body must be copy-ready and preserve formal line breaks, blank lines, indentation, greetings, request details, and signature placeholders. "
                "Do not flatten email content into description or details when it should be sent as a message. "
                "If there is only mail body text without to/cc/bcc, do not create mailTemplate; keep it as a normal detail or description. "
                "Use action values from: request, mail, contact, connect, verify, remote, note. "
                "If a step requires applying for VPN/remote permission by email, phone, contact, approval, request, or any similar application process, make that step action request or contact. "
                "Group related credentials into the same step instead of splitting every line. "
                "Credentials are critical operation data. Put URLs, hosts, ports, account IDs, usernames, passwords, shared secrets, OTP notes, contacts, and remarks in details when possible. "
                "Keep passwords, shared secrets, account names, URLs, customer contacts, and mail instructions exactly when present; never mask, omit, summarize, or replace them. "
                "For credentials, use standalone detail objects such as {label:'VPN username',value:'...'} and {label:'VPN password',value:'...'} instead of mixing labels and values into long sentences. "
                "Treat Source and Path context lines as semantic source text. Japanese file or folder names may express scope or precedence, such as '20260501以降', '新サーバ', '補足', '追加', or '旧'; use that meaning when deciding which instructions apply. "
                "When the input contains a Source precedence section, use it to decide the current effective procedure. Prefer current/override/supplement sources over historical sources, and use client modified dates, path dates, and content date hints to resolve conflicts. "
                "If sources conflict, output the final adopted instruction in the step and keep the source filename/path in details when useful. Historical sources may be referenced only as old information and must not override newer effective instructions. "
                "If connection notes say one server must be reached through another host, jump server, bastion, gateway, proxy, relay, '踏み台', '経由', '中継', or similar, split it into ordered connection steps. "
                "Keep credentials attached to the exact host or hop they belong to, and do not flatten all servers into one generic remote connection detail list. "
                "Do not create steps or details for customer/organization code or customer/organization name by themselves; those are page context, not operating procedure. "
                "Ignore content unrelated to VPN, remote access, connection approval, servers used for remote operation, credentials, contacts, or mail templates. "
                "Do not invent facts."
            ),
        },
        {
            "role": "user",
            "content": text,
        },
    ])
    return normalize_ai_steps(parse_json_array(content))


def parse_json_array(content: str) -> Any:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        text = match.group(0)
    return json.loads(text)


def normalize_ai_steps(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("AI workflow is not a JSON array.")
    steps: list[dict[str, Any]] = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        description = str(item.get("description") or item.get("value") or "").strip()
        title = str(item.get("title") or item.get("step") or "手順").strip()
        if not description and not title:
            continue
        steps.append({
            "order": len(steps) + 1,
            "title": title or "手順",
            "description": description or title,
            "action": normalize_action(str(item.get("action") or "note")),
            "details": normalize_details(item.get("details")),
            "credentialGroups": normalize_credential_groups(item.get("credentialGroups") or item.get("credentials") or item.get("servers")),
            "mailTemplate": normalize_mail_template(item),
            "source": "ai",
        })
    if not steps:
        raise ValueError("AI workflow did not contain usable steps.")
    return steps


def normalize_action(value: str) -> str:
    action = value.strip().lower()
    if action in {"request", "mail", "contact", "connect", "verify", "remote", "note"}:
        return action
    return "note"


def normalize_details(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    details: list[dict[str, str]] = []
    for item in value[:30]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        detail_value = str(item.get("value") or "").strip()
        if label or detail_value:
            details.append({"label": label or "Info", "value": detail_value})
    return details


def normalize_credential_groups(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    groups: list[dict[str, Any]] = []
    for item in value[:20]:
        if not isinstance(item, dict):
            continue
        details = normalize_details(item.get("details"))
        group = {
            "title": str(item.get("title") or item.get("name") or item.get("server") or item.get("host") or "").strip(),
            "host": str(item.get("host") or item.get("hostname") or "").strip(),
            "address": str(item.get("address") or item.get("ip") or item.get("url") or "").strip(),
            "port": str(item.get("port") or "").strip(),
            "protocol": str(item.get("protocol") or item.get("type") or "").strip(),
            "username": str(item.get("username") or item.get("user") or item.get("loginId") or item.get("account") or "").strip(),
            "password": str(item.get("password") or item.get("pwd") or item.get("pass") or "").strip(),
            "note": str(item.get("note") or item.get("memo") or item.get("remark") or "").strip(),
            "details": details,
        }
        if any(group.get(key) for key in ["title", "host", "address", "port", "protocol", "username", "password", "note"]) or details:
            groups.append(group)
    return groups


def normalize_mail_template(item: dict[str, Any]) -> dict[str, str] | None:
    value = (
        item.get("mailTemplate")
        or item.get("emailTemplate")
        or item.get("mail")
        or item.get("email")
    )
    if not isinstance(value, dict):
        return None
    body = str(value.get("body") or value.get("content") or value.get("text") or "").strip()
    subject = str(value.get("subject") or value.get("title") or "").strip()
    to = str(value.get("to") or value.get("宛先") or value.get("收件人") or "").strip()
    cc = str(value.get("cc") or value.get("CC") or "").strip()
    bcc = str(value.get("bcc") or value.get("BCC") or value.get("bcc_mail") or "").strip()
    if not any([to, cc, bcc, subject, body]):
        return None
    return {
        "to": to,
        "cc": cc,
        "bcc": bcc,
        "subject": subject,
        "body": body,
    }
