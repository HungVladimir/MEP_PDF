import re
from hashlib import sha256
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlencode, urlsplit
from uuid import uuid4


REPORT_URL = "/mep_payment/files/"


def session_prefix(keyid: str) -> str:
    digest = sha256(keyid.strip().encode("utf-8")).hexdigest()
    return f"session_v2_{digest}_"


def new_session_name(keyid: str) -> str:
    return session_prefix(keyid) + uuid4().hex


def task_sessions(root: Path, keyid: str, *, include_legacy: bool = True) -> list[Path]:
    prefix = session_prefix(keyid)
    keyid = keyid.strip()
    legacy_prefix = f"session_{keyid}_"
    if not root.is_dir():
        return []

    sessions = []
    resolved_root = root.resolve()
    for path in root.iterdir():
        new_run = path.name.startswith(prefix) and re.fullmatch(r"[0-9a-f]{32}", path.name[len(prefix):])
        # Older directory names end in the upload timestamp.
        legacy_run = (
            include_legacy and path.name.startswith(legacy_prefix)
            and re.fullmatch(r"[0-9]+", path.name[len(legacy_prefix):])
        )
        if (new_run or legacy_run) and path.is_dir() and path.resolve() == resolved_root / path.name:
            sessions.append(path)
    return sorted(sessions, key=lambda path: path.stat().st_mtime, reverse=True)


def valid_filename(filename: str) -> bool:
    return bool(
        filename and filename not in (".", "..") and filename == filename.rstrip(". ")
        and not PureWindowsPath(filename).is_reserved()
        and not re.search(r'[<>:"/\\|?*\x00-\x1f]', filename)
    )


def file_in_directory(directory: Path, path: Path) -> bool:
    return (
        not path.is_symlink() and path.is_file()
        and path.resolve().is_relative_to(directory.resolve())
    )


def report_download_link(keyid: str, filename: str) -> str:
    # Keep Unicode in RESULT_LINK, which has a database length limit.
    name = filename.replace("%", "%25").replace("#", "%23").replace("?", "%3F")
    return f"{REPORT_URL}{name}?{urlencode({'keyid': keyid})}"


def report_filename(link: str | None) -> str | None:
    if not link:
        return None
    parsed = urlsplit(link)
    if parsed.scheme or parsed.netloc or parsed.query or not parsed.path.startswith(REPORT_URL):
        return None
    name = unquote(parsed.path[len(REPORT_URL):])
    if valid_filename(name) and Path(name).suffix.lower() in (".zip", ".xlsx"):
        return name
    return None


def report_variants(filename: str) -> tuple[str, str]:
    path = Path(filename)
    other_suffix = ".xlsx" if path.suffix.lower() == ".zip" else ".zip"
    return filename, path.with_suffix(other_suffix).name
