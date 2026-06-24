from __future__ import annotations

import json
import os
import re
import smtplib
import sys
import time
from collections.abc import Callable
from contextlib import contextmanager
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Iterator

DEFAULT_SEND_DELAY = 0.5
DEFAULT_ERROR_LOG = Path("data/account_prepare/notify_send_errors.jsonl")

SUBJECT = "实验室账号已开通 — GSAD 与 NetBird 登录说明"

GSAD_PREEXISTING_NOTE = (
    "  说明：该邮箱此前已在 GSAD 注册，导入已跳过。"
    "请继续使用你原有的登录密码；如遗忘请联系管理员重置。"
)
NETBIRD_PREEXISTING_NOTE = (
    "  说明：该邮箱此前已在 NetBird 注册，导入已跳过。请继续使用你原有的登录密码。"
)


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def netbird_hint_line(dashboard_url: str, *, include_password: bool) -> str:
    if dashboard_url:
        return f"  管理后台：{dashboard_url}\n"
    if include_password:
        return "  请使用 NetBird 客户端，使用上述邮箱和密码登录。\n"
    return "  请使用 NetBird 客户端，使用上述邮箱和你原有的密码登录。\n"


def _footer_notes(*, include_gsad_password: bool, include_netbird_password: bool) -> str:
    if include_gsad_password and include_netbird_password:
        return (
            "1. GSAD 与 NetBird 密码不同，请分别妥善保管，不要转发本邮件。\n"
            "2. 建议首次登录后在 GSAD「修改密码」及 NetBird 客户端中修改为你自己的密码。"
        )
    if include_gsad_password or include_netbird_password:
        return (
            "1. 请妥善保管本邮件中的密码，不要转发本邮件。\n"
            "2. 另一系统请使用你原有的登录密码；建议首次登录后修改为你自己的密码。"
        )
    return "1. 请使用你在 GSAD 与 NetBird 的原有登录信息；如有问题请联系管理员。"


def _gsad_section(
    row: dict[str, Any],
    *,
    gsad_url: str,
    include_password: bool,
) -> str:
    lines = [
        "一、GSAD（GPU 资源申请与 SSH 凭据）",
        f"  登录地址：{gsad_url}",
        f"  登录邮箱：{row['email']}",
    ]
    if include_password:
        lines.extend(
            [
                f"  登录密码：{row['gsad_password']}",
                f"  Linux 用户名：{row['linux_username']}",
                "  （申请 GPU 后 SSH 使用该 Linux 用户名；SSH 密码可在 GSAD「新建申请」中自选或留空由系统生成。）",
            ]
        )
    else:
        lines.extend(
            [
                f"  Linux 用户名：{row['linux_username']}",
                GSAD_PREEXISTING_NOTE,
            ]
        )
    return "\n".join(lines)


def _netbird_section(
    row: dict[str, Any],
    *,
    netbird_dashboard_url: str,
    include_password: bool,
) -> str:
    lines = [
        "二、NetBird（VPN 组网）",
        f"  登录邮箱：{row['email']}",
    ]
    if include_password:
        lines.append(f"  登录密码：{row['netbird_password']}")
    else:
        lines.append(NETBIRD_PREEXISTING_NOTE)
    lines.append(netbird_hint_line(netbird_dashboard_url, include_password=include_password).rstrip())
    return "\n".join(lines)


def build_message(
    row: dict[str, Any],
    *,
    gsad_url: str,
    netbird_dashboard_url: str,
) -> tuple[str, str]:
    include_gsad = bool(row.get("gsad_include_password", True))
    include_netbird = bool(row.get("netbird_include_password", True))

    body = "\n\n".join(
        [
            f"{row['display_name']}，你好：",
            "你的实验室账号已开通，请使用以下信息登录。",
            _gsad_section(row, gsad_url=gsad_url, include_password=include_gsad),
            _netbird_section(
                row,
                netbird_dashboard_url=netbird_dashboard_url,
                include_password=include_netbird,
            ),
            "说明：\n"
            + _footer_notes(
                include_gsad_password=include_gsad,
                include_netbird_password=include_netbird,
            ),
            "如有问题请联系管理员。",
            "此邮件由系统自动发送，请不要直接回复。",
        ]
    )
    return SUBJECT, body


def safe_filename(email: str) -> str:
    return re.sub(r"[^\w.\-@]+", "_", email)


def print_notices(
    rows: list[dict[str, Any]],
    *,
    gsad_url: str,
    netbird_dashboard_url: str,
    subject: str = SUBJECT,
) -> None:
    for i, row in enumerate(rows):
        subj, body = build_message(
            row, gsad_url=gsad_url, netbird_dashboard_url=netbird_dashboard_url
        )
        if i:
            print("\n" + "=" * 60 + "\n")
        print(f"To: {row['email']}")
        print(f"Subject: {subj}")
        print()
        print(body)


