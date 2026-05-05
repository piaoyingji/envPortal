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
    system_prompt = (
        "You convert cleaned VPN/remote-operation notes into a concise workflow for Japanese operators. "
        "Return only valid JSON array. All operator-facing strings must be Japanese. Keep literal URLs, hosts, usernames, passwords, keys, ports, commands, and proper nouns exactly as written. "
        "The workflow must answer only four questions: 1) what to do before remote work, 2) how to connect, 3) which servers are reached, 4) what to do after work. "
        "Create only 3-6 major steps. Do not create top-level steps for individual credentials, server rows, filenames, headings, parser metadata, or isolated tokens. "
        "Use Japanese titles such as 事前確認, 承認・申請, Azure Portal接続, VPN接続, Bastion接続, 対象サーバ接続, 作業終了連絡. Never output English titles. "
        "Each step object must include order, title, description, action. action is one of request, mail, contact, connect, verify, remote, note. "
        "Optional fields: purpose, operatorAction, requiredInfo:[{label,value}], details:[{label,value}], sourceRefs:[{file,note}], mailTemplate:{to,cc,bcc,subject,body}, credentialGroups:[...]. "
        "Put URLs, account IDs, contacts, notes, and source references into requiredInfo/details only when directly useful. Do not paste full templates or source text. "
        "For every VPN entry, jump host, Bastion, RDP/SSH hop, target server, DB/AP/WEB server, or storage endpoint with credentials, create one credentialGroups item: "
        "{title,host,address,port,protocol,username,password,note,details:[{label,value}]}. "
        "Attach each username, password, shared secret, host, port, and protocol to the exact server/hop it belongs to. Detached username/password lists are invalid. "
        "If one server must be reached through another host, gateway, Bastion, proxy, relay, 踏み台, 経由, or 中継, keep the sequence as ordered major steps and attach credentials to the matching hop. "
        "AzureFiles, Box, and file import/export notes are auxiliary only. Include them only as pre/post-work details when they directly affect file transfer, copy/paste, or completion notice; never make them a main connection step. "
        "If email recipients/CC/BCC and body are present, use action mail and mailTemplate with preserved line breaks. If only a body exists, keep it as normal text. "
        "Ignore customer code/name, parser metadata, form filling instructions, revision history, cover sheets, and general policy text unless they contain a required contact, approval, endpoint, credential, or post-work notice. "
        "Do not invent facts."
    )
    content = ai_chat([
        {
            "role": "system",
            "content": system_prompt,
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
        purpose = str(item.get("purpose") or "").strip()
        operator_action = str(item.get("operatorAction") or item.get("operator_action") or "").strip()
        description = str(item.get("description") or item.get("value") or operator_action or purpose or "").strip()
        title = str(item.get("title") or item.get("step") or "手順").strip()
        if not description and not title:
            continue
        detail_values = []
        detail_values.extend(normalize_details(item.get("requiredInfo") or item.get("required_info")))
        detail_values.extend(normalize_details(item.get("details")))
        detail_values.extend(normalize_source_refs(item.get("sourceRefs") or item.get("source_refs")))
        if purpose:
            detail_values.insert(0, {"label": "目的", "value": purpose})
        if operator_action and operator_action != description:
            detail_values.insert(1 if purpose else 0, {"label": "作業", "value": operator_action})
        steps.append({
            "order": len(steps) + 1,
            "title": title or "手順",
            "description": description or title,
            "action": normalize_action(str(item.get("action") or "note")),
            "details": dedupe_details(detail_values),
            "credentialGroups": normalize_credential_groups(item.get("credentialGroups") or item.get("credentials") or item.get("servers")),
            "mailTemplate": normalize_mail_template(item),
            "source": "ai",
        })
    if not steps:
        raise ValueError("AI workflow did not contain usable steps.")
    if len(steps) > 6:
        steps = coalesce_overfragmented_steps(steps)
    return steps


def coalesce_overfragmented_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: list[dict[str, Any]] = []
    bucket_defs = [
        ("事前確認・申請", "作業前に必要な確認、申請、連絡を行います。", "request", ["申請", "依頼", "許可", "承認", "電話", "連絡", "切替", "request", "contact"]),
        ("LAPLINK接続", "LAPLINKまたは保守端末への接続を行います。", "connect", ["laplink", "アナログ", "保守端末"]),
        ("VPN接続", "VPN接続情報を使用してVPNへ接続します。", "connect", ["vpn", "yms", "yamaha", "forticlient", "共有鍵"]),
        ("対象サーバ接続", "VPNまたは保守端末経由で対象サーバへ接続します。", "remote", ["サーバ", "server", "db", "ap", "ip", "administrator", "windows", "oracle", "remote"]),
        ("作業終了連絡", "作業完了後に必要な終了連絡を行います。", "contact", ["終了", "完了", "報告", "mail"]),
    ]
    for title, description, action, tokens in bucket_defs:
        matched = [step for step in steps if step_matches_bucket(step, tokens)]
        if not matched:
            continue
        buckets.append({
            "order": len(buckets) + 1,
            "title": title,
            "description": description,
            "action": action,
            "details": merge_step_details(matched),
            "credentialGroups": merge_credential_groups(matched),
            "mailTemplate": first_mail_template(matched),
            "source": "ai",
        })
    if buckets:
        return buckets[:6]
    return steps[:6]


def step_matches_bucket(step: dict[str, Any], tokens: list[str]) -> bool:
    text = " ".join([
        str(step.get("title") or ""),
        str(step.get("description") or ""),
        str(step.get("action") or ""),
        json.dumps(step.get("details") or [], ensure_ascii=False),
        json.dumps(step.get("credentialGroups") or [], ensure_ascii=False),
    ]).lower()
    return any(token.lower() in text for token in tokens)


def merge_step_details(steps: list[dict[str, Any]]) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for step in steps:
        title = str(step.get("title") or "").strip()
        description = str(step.get("description") or "").strip()
        if description:
            key = (title or "情報", description)
            if key not in seen:
                seen.add(key)
                details.append({"label": title or "情報", "value": description})
        for detail in step.get("details") or []:
            if not isinstance(detail, dict):
                continue
            label = str(detail.get("label") or "情報").strip()
            value = str(detail.get("value") or "").strip()
            key = (label, value)
            if value and key not in seen:
                seen.add(key)
                details.append({"label": label, "value": value})
    return details[:30]


def merge_credential_groups(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    seen: set[str] = set()
    for step in steps:
        for group in step.get("credentialGroups") or []:
            if not isinstance(group, dict):
                continue
            key = json.dumps(group, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            groups.append(group)
    return groups[:20]


def first_mail_template(steps: list[dict[str, Any]]) -> dict[str, str] | None:
    for step in steps:
        mail = step.get("mailTemplate")
        if isinstance(mail, dict):
            return mail
    return None


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
            details.append({"label": label or "情報", "value": detail_value})
    return details


def normalize_source_refs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    refs: list[dict[str, str]] = []
    for item in value[:12]:
        if isinstance(item, str) and item.strip():
            refs.append({"label": "引用", "value": item.strip()})
        elif isinstance(item, dict):
            file_name = str(item.get("file") or item.get("filename") or item.get("source") or "").strip()
            note = str(item.get("note") or item.get("text") or item.get("reason") or "").strip()
            value = " / ".join(part for part in [file_name, note] if part)
            if value:
                refs.append({"label": "引用", "value": value})
    return refs


def dedupe_details(details: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for detail in details:
        label = str(detail.get("label") or "情報").strip()
        value = str(detail.get("value") or "").strip()
        if not value:
            continue
        key = (label, value)
        if key in seen:
            continue
        seen.add(key)
        result.append({"label": label, "value": value})
    return result[:30]


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
