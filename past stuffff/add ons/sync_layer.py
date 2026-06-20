"""
Sync Layer: Offline-first delta sync with the backend REST API.
Last-write-wins by timestamp. Runs as a background worker.
Android connectivity polling via threading.Timer (Kivy/Android ConnectivityManager
integration via jnius shown in comments for the actual APK build).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
import urllib.request
import urllib.error

from tutor_app.core.sm2_scheduler import SM2Scheduler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONNECTIVITY_POLL_INTERVAL_S = 30
SYNC_TIMEOUT_S = 15
MAX_BATCH_SIZE = 100
API_VERSION = "v1"


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------

class SyncStatus(Enum):
    IDLE = auto()
    SYNCING = auto()
    ERROR = auto()
    OFFLINE = auto()


@dataclass
class SyncResult:
    pushed: int = 0
    pulled: int = 0
    conflicts: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


@dataclass
class ConflictRecord:
    record_id: str
    local_updated_at: str
    remote_updated_at: str
    resolution: str   # "local_wins" | "remote_wins"
    field_conflicts: list[str]


# ---------------------------------------------------------------------------
# Connectivity Checker
# ---------------------------------------------------------------------------

class ConnectivityChecker:
    """
    Polls connectivity by attempting a lightweight HEAD request.
    
    On the actual Android APK, swap this for:
        from jnius import autoclass
        ConnectivityManager = autoclass('android.net.ConnectivityManager')
        ...
    """

    def __init__(self, health_url: str, timeout: float = 3.0):
        self.health_url = health_url
        self.timeout = timeout
        self._last_known_online = False

    def is_online(self) -> bool:
        try:
            req = urllib.request.Request(self.health_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=self.timeout):
                self._last_known_online = True
                return True
        except Exception:
            self._last_known_online = False
            return False

    @property
    def last_known_online(self) -> bool:
        return self._last_known_online


# ---------------------------------------------------------------------------
# REST Client (thin, no external deps)
# ---------------------------------------------------------------------------

class SyncAPIClient:
    """
    Minimal HTTP client for the sync REST API.
    Uses stdlib only — no requests dependency needed on Android.
    """

    def __init__(self, base_url: str, student_id: str, timeout: float = SYNC_TIMEOUT_S):
        self.base_url = base_url.rstrip("/")
        self.student_id = student_id
        self.timeout = timeout

    def push_records(self, records: list[dict]) -> dict:
        """POST /api/v1/sync/push with JSON payload."""
        url = f"{self.base_url}/api/{API_VERSION}/sync/push"
        payload = json.dumps({
            "student_id": self.student_id,
            "records": records,
            "client_timestamp": datetime.utcnow().isoformat(),
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise SyncError(f"HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise SyncError(f"Network error: {e.reason}") from e

    def pull_records(self, since_timestamp: Optional[str] = None) -> dict:
        """GET /api/v1/sync/pull?student_id=...&since=..."""
        params = f"student_id={self.student_id}"
        if since_timestamp:
            params += f"&since={since_timestamp}"
        url = f"{self.base_url}/api/{API_VERSION}/sync/pull?{params}"

        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise SyncError(f"HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise SyncError(f"Network error: {e.reason}") from e

    def get_health(self) -> bool:
        url = f"{self.base_url}/health"
        try:
            with urllib.request.urlopen(url, timeout=3):
                return True
        except Exception:
            return False


class SyncError(Exception):
    pass


# ---------------------------------------------------------------------------
# Conflict Resolver
# ---------------------------------------------------------------------------

class ConflictResolver:
    """
    Last-write-wins by updated_at timestamp.
    For repetition_records: if same timestamp, keep higher repetition_count.
    All conflicts are logged.
    """

    @staticmethod
    def resolve(local: dict, remote: dict) -> tuple[dict, ConflictRecord]:
        local_ts = local.get("updated_at", "")
        remote_ts = remote.get("updated_at", "")
        conflicts = [k for k in ("ease_factor", "interval_days", "repetitions", "next_review")
                     if local.get(k) != remote.get(k)]

        if local_ts > remote_ts:
            winner = local
            resolution = "local_wins"
        elif remote_ts > local_ts:
            winner = remote
            resolution = "remote_wins"
        else:
            # Tie-break: higher repetition count
            if local.get("repetitions", 0) >= remote.get("repetitions", 0):
                winner = local
                resolution = "local_wins_tiebreak"
            else:
                winner = remote
                resolution = "remote_wins_tiebreak"

        log = ConflictRecord(
            record_id=local.get("id", "unknown"),
            local_updated_at=local_ts,
            remote_updated_at=remote_ts,
            resolution=resolution,
            field_conflicts=conflicts,
        )
        logger.info(f"Conflict resolved: {log.record_id} → {resolution}")
        return winner, log


# ---------------------------------------------------------------------------
# SyncLayer (main class)
# ---------------------------------------------------------------------------

class SyncLayer:
    """
    Background sync worker. Polls connectivity every 30s and pushes unsynced
    records to the server, then pulls any remote changes.

    Usage:
        sync = SyncLayer(
            scheduler=sm2_scheduler,
            server_url="https://tutor.example.com",
            student_id="stu_001",
            state_dir=Path("data"),
        )
        sync.start()   # launches background thread
        ...
        sync.stop()
    """

    def __init__(
        self,
        scheduler: SM2Scheduler,
        server_url: str,
        student_id: str,
        state_dir: Path,
        poll_interval: float = CONNECTIVITY_POLL_INTERVAL_S,
    ):
        self.scheduler = scheduler
        self.student_id = student_id
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval

        health_url = urljoin(server_url, "/health")
        self.connectivity = ConnectivityChecker(health_url)
        self.api = SyncAPIClient(server_url, student_id)
        self.resolver = ConflictResolver()

        self._status = SyncStatus.OFFLINE
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._last_pull_ts: Optional[str] = self._load_last_pull_ts()

    # --- Lifecycle ---

    def start(self) -> None:
        """Start background poll-and-sync loop."""
        if self._worker and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._loop, daemon=True, name="SyncWorker")
        self._worker.start()
        logger.info("SyncLayer started")

    def stop(self) -> None:
        """Signal the background thread to stop and wait."""
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=5)
        logger.info("SyncLayer stopped")

    def force_sync(self) -> SyncResult:
        """Trigger an immediate sync (blocking). Safe to call from UI."""
        with self._lock:
            return self._do_sync()

    @property
    def status(self) -> SyncStatus:
        return self._status

    # --- Internal loop ---

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self.connectivity.is_online():
                    with self._lock:
                        result = self._do_sync()
                    if result.success:
                        self._status = SyncStatus.IDLE
                    else:
                        self._status = SyncStatus.ERROR
                        logger.warning(f"Sync errors: {result.errors}")
                else:
                    self._status = SyncStatus.OFFLINE
                    logger.debug("Offline — skipping sync")
            except Exception as exc:
                self._status = SyncStatus.ERROR
                logger.exception(f"Sync loop error: {exc}")

            self._stop_event.wait(timeout=self.poll_interval)

    def _do_sync(self) -> SyncResult:
        self._status = SyncStatus.SYNCING
        result = SyncResult()
        t0 = time.perf_counter()

        try:
            # 1. Push local unsynced records
            unsynced = self.scheduler.get_unsynced_records(self.student_id)
            if unsynced:
                batches = [unsynced[i:i+MAX_BATCH_SIZE] for i in range(0, len(unsynced), MAX_BATCH_SIZE)]
                synced_ids: list[str] = []
                for batch in batches:
                    resp = self.api.push_records(batch)
                    accepted_ids = resp.get("accepted_ids", [])
                    synced_ids.extend(accepted_ids)
                    result.pushed += len(accepted_ids)
                self.scheduler.mark_synced(synced_ids)

            # 2. Pull remote changes
            pull_resp = self.api.pull_records(since_timestamp=self._last_pull_ts)
            remote_records: list[dict] = pull_resp.get("records", [])

            for remote in remote_records:
                conflicts = self._apply_remote_record(remote)
                result.conflicts += conflicts

            result.pulled = len(remote_records)
            if remote_records:
                self._last_pull_ts = pull_resp.get("server_timestamp", datetime.utcnow().isoformat())
                self._save_last_pull_ts(self._last_pull_ts)

        except SyncError as e:
            result.errors.append(str(e))
        except Exception as e:
            result.errors.append(f"Unexpected: {e}")
            logger.exception("Unexpected sync error")

        result.duration_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"Sync complete: pushed={result.pushed} pulled={result.pulled} "
            f"conflicts={result.conflicts} errors={result.errors} "
            f"duration={result.duration_ms:.0f}ms"
        )
        return result

    def _apply_remote_record(self, remote: dict) -> int:
        """
        Merge a remote repetition_record into local DB.
        Returns 1 if a conflict was found, 0 otherwise.
        """
        from contextlib import suppress
        import sqlite3

        with self.scheduler._connect() as conn:
            row = conn.execute(
                "SELECT * FROM repetition_records WHERE id=?", (remote["id"],)
            ).fetchone()
            local = dict(row) if row else None

        if local is None:
            # New record from server — insert directly
            self._insert_remote_record(remote)
            return 0

        # Check for conflict
        if local.get("updated_at") == remote.get("updated_at"):
            return 0  # Already in sync

        winner, conflict_log = self.resolver.resolve(local, remote)
        if conflict_log.resolution.startswith("remote"):
            self._update_from_remote(winner)
            return 1

        return 0  # Local wins — nothing to do

    def _insert_remote_record(self, record: dict) -> None:
        with self.scheduler._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO repetition_records
                    (id, student_id, item_id, ease_factor, interval_days,
                     repetitions, last_quality, next_review, updated_at, synced)
                VALUES (:id, :student_id, :item_id, :ease_factor, :interval_days,
                        :repetitions, :last_quality, :next_review, :updated_at, 1)
            """, record)

    def _update_from_remote(self, record: dict) -> None:
        with self.scheduler._connect() as conn:
            conn.execute("""
                UPDATE repetition_records
                SET ease_factor=:ease_factor, interval_days=:interval_days,
                    repetitions=:repetitions, last_quality=:last_quality,
                    next_review=:next_review, updated_at=:updated_at, synced=1
                WHERE id=:id
            """, record)

    # --- State persistence ---

    def _load_last_pull_ts(self) -> Optional[str]:
        path = self.state_dir / "last_pull.txt"
        if path.exists():
            return path.read_text().strip() or None
        return None

    def _save_last_pull_ts(self, ts: str) -> None:
        (self.state_dir / "last_pull.txt").write_text(ts)