def write_notice_files(
    rows: list[dict[str, Any]],
    out_dir: Path,
    *,
    gsad_url: str,
    netbird_dashboard_url: str,
    subject: str = SUBJECT,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        subj, body = build_message(
            row, gsad_url=gsad_url, netbird_dashboard_url=netbird_dashboard_url
        )
        path = out_dir / f"{safe_filename(row['email'])}.txt"
        content = f"To: {row['email']}\nSubject: {subj}\n\n{body}"
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")


def smtp_settings_from_env() -> dict[str, str | int | bool]:
    host = _env("SMTP_HOST")
    user = _env("SMTP_USER")
    password = _env("SMTP_PASSWORD")
    from_addr = _env("SMTP_FROM") or user
    port_raw = _env("SMTP_PORT") or "587"
    port = int(port_raw)

    use_ssl_raw = _env("SMTP_SSL")
    if use_ssl_raw:
        use_ssl = use_ssl_raw not in ("0", "false", "no")
    else:
        use_ssl = port in (465, 994)

    use_tls_raw = _env("SMTP_USE_TLS")
    if use_tls_raw:
        use_tls = use_tls_raw not in ("0", "false", "no")
    else:
        use_tls = not use_ssl

    if not host or not user or not password or not from_addr:
        raise ValueError(
            "Set SMTP in .env: SMTP_HOST, SMTP_USER, SMTP_PASSWORD "
            "(and SMTP_PORT, SMTP_FROM as needed)"
        )
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr,
        "use_ssl": use_ssl,
        "use_tls": use_tls,
    }


def build_mime_message(
    *,
    from_addr: str,
    to_email: str,
    subject: str,
    body: str,
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


@contextmanager
def smtp_session(smtp: dict[str, str | int | bool]) -> Iterator[smtplib.SMTP]:
    host = str(smtp["host"])
    port = int(smtp["port"])
    use_ssl = bool(smtp["use_ssl"])
    use_tls = bool(smtp["use_tls"])

    if use_ssl:
        server: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=60)
    else:
        server = smtplib.SMTP(host, port, timeout=60)

    try:
        if not use_ssl and use_tls:
            server.starttls()
        server.login(str(smtp["user"]), str(smtp["password"]))
        yield server
    finally:
        try:
            server.quit()
        except smtplib.SMTPException:
            pass


def send_with_server(
    server: smtplib.SMTP,
    smtp: dict[str, str | int | bool],
    *,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    from_addr = str(smtp["from_addr"])
    msg = build_mime_message(
        from_addr=from_addr, to_email=to_email, subject=subject, body=body
    )
    server.sendmail(from_addr, [to_email], msg.as_string())


def append_send_error(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def send_delay_seconds(cli_delay: float | None) -> float:
    if cli_delay is not None:
        return max(0.0, cli_delay)
    raw = _env("SMTP_DELAY_SECONDS")
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return DEFAULT_SEND_DELAY


def send_notices(
    rows: list[dict[str, Any]],
    *,
    gsad_url: str,
    netbird_dashboard_url: str,
    subject: str,
    dry_run: bool,
    delay_seconds: float,
    error_log: Path,
    on_sent: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[int, int]:
    if dry_run:
        for row in rows:
            subj, _ = build_message(
                row, gsad_url=gsad_url, netbird_dashboard_url=netbird_dashboard_url
            )
            print(f"[dry-run] would send to {row['email']}: {subj}")
        return 0, 0

    smtp = smtp_settings_from_env()
    ok = 0
    failed = 0

    with smtp_session(smtp) as server:
        for i, row in enumerate(rows):
            to_email = row["email"]
            try:
                subj, body = build_message(
                    row, gsad_url=gsad_url, netbird_dashboard_url=netbird_dashboard_url
                )
                send_with_server(
                    server, smtp, to_email=to_email, subject=subj, body=body
                )
                if on_sent is not None:
                    on_sent(row)
                ok += 1
                print(f"Sent to {to_email}")
            except (smtplib.SMTPException, OSError, ValueError) as e:
                failed += 1
                err_msg = str(e)
                print(f"Failed {to_email}: {err_msg}", file=sys.stderr)
                append_send_error(
                    error_log,
                    {
                        "email": to_email,
                        "display_name": row.get("display_name", ""),
                        "error": err_msg,
                    },
                )

            if delay_seconds > 0 and i < len(rows) - 1:
                time.sleep(delay_seconds)

    print(f"Send summary: ok={ok} failed={failed}", file=sys.stderr)
    if failed:
        print(f"Failures logged to {error_log}", file=sys.stderr)
    return ok, failed
