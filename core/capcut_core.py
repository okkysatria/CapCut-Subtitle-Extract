from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Set

DEFAULT_DRAFT_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "CapCut", "User Data", "Projects", "com.lveditor.draft",
)
IGNORED_DIRS = {".recycle_bin", "Timelines", "subdraft"}
DRAFT_FILES = ("draft_content.json", "draft_content.json.bak", "draft_info.json")
META_FILE = "draft_meta_info.json"

WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

ORIGIN_ALL = "all"
ORIGIN_AUTO = "auto"
ORIGIN_MANUAL = "manual"

FORMAT_EXT = {"srt": ".srt", "vtt": ".vtt", "txt": ".txt", "csv": ".csv", "json": ".json"}


@dataclass
class Subtitle:
    index: int
    start_us: int
    end_us: int
    text: str
    origin: str
    material_id: str = ""


@dataclass
class Project:
    folder: str
    name: str
    title: str
    modified: float = 0.0
    subtitles: List[Subtitle] = field(default_factory=list)
    error: str = ""

    @property
    def total(self) -> int:
        return len(self.subtitles)

    @property
    def auto_count(self) -> int:
        return sum(1 for s in self.subtitles if s.origin == ORIGIN_AUTO)

    @property
    def manual_count(self) -> int:
        return sum(1 for s in self.subtitles if s.origin == ORIGIN_MANUAL)


def us_to_ms(time_us) -> int:
    if time_us is None:
        return 0
    try:
        return max(0, int(round(float(time_us) / 1000.0)))
    except (TypeError, ValueError):
        return 0


def _split_ms(total_ms: int):
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return hours, minutes, seconds, millis


def format_srt_time(time_us) -> str:
    h, m, s, ms = _split_ms(us_to_ms(time_us))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_vtt_time(time_us) -> str:
    h, m, s, ms = _split_ms(us_to_ms(time_us))
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
_CAPCUT_DELIM_RE = re.compile(r"\[\|\]|\|\|")
_HSPACE_RE = re.compile(r"[ \t\f\v]+")


def sanitize_text(text: str) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub("", text)
    text = _CAPCUT_DELIM_RE.sub(" ", text)
    lines = []
    for line in text.splitlines():
        cleaned_line = _HSPACE_RE.sub(" ", line).strip()
        if cleaned_line:
            lines.append(cleaned_line)
    return "\n".join(lines)


def extract_text(content) -> str:
    if isinstance(content, dict):
        value = content.get("text", "")
        return value if isinstance(value, str) else ""
    if not isinstance(content, str):
        return ""
    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
        except (ValueError, TypeError):
            obj = None
        if isinstance(obj, dict) and isinstance(obj.get("text"), str):
            return obj["text"]
    return content


def extract_text_from_material(material: dict) -> str:
    text = extract_text(material.get("content"))
    if not text:
        words = material.get("words")
        if isinstance(words, list) and words:
            extracted = []
            for w in words:
                if isinstance(w, dict):
                    wt = w.get("text") or w.get("word") or ""
                    if wt:
                        extracted.append(str(wt))
                elif isinstance(w, str) and w:
                    extracted.append(w)
            if extracted:
                text = " ".join(extracted)
    return text


def _has_words(words) -> bool:
    if isinstance(words, dict):
        return any(bool(v) for v in words.values())
    if isinstance(words, (list, tuple)):
        return len(words) > 0
    return False


def classify_origin(material: dict) -> str:
    add_type = material.get("add_type")
    if add_type in (1, "1"):
        return ORIGIN_AUTO
    if add_type in (2, "2"):
        return ORIGIN_MANUAL
    if (
        _has_words(material.get("words"))
        or material.get("caption_type") == 1
        or material.get("subtitle_type") == 1
        or material.get("recognize_type") is not None
    ):
        return ORIGIN_AUTO
    return ORIGIN_MANUAL


def _to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def extract_subtitles(draft: dict) -> List[Subtitle]:
    materials = draft.get("materials") or {}
    texts = (materials.get("texts") or []) + (materials.get("subtitles") or [])
    mat_map: Dict[str, dict] = {
        m["id"]: m for m in texts if isinstance(m, dict) and m.get("id")
    }
    cache: Dict[str, tuple] = {}
    entries = []
    seen = set()
    for track in draft.get("tracks") or []:
        if not isinstance(track, dict) or track.get("type") not in ("text", "subtitle"):
            continue
        for seg in track.get("segments") or []:
            if not isinstance(seg, dict):
                continue
            mid = seg.get("material_id")
            mat = mat_map.get(mid)
            if mat is None:
                continue
            if mid not in cache:
                cache[mid] = (
                    sanitize_text(extract_text_from_material(mat)),
                    classify_origin(mat),
                )
            text, origin = cache[mid]
            if not text:
                continue
            tr = seg.get("target_timerange") or {}
            start = _to_int(tr.get("start"))
            duration = _to_int(tr.get("duration"))
            if duration <= 0:
                continue
            end = start + duration
            key = (start, end, text, origin)
            if key not in seen:
                seen.add(key)
                entries.append((start, end, text, origin, mid))
    entries.sort(key=lambda e: (e[0], e[1]))
    return [
        Subtitle(i, st, en, tx, og, mid)
        for i, (st, en, tx, og, mid) in enumerate(entries, 1)
    ]


def filter_by_origin(subs: Iterable[Subtitle], origin: str) -> List[Subtitle]:
    if origin in (ORIGIN_AUTO, ORIGIN_MANUAL):
        return [s for s in subs if s.origin == origin]
    return list(subs)


def _load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            return json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def discover_title(folder: str) -> str:
    data = _load_json(os.path.join(folder, META_FILE))
    if isinstance(data, dict):
        for key in ("draft_name", "title", "name"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return os.path.basename(folder.rstrip("\\/"))


def list_project_dirs(root: str) -> List[str]:
    dirs = []
    try:
        with os.scandir(root) as it:
            for entry in it:
                if (
                    entry.is_dir()
                    and not entry.name.startswith(".")
                    and entry.name not in IGNORED_DIRS
                ):
                    dirs.append(entry.path)
    except OSError:
        return []

    def mtime(p: str) -> float:
        try:
            return os.path.getmtime(p)
        except OSError:
            return 0.0

    dirs.sort(key=mtime, reverse=True)
    return dirs


def load_project(folder: str) -> Optional[Project]:
    draft_path = next(
        (os.path.join(folder, n) for n in DRAFT_FILES
         if os.path.isfile(os.path.join(folder, n))),
        None,
    )
    if draft_path is None:
        return None
    try:
        modified = os.path.getmtime(draft_path)
    except OSError:
        modified = 0.0

    meta_path = os.path.join(folder, META_FILE)
    meta_data = _load_json(meta_path)
    title = os.path.basename(folder.rstrip("\\/"))
    if isinstance(meta_data, dict):
        for key in ("draft_name", "title", "name"):
            val = meta_data.get(key)
            if isinstance(val, str) and val.strip():
                title = val.strip()
                break
        tm = _to_int(meta_data.get("tm_draft_modified"))
        if tm > 0:
            modified = tm / 1_000_000.0

    project = Project(
        folder=folder,
        name=os.path.basename(folder.rstrip("\\/")),
        title=title,
        modified=modified,
    )

    data = _load_json(draft_path)
    if not isinstance(data, dict):
        bak_path = os.path.join(folder, "draft_content.json.bak")
        if os.path.isfile(bak_path) and bak_path != draft_path:
            data = _load_json(bak_path)

    if not isinstance(data, dict):
        project.error = "Draft cannot be read (it may be encrypted by CapCut)."
        return project
    try:
        project.subtitles = extract_subtitles(data)
    except Exception as exc:
        project.error = f"Failed to process draft: {exc}"
    return project


def scan_projects(
    root: str,
    on_project: Optional[Callable[[Project], None]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> List[Project]:
    projects: List[Project] = []
    dirs = list_project_dirs(root)
    total = len(dirs)
    for i, folder in enumerate(dirs, 1):
        if should_cancel and should_cancel():
            break
        project = load_project(folder)
        if project is not None:
            projects.append(project)
            if on_project:
                on_project(project)
        if on_progress:
            on_progress(i, total)
    return projects


def to_srt(subs: List[Subtitle]) -> str:
    blocks = []
    for i, s in enumerate(subs, 1):
        blocks.append(
            f"{i}\n{format_srt_time(s.start_us)} --> {format_srt_time(s.end_us)}\n{s.text}"
        )
    return ("\n\n".join(blocks) + "\n") if blocks else ""


def to_vtt(subs: List[Subtitle]) -> str:
    blocks = []
    for i, s in enumerate(subs, 1):
        blocks.append(
            f"{i}\n{format_vtt_time(s.start_us)} --> {format_vtt_time(s.end_us)}\n{s.text}"
        )
    if not blocks:
        return "WEBVTT\n"
    return "WEBVTT\n\n" + "\n\n".join(blocks) + "\n"


def to_txt(subs: List[Subtitle]) -> str:
    return "\n".join(s.text for s in subs) + ("\n" if subs else "")


def to_csv(subs: List[Subtitle]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(
        ["sub_number", "start_us", "end_us", "srt_start", "srt_end", "origin", "content"]
    )
    for i, s in enumerate(subs, 1):
        writer.writerow(
            [i, s.start_us, s.end_us, format_srt_time(s.start_us),
             format_srt_time(s.end_us), s.origin, s.text]
        )
    return buf.getvalue()


def to_json(subs: List[Subtitle], project: Optional[Project] = None) -> str:
    payload = {
        "project": project.title if project else "",
        "folder": project.folder if project else "",
        "total": len(subs),
        "subtitles": [
            {
                "sub_number": i,
                "start_us": s.start_us,
                "end_us": s.end_us,
                "duration_us": max(0, s.end_us - s.start_us),
                "srt_start": format_srt_time(s.start_us),
                "srt_end": format_srt_time(s.end_us),
                "origin": s.origin,
                "content": s.text,
            }
            for i, s in enumerate(subs, 1)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_format(fmt: str, subs: List[Subtitle], project: Optional[Project] = None) -> str:
    if fmt == "srt":
        return to_srt(subs)
    if fmt == "vtt":
        return to_vtt(subs)
    if fmt == "txt":
        return to_txt(subs)
    if fmt == "csv":
        return to_csv(subs)
    if fmt == "json":
        return to_json(subs, project)
    raise ValueError(f"Unknown format: {fmt}")


_BAD_FILENAME_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def safe_filename(name: str) -> str:
    cleaned = _BAD_FILENAME_RE.sub("_", name).strip(" .")
    if not cleaned:
        cleaned = "untitled"
    cleaned = cleaned[:120].rstrip(" .") or "untitled"
    if cleaned.upper() in WINDOWS_RESERVED:
        cleaned = f"{cleaned}_subtitles"
    return cleaned


def unique_basename(title: str, used: Set[str]) -> str:
    base = safe_filename(title)
    name, n = base, 2
    while name.lower() in used:
        name = f"{base} ({n})"
        n += 1
    used.add(name.lower())
    return name


def export_file(project: Project, subs: List[Subtitle], fmt: str, out_dir: str, basename: str) -> str:
    content = render_format(fmt, subs, project)
    path = os.path.join(out_dir, basename + FORMAT_EXT[fmt])
    encoding = "utf-8" if fmt == "json" else "utf-8-sig"
    with open(path, "w", encoding=encoding, newline="") as fh:
        fh.write(content)
    return path
