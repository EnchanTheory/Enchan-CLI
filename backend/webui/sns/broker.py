import json
import logging
import os
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import httpx
import threading
from datetime import datetime, timezone
from urllib.parse import quote

logger = logging.getLogger("enchan.social")

CLI_DIR = Path(__file__).resolve().parents[3]
PRODUCTION_SOCIAL_API_BASE_URL = "https://enchan-social-api-567587925606.asia-northeast1.run.app"
MASCOT_WEBP_ENCODER_VERSION = 1
MASCOT_WEBP_MAX_BYTES = 512 * 1024
MASCOT_FRAME_WIDTH = 192
MASCOT_FRAME_HEIGHT = 208
MASCOT_SHEET_COLUMNS = 8
MASCOT_IDLE_FRAMES = (0, 1, 2, 3, 4, 5)
SNS_BROWSE_TOKEN_BUDGET = 6000
SNS_BROWSE_MAX_POSTS = 30
SNS_BROWSE_MAX_POST_CHARS = 500
LIKED_POST_CACHE_FIELDS = (
    "id", "agent_id", "agent_name", "member_number", "mascot", "mascot_id",
    "mascot_name", "mascot_hash", "mascot_url", "body", "status",
    "like_count", "created_at", "updated_at", "published_at",
)


def _resolve_social_api_base_url() -> str:
    configured = os.environ.get("SOCIAL_API_BASE_URL", "").strip()
    if not configured:
        config_path = CLI_DIR / "enchan_config.json"
        if config_path.is_file():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Failed to read Social API configuration: {exc}") from exc
            configured = str(config.get("social_api_base_url") or "").strip()

    if not configured:
        configured = PRODUCTION_SOCIAL_API_BASE_URL
    if not configured.startswith(("https://", "http://localhost:", "http://127.0.0.1:")):
        raise RuntimeError("Social API URL must use HTTPS, except for a local development server")
    return configured.rstrip("/")

class SocialBroker:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.api_base_url = _resolve_social_api_base_url()
        self.credentials_file = data_dir / "social_credentials.json"
        self.drafts_file = data_dir / "social_drafts.json"
        self.cache_file = data_dir / "social_cache.json"
        self.mascot_sync_file = data_dir / "mascot_sync.json"
        self.mascot_webp_cache_dir = data_dir / "mascot_webp"

        self.mascots_dir = data_dir.parent / "mascots"
        self.builtin_mascots_dir = Path(__file__).resolve().parents[1] / "mascots"
        self.mascot_config = self.mascots_dir / "mascots.json"
        self._drafts_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._mascot_lock = threading.RLock()

        self.client = httpx.Client(timeout=15.0)
        self._ensure_files()
        self._migrate_legacy_drafts()
        self._migrate_legacy_cache()

    def _ensure_files(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.mascot_webp_cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.drafts_file.exists():
            self.drafts_file.write_text("{}", encoding="utf-8")
        if not self.cache_file.exists():
            self._save_cache(self._default_cache())
        if not self.mascot_sync_file.exists():
            self.mascot_sync_file.write_text("{}", encoding="utf-8")

    @staticmethod
    def _default_cache() -> Dict[str, Any]:
        return {
            "version": 5,
            "feed": [],
            "own_posts": [],
            "own_posts_by_mascot": {},
            "liked_posts": [],
            "following": [],
            "followers": [],
            "unread": {"tweets": 0, "following": 0, "followers": 0},
            "unread_tweets_by_mascot": {},
            "last_changes": {"tweets": 0, "following": 0, "followers": 0},
            "last_tweet_changes_by_mascot": {},
            "updated_at": None,
            "seen_post_ids": [],
            "last_browse_at": None,
        }

    @staticmethod
    def _normalize_liked_post(post: Any) -> Dict[str, Any]:
        if not isinstance(post, dict):
            return {}
        post_id = str(post.get("id") or "").strip()
        if not post_id:
            return {}
        normalized = {
            field: post[field]
            for field in LIKED_POST_CACHE_FIELDS
            if field in post
        }
        normalized["id"] = post_id
        normalized["body"] = str(post.get("body") or "")[:SNS_BROWSE_MAX_POST_CHARS]
        normalized["liked_by_me"] = True
        return normalized

    def _load_cache(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        legacy_cache = not isinstance(data, dict) or int(data.get("version", 0) or 0) < 5
        cache = self._default_cache()
        if isinstance(data, dict):
            for key in ("feed", "own_posts", "liked_posts", "following", "followers"):
                if isinstance(data.get(key), list):
                    cache[key] = data[key]
            for key in ("own_posts_by_mascot", "unread_tweets_by_mascot", "last_tweet_changes_by_mascot"):
                if isinstance(data.get(key), dict):
                    cache[key] = data[key]
            for key in ("unread", "last_changes"):
                values = data.get(key)
                if isinstance(values, dict):
                    cache[key] = {
                        section: max(0, int(values.get(section, 0) or 0))
                        for section in ("tweets", "following", "followers")
                    }
            cache["updated_at"] = data.get("updated_at")
            # Remote feed bodies are browse-only and must never persist locally.
            cache["feed"] = []
            if isinstance(data.get("seen_post_ids"), list):
                cache["seen_post_ids"] = [str(item) for item in data["seen_post_ids"] if str(item)]
            cache["last_browse_at"] = data.get("last_browse_at")
            cache["liked_posts"] = [
                normalized
                for post in cache["liked_posts"]
                if (normalized := self._normalize_liked_post(post))
            ]

        active_mascot_id = self._get_active_mascot_id()
        if legacy_cache and not cache["own_posts_by_mascot"] and cache["own_posts"]:
            grouped: Dict[str, list[Dict[str, Any]]] = {}
            for post in cache["own_posts"]:
                mascot_id = str(post.get("mascot_id") or active_mascot_id)
                grouped.setdefault(mascot_id, []).append(post)
            cache["own_posts_by_mascot"] = grouped
        cache["own_posts"] = list(cache["own_posts_by_mascot"].get(active_mascot_id, []))
        legacy_unread_tweets = int(cache["unread"].get("tweets", 0) or 0)
        legacy_last_tweets = int(cache["last_changes"].get("tweets", 0) or 0)
        if legacy_cache and active_mascot_id not in cache["unread_tweets_by_mascot"] and legacy_unread_tweets:
            cache["unread_tweets_by_mascot"][active_mascot_id] = legacy_unread_tweets
        if legacy_cache and active_mascot_id not in cache["last_tweet_changes_by_mascot"] and legacy_last_tweets:
            cache["last_tweet_changes_by_mascot"][active_mascot_id] = legacy_last_tweets
        cache["unread"]["tweets"] = max(
            0, int(cache["unread_tweets_by_mascot"].get(active_mascot_id, 0) or 0)
        )
        cache["last_changes"]["tweets"] = max(
            0, int(cache["last_tweet_changes_by_mascot"].get(active_mascot_id, 0) or 0)
        )
        return cache

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        self.cache_file.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _migrate_legacy_cache(self) -> None:
        with self._cache_lock:
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            if not isinstance(data, dict) or int(data.get("version", 0) or 0) < 5:
                self._save_cache(self._load_cache())

    def get_cached_state(self) -> Dict[str, Any]:
        with self._cache_lock:
            return self._load_cache()

    def mark_cached_state_read(self, section: str) -> Dict[str, Any]:
        if section not in {"tweets", "following", "followers"}:
            raise ValueError("Unknown social section")
        with self._cache_lock:
            cache = self._load_cache()
            cache["unread"][section] = 0
            if section == "tweets":
                cache["unread_tweets_by_mascot"][self._get_active_mascot_id()] = 0
            self._save_cache(cache)
            return cache

    def _set_cached_post_liked(self, post_id: str, liked: bool) -> None:
        with self._cache_lock:
            cache = self._load_cache()
            liked_posts = [
                post for post in cache["liked_posts"]
                if self._record_id(post) != post_id
            ]
            if liked and post_id:
                liked_posts.append({"id": post_id, "liked_by_me": True})
            cache["liked_posts"] = liked_posts
            self._save_cache(cache)

    def _load_credentials(self) -> Dict[str, Any]:
        if not self.credentials_file.exists():
            return {}
        try:
            return json.loads(self.credentials_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_credentials(self, creds: Dict[str, Any]):
        self.credentials_file.write_text(json.dumps(creds, indent=2), encoding="utf-8")
        if os.name != 'nt':
            try:
                self.credentials_file.chmod(0o600)
            except Exception:
                pass

    def is_activated(self) -> bool:
        creds = self._load_credentials()
        return bool(creds.get("agent_token") and creds.get("owner_token"))

    def get_member_number(self) -> Optional[str]:
        return self._load_credentials().get("member_number")

    def get_agent_id(self) -> Optional[str]:
        return self._load_credentials().get("agent_id")

    def _load_mascot_sync_state(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.mascot_sync_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_mascot_sync_state(self, state: Dict[str, Any]) -> None:
        temp = self.mascot_sync_file.with_suffix(".tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.mascot_sync_file)

    def _default_tikta_record(self) -> Dict[str, Any]:
        manifest_path = self.builtin_mascots_dir / "tikta" / "pet.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "id": manifest["id"],
            "name": manifest["displayName"],
            "description": manifest["description"],
            "personality": manifest["personality"],
            "spritesheet": manifest["spritesheetPath"],
            "builtin": True,
        }

    def _get_active_mascot_record(self) -> Tuple[str, Dict[str, Any]]:
        if not self.mascot_config.exists():
            return "tikta", self._default_tikta_record()
        try:
            data = json.loads(self.mascot_config.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "tikta", self._default_tikta_record()
        selected_id = str(data.get("selected", "tikta"))
        mascot = next(
            (item for item in data.get("mascots", []) if item.get("id") == selected_id),
            {},
        )
        if not mascot and selected_id == "tikta":
            mascot = self._default_tikta_record()
        return selected_id, mascot
    def _get_active_mascot_id(self) -> str:
        try:
            selected_id, _ = self._get_active_mascot_record()
            return selected_id
        except Exception:
            return "tikta"

    def _mascot_source_path(self, mascot_id: str, mascot: Dict[str, Any]) -> Optional[Path]:
        spritesheet = str(mascot.get("spritesheet", ""))
        if not spritesheet or Path(spritesheet).name != spritesheet:
            return None
        base = self.builtin_mascots_dir if mascot.get("builtin") else self.mascots_dir
        path = base / mascot_id / spritesheet
        return path if path.is_file() else None

    @staticmethod
    def _encode_mascot_webp(source_bytes: bytes) -> bytes:
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Pillow is required for SNS mascot WebP generation") from exc

        with Image.open(BytesIO(source_bytes)) as source_image:
            source = source_image.convert("RGBA")
        required_width = MASCOT_FRAME_WIDTH * MASCOT_SHEET_COLUMNS
        if source.width < required_width or source.height < MASCOT_FRAME_HEIGHT:
            raise ValueError(
                f"Mascot sheet must be at least {required_width}x{MASCOT_FRAME_HEIGHT} pixels"
            )
        frames = []
        for frame_index in MASCOT_IDLE_FRAMES:
            column = frame_index % MASCOT_SHEET_COLUMNS
            row = frame_index // MASCOT_SHEET_COLUMNS
            left = column * MASCOT_FRAME_WIDTH
            top = row * MASCOT_FRAME_HEIGHT
            frames.append(source.crop((
                left,
                top,
                left + MASCOT_FRAME_WIDTH,
                top + MASCOT_FRAME_HEIGHT,
            )))

        def encode(**options: Any) -> bytes:
            output = BytesIO()
            frames[0].save(
                output,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=[200] * len(frames),
                loop=0,
                disposal=2,
                blend=0,
                method=6,
                **options,
            )
            return output.getvalue()

        encoded = encode(lossless=True)
        if len(encoded) > MASCOT_WEBP_MAX_BYTES:
            encoded = encode(lossless=False, quality=95)
        if len(encoded) > MASCOT_WEBP_MAX_BYTES:
            encoded = encode(lossless=False, quality=90)
        if len(encoded) > MASCOT_WEBP_MAX_BYTES:
            raise ValueError("Generated mascot WebP exceeds the 512 KB server limit")
        return encoded

    def _get_cached_mascot_webp(self, mascot_id: str, source_path: Path) -> bytes:
        source_bytes = source_path.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        webp_path = self.mascot_webp_cache_dir / f"{mascot_id}.webp"
        metadata_path = self.mascot_webp_cache_dir / f"{mascot_id}.json"
        with self._mascot_lock:
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except Exception:
                metadata = {}
            if (
                webp_path.is_file()
                and metadata.get("source_hash") == source_hash
                and metadata.get("encoder_version") == MASCOT_WEBP_ENCODER_VERSION
            ):
                return webp_path.read_bytes()

            encoded = self._encode_mascot_webp(source_bytes)
            temp_webp = webp_path.with_suffix(".webp.tmp")
            temp_metadata = metadata_path.with_suffix(".json.tmp")
            temp_webp.write_bytes(encoded)
            temp_metadata.write_text(json.dumps({
                "source_hash": source_hash,
                "encoder_version": MASCOT_WEBP_ENCODER_VERSION,
                "width": MASCOT_FRAME_WIDTH,
                "height": MASCOT_FRAME_HEIGHT,
                "frames": len(MASCOT_IDLE_FRAMES),
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_webp.replace(webp_path)
            temp_metadata.replace(metadata_path)
            return encoded

    def get_active_mascot_info(self) -> Tuple[str, Optional[bytes]]:
        """Returns the mascot name and cached 192x208 animated WebP bytes."""
        try:
            selected_id, mascot = self._get_active_mascot_record()
            if not mascot:
                return "Tikta", None
            name = mascot.get("name", "Tikta")
            source_path = self._mascot_source_path(selected_id, mascot)
            return (name, self._get_cached_mascot_webp(selected_id, source_path)) if source_path else (name, None)
        except Exception as e:
            logger.warning(f"Failed to load mascot info: {e}")
            return "Tikta", None

    def _compute_mascot_hash(self, img_bytes: bytes) -> str:
        return hashlib.sha256(img_bytes).hexdigest()

    def _upload_and_verify_mascot(
        self,
        upload_url: str,
        img_bytes: bytes,
        mascot_id: str,
        mascot_hash: str,
    ) -> Dict[str, Any]:
        upload = httpx.put(
            upload_url,
            content=img_bytes,
            headers={"Content-Type": "image/webp"},
            timeout=30.0,
        )
        upload.raise_for_status()
        owner_token = self._load_credentials().get("owner_token")
        if not owner_token:
            raise ValueError("Missing owner token")
        verify = self.client.post(
            f"{self.api_base_url}/v1/mascots/{mascot_id}/verify",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"mascot_hash": mascot_hash},
        )
        verify.raise_for_status()
        return verify.json()

    def _api_get(self, endpoint: str, role: str = "agent") -> httpx.Response:
        creds = self._load_credentials()
        token = creds.get(f"{role}_token")
        if not token:
            raise ValueError(f"Missing {role} token")

        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.get(f"{self.api_base_url}{endpoint}", headers=headers)
        return res

    def _api_post(self, endpoint: str, role: str = "agent", json_data: Optional[Dict] = None, headers: Optional[Dict] = None) -> httpx.Response:
        creds = self._load_credentials()
        token = creds.get(f"{role}_token")
        if not token:
            raise ValueError(f"Missing {role} token")

        req_headers = {"Authorization": f"Bearer {token}"}
        if headers:
            req_headers.update(headers)

        res = self.client.post(f"{self.api_base_url}{endpoint}", headers=req_headers, json=json_data)
        return res

    def _api_delete(self, endpoint: str, role: str = "agent") -> httpx.Response:
        creds = self._load_credentials()
        token = creds.get(f"{role}_token")
        if not token:
            raise ValueError(f"Missing {role} token")

        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.delete(f"{self.api_base_url}{endpoint}", headers=headers)
        return res

    def _get_installation_id(self) -> str:
        return "cli-" + hashlib.sha256(str(self.data_dir).encode()).hexdigest()[:16]

    # --- Activation ---
    def request_activation(self) -> Dict[str, Any]:
        res = self.client.post(f"{self.api_base_url}/v1/activation-challenges", json={
            "installation_id": self._get_installation_id()
        })
        res.raise_for_status()
        return res.json()

    def _solve_challenge(self, challenge_id: str, nonce: str, difficulty_bits: int) -> str:
        prefix = f"{challenge_id}\0{nonce}\0".encode("utf-8")
        target = (1 << (256 - difficulty_bits)) - 1
        counter = 0
        while True:
            candidate = f"{counter:x}"
            digest = hashlib.sha256(prefix + candidate.encode("utf-8")).digest()
            val = int.from_bytes(digest, "big")
            if val <= target:
                return candidate
            counter += 1

    def complete_activation(self, challenge: Dict[str, Any], idempotency_key: str) -> Dict[str, Any]:
        challenge_id = challenge["challenge_id"]
        nonce = challenge["nonce"]
        difficulty_bits = challenge["proof_of_work"]["difficulty_bits"]

        solution = self._solve_challenge(challenge_id, nonce, difficulty_bits)
        name, _ = self.get_active_mascot_info()
        mascot_id = self._get_active_mascot_id()
        installation_id = self._get_installation_id()

        headers = {
            "Idempotency-Key": idempotency_key
        }

        res = self.client.post(f"{self.api_base_url}/v1/activations", headers=headers, json={
            "challenge_id": challenge_id,
            "proof_of_work": solution,
            "installation_id": installation_id,
            "display_name": name,
            "mascot": mascot_id,
            "consent_version": "social-consent-v1"
        })
        res.raise_for_status()
        data = res.json()

        creds = self._load_credentials()
        creds["agent_token"] = data["agent_token"]
        creds["owner_token"] = data["owner_token"]
        creds["member_number"] = data["member_number"]
        creds["agent_id"] = data["id"]
        self._save_credentials(creds)
        with self._cache_lock:
            self._save_cache(self._default_cache())

        return data

    # --- Drafts (Local Only) ---
    def _load_drafts(self) -> Dict[str, Any]:
        try:
            return json.loads(self.drafts_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_drafts(self, drafts: Dict[str, Any]):
        self.drafts_file.write_text(json.dumps(drafts, indent=2), encoding="utf-8")

    def _draft_mascot_id(self, draft: Dict[str, Any]) -> str:
        return str(draft.get("mascot_id") or self._get_active_mascot_id())

    def _migrate_legacy_drafts(self) -> None:
        with self._drafts_lock:
            drafts = self._load_drafts()
            active_mascot_id = self._get_active_mascot_id()
            try:
                cached_posts = json.loads(self.cache_file.read_text(encoding="utf-8")).get("own_posts", [])
            except Exception:
                cached_posts = []
            post_mascots = {
                str(post.get("id")): str(post.get("mascot_id"))
                for post in cached_posts
                if post.get("id") and post.get("mascot_id")
            }
            changed = False
            for draft in drafts.values():
                if not draft.get("mascot_id"):
                    draft["mascot_id"] = post_mascots.get(
                        str(draft.get("server_post_id") or ""), active_mascot_id,
                    )
                    changed = True
            if changed:
                self._save_drafts(drafts)

    def create_draft(self, body: str) -> Dict[str, Any]:
        body = body.strip()
        if not body:
            raise ValueError("Draft body is empty")
        if len(body) > 500:
            raise ValueError("Draft body must be 500 characters or fewer")
        with self._drafts_lock:
            drafts = self._load_drafts()
            import uuid
            draft_id = uuid.uuid4().hex
            now = datetime.now(timezone.utc).isoformat()
            draft = {
                "id": draft_id,
                "mascot_id": self._get_active_mascot_id(),
                "body": body,
                "status": "draft",
                "server_post_id": None,
                "like_count": 0,
                "created_at": now,
                "updated_at": now,
            }
            drafts[draft_id] = draft
            self._save_drafts(drafts)
            return draft

    def list_drafts(self) -> list[Dict[str, Any]]:
        with self._drafts_lock:
            active_mascot_id = self._get_active_mascot_id()
            drafts = [
                draft for draft in self._load_drafts().values()
                if self._draft_mascot_id(draft) == active_mascot_id
            ]
        return sorted(drafts, key=lambda item: item.get("created_at", ""), reverse=True)

    def draft_has_remote_post(self, draft_id: str) -> bool:
        with self._drafts_lock:
            draft = self._load_drafts().get(draft_id, {})
            if draft and self._draft_mascot_id(draft) != self._get_active_mascot_id():
                return False
            return bool(draft.get("status") == "published" and draft.get("server_post_id"))

    def delete_draft(self, draft_id: str) -> bool:
        with self._drafts_lock:
            drafts = self._load_drafts()
            draft = drafts.get(draft_id)
            if not draft:
                return False
            if self._draft_mascot_id(draft) != self._get_active_mascot_id():
                return False
            server_post_id = draft.get("server_post_id")
            if draft.get("status") == "published" and server_post_id:
                res = self._api_delete(f"/v1/posts/{server_post_id}", role="owner")
                res.raise_for_status()
            del drafts[draft_id]
            self._save_drafts(drafts)
            return True

    def sync_active_mascot(self) -> None:
        """Syncs the locally selected mascot to the server to ensure it exists before posting."""
        try:
            selected_id, mascot = self._get_active_mascot_record()
            if not mascot:
                return
            name = mascot.get("name", "Tikta")
            _, img_bytes = self.get_active_mascot_info()
            mascot_hash = self._compute_mascot_hash(img_bytes) if img_bytes else None
            sync_state = self._load_mascot_sync_state()
            previous = sync_state.get(selected_id, {})
            if previous.get("name") == name and previous.get("mascot_hash") == mascot_hash:
                return
            needs_upload = bool(mascot_hash and previous.get("mascot_hash") != mascot_hash)
            payload = {"name": name}
            if needs_upload:
                payload["mascot_hash"] = mascot_hash
            res = self._api_put(f"/v1/mascots/{selected_id}", role="owner", json_data=payload)
            res.raise_for_status()
            sync_state[selected_id] = {
                "name": name,
                "mascot_hash": mascot_hash,
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_mascot_sync_state(sync_state)
        except Exception as e:
            logger.warning(f"Failed to sync mascot to server: {e}")

    def _api_put(self, endpoint: str, role: str = "agent", json_data: Optional[Dict] = None, headers: Optional[Dict] = None) -> httpx.Response:
        creds = self._load_credentials()
        token = creds.get(f"{role}_token")
        if not token:
            raise ValueError(f"Missing {role} token")

        req_headers = {"Authorization": f"Bearer {token}"}
        if headers:
            req_headers.update(headers)

        name, img_bytes = self.get_active_mascot_info()
        res = self.client.put(f"{self.api_base_url}{endpoint}", headers=req_headers, json=json_data)

        upload_url = res.headers.get("x-mascot-upload-url")
        # For PUT /v1/mascots, the upload_url is also returned in the JSON body
        try:
            if res.status_code == 200:
                body = res.json()
                if "upload_url" in body:
                    upload_url = body["upload_url"]
        except Exception:
            pass

        if upload_url and img_bytes:
            mascot_id = endpoint.rstrip("/").rsplit("/", 1)[-1]
            mascot_hash = self._compute_mascot_hash(img_bytes)
            self._upload_and_verify_mascot(upload_url, img_bytes, mascot_id, mascot_hash)

        return res

    # --- Owner Actions ---
    def push_draft(self, draft_id: str) -> Dict[str, Any]:
        self.sync_active_mascot()

        with self._drafts_lock:
            drafts = self._load_drafts()
            if draft_id not in drafts:
                raise ValueError("Draft not found")

            draft = drafts[draft_id]
            if draft["status"] == "published":
                raise ValueError("Already published")

            mascot_id = self._draft_mascot_id(draft)
            if mascot_id != self._get_active_mascot_id():
                raise ValueError("Draft belongs to another mascot")

            import uuid
            idempotency_key = uuid.uuid4().hex

            res = self._api_post("/v1/posts", role="owner", json_data={"body": draft["body"], "mascot_id": mascot_id}, headers={"Idempotency-Key": idempotency_key})
            res.raise_for_status()
            data = res.json()

            draft["status"] = "published"
            draft["server_post_id"] = data["id"]
            draft["like_count"] = data.get("like_count", 0)
            draft["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_drafts(drafts)
            return data

    def withdraw_post(self, draft_id: str) -> bool:
        with self._drafts_lock:
            drafts = self._load_drafts()
            if draft_id not in drafts:
                raise ValueError("Draft not found")

            draft = drafts[draft_id]
            if self._draft_mascot_id(draft) != self._get_active_mascot_id():
                raise ValueError("Draft belongs to another mascot")
            if draft["status"] != "published" or not draft["server_post_id"]:
                return False

            res = self._api_delete(f"/v1/posts/{draft['server_post_id']}", role="owner")
            res.raise_for_status()

            draft["status"] = "private"
            draft["server_post_id"] = None
            draft["like_count"] = 0
            draft["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_drafts(drafts)
            return True

    # --- Agent Actions ---
    def get_feed(self) -> list[Dict[str, Any]]:
        res = self._api_get("/v1/feed", role="agent")
        res.raise_for_status()
        return res.json()

    def get_server_read_state(self) -> Dict[str, Any]:
        res = self._api_get("/v1/read-state", role="agent")
        res.raise_for_status()
        return res.json()

    def set_server_read_state(self, cursor: str) -> Dict[str, Any]:
        res = self._api_post("/v1/read-state", role="agent", json_data={"cursor": cursor})
        res.raise_for_status()
        return res.json()

    def get_self_review_history(self, *, max_posts: int = 30, token_budget: int = 6000) -> list[Dict[str, Any]]:
        """Return a bounded recent history of this mascot's own posts for self-review."""
        posts = self.get_own_posts()
        posts.sort(key=lambda item: str(item.get("created_at") or item.get("updated_at") or ""), reverse=True)
        selected: list[Dict[str, Any]] = []
        total = 0
        for post in posts[:max_posts]:
            body = str(post.get("body") or "").strip()
            if not body:
                continue
            cost = max(1, (len(body) + 3) // 4)
            if selected and total + cost > token_budget:
                break
            selected.append({"id": post.get("id"), "created_at": post.get("created_at"), "like_count": int(post.get("like_count", 0) or 0), "body": body})
            total += cost
        return selected

    def get_own_posts(self) -> list[Dict[str, Any]]:
        mascot_id = quote(self._get_active_mascot_id(), safe="")
        res = self._api_get(f"/v1/posts/mine?mascot_id={mascot_id}", role="owner")
        res.raise_for_status()
        return res.json()

    def get_followers(self) -> list[Dict[str, Any]]:
        res = self._api_get("/v1/followers", role="agent")
        res.raise_for_status()
        return res.json()

    def get_liked_posts(self) -> list[Dict[str, Any]]:
        res = self._api_get("/v1/likes?limit=100", role="agent")
        res.raise_for_status()
        return res.json()

    def get_following(self) -> list[Dict[str, Any]]:
        res = self._api_get("/v1/following", role="agent")
        res.raise_for_status()
        return res.json()

    @staticmethod
    def _record_id(record: Dict[str, Any]) -> str:
        return str(
            record.get("id")
            or record.get("agent_id")
            or record.get("member_number")
            or ""
        )

    @staticmethod
    def _estimate_browse_tokens(post: Dict[str, Any]) -> int:
        text = str(post.get("body") or "")[:SNS_BROWSE_MAX_POST_CHARS]
        metadata = f"{post.get('id', '')} {post.get('agent_id', '')} {post.get('agent_name', '')}"
        return max(1, (len(text) + len(metadata)) // 4)

    def browse_remote_state(self, *, advance_cursor: bool = True) -> Dict[str, Any]:
        """Browse a bounded, prioritized remote feed without persisting tweet bodies."""
        read_state = self.get_server_read_state()
        cursor = read_state.get("cursor")
        endpoint = "/v1/feed?limit=100"
        if cursor:
            endpoint += "&after=" + quote(str(cursor), safe="")
        response = self._api_get(endpoint, role="agent")
        response.raise_for_status()
        remote_feed = response.json()
        snapshot = self.sync_remote_state(remote_feed=remote_feed)
        following_ids = {
            self._record_id(person)
            for person in snapshot.get("following", [])
            if self._record_id(person)
        }
        own_agent_id = str(self.get_agent_id() or "")
        candidates = [
            post for post in remote_feed
            if self._record_id(post) and str(post.get("agent_id") or "") != own_agent_id
        ]
        candidates.sort(
            key=lambda post: str(post.get("created_at") or post.get("updated_at") or ""),
            reverse=True,
        )
        candidates.sort(key=lambda post: str(post.get("agent_id") or "") not in following_ids)
        selected: list[Dict[str, Any]] = []
        token_total = 0
        for post in candidates:
            cost = self._estimate_browse_tokens(post)
            if selected and token_total + cost > SNS_BROWSE_TOKEN_BUDGET:
                break
            selected.append({
                **post,
                "body": str(post.get("body") or "")[:SNS_BROWSE_MAX_POST_CHARS],
            })
            token_total += cost
            if len(selected) >= SNS_BROWSE_MAX_POSTS:
                break

        cursor_candidate = None
        if selected:
            cursor_candidate = max(
                str(post.get("created_at") or post.get("updated_at") or "")
                for post in selected
            )
            if advance_cursor:
                self.set_server_read_state(cursor_candidate)
                snapshot["read_cursor"] = cursor_candidate
        return {
            "posts": selected,
            "token_estimate": token_total,
            "state": snapshot,
            "cursor_candidate": cursor_candidate,
        }
    def sync_remote_state(self, *, remote_feed: Optional[list[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Refresh the local SNS snapshot after an explicit remote action."""
        self.sync_active_mascot()
        feed = remote_feed if remote_feed is not None else self.get_feed()
        own_posts = self.get_own_posts()
        liked_posts = [
            normalized
            for post in self.get_liked_posts()
            if (normalized := self._normalize_liked_post(post))
        ]
        following = self.get_following()
        followers = self.get_followers()

        with self._cache_lock:
            previous = self._load_cache()
            active_mascot_id = self._get_active_mascot_id()
            previous_likes = {
                self._record_id(post): int(post.get("like_count", 0) or 0)
                for post in previous["own_posts"]
                if self._record_id(post)
            }
            new_likes = sum(
                max(0, int(post.get("like_count", 0) or 0) - previous_likes.get(self._record_id(post), 0))
                for post in own_posts
                if self._record_id(post)
            )
            previous_following = {self._record_id(person) for person in previous["following"]}
            previous_followers = {self._record_id(person) for person in previous["followers"]}
            new_following = sum(
                1 for person in following
                if self._record_id(person) and self._record_id(person) not in previous_following
            )
            new_followers = sum(
                1 for person in followers
                if self._record_id(person) and self._record_id(person) not in previous_followers
            )
            changes = {
                "tweets": new_likes,
                "following": new_following,
                "followers": new_followers,
            }
            unread = {
                section: int(previous["unread"].get(section, 0) or 0) + changes[section]
                for section in changes
            }
            own_posts_by_mascot = dict(previous["own_posts_by_mascot"])
            own_posts_by_mascot[active_mascot_id] = own_posts
            unread_tweets_by_mascot = dict(previous["unread_tweets_by_mascot"])
            unread_tweets_by_mascot[active_mascot_id] = unread["tweets"]
            last_tweet_changes_by_mascot = dict(previous["last_tweet_changes_by_mascot"])
            last_tweet_changes_by_mascot[active_mascot_id] = changes["tweets"]
            cache = {
                "version": 5,
                "feed": [],
                "own_posts": own_posts,
                "own_posts_by_mascot": own_posts_by_mascot,
                "liked_posts": liked_posts,
                "following": following,
                "followers": followers,
                "unread": unread,
                "unread_tweets_by_mascot": unread_tweets_by_mascot,
                "last_changes": changes,
                "last_tweet_changes_by_mascot": last_tweet_changes_by_mascot,
                "seen_post_ids": list(previous.get("seen_post_ids", [])),
                "last_browse_at": previous.get("last_browse_at"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_cache(cache)

        own_by_id = {
            self._record_id(post): post
            for post in own_posts
            if self._record_id(post)
        }
        with self._drafts_lock:
            drafts = self._load_drafts()
            changed = False
            for draft in drafts.values():
                server_post = own_by_id.get(str(draft.get("server_post_id") or ""))
                if server_post is None:
                    continue
                like_count = int(server_post.get("like_count", 0) or 0)
                if draft.get("like_count") != like_count:
                    draft["like_count"] = like_count
                    changed = True
            if changed:
                self._save_drafts(drafts)
        return cache

    def attach_remote_sync(self, result: Any) -> Dict[str, Any]:
        """Keep a completed remote action successful even if the follow-up refresh fails."""
        try:
            cache = self.sync_remote_state()
            return {"result": result, "sync": cache, "sync_error": None}
        except Exception as exc:
            logger.warning("SNS action completed, but local snapshot refresh failed: %s", exc)
            return {
                "result": result,
                "sync": self.get_cached_state(),
                "sync_error": str(exc),
            }

    def like_post(self, post_id: str) -> Dict[str, Any]:
        res = self._api_post(f"/v1/posts/{post_id}/like", role="agent")
        res.raise_for_status()
        result = res.json()
        self._set_cached_post_liked(post_id, True)
        return result

    def unlike_post(self, post_id: str) -> Dict[str, Any]:
        res = self._api_delete(f"/v1/posts/{post_id}/like", role="agent")
        res.raise_for_status()
        result = res.json()
        self._set_cached_post_liked(post_id, False)
        return result

    def follow(self, agent_id: str) -> Dict[str, Any]:
        res = self._api_post(f"/v1/agents/{agent_id}/follow", role="agent")
        res.raise_for_status()
        return res.json()

    def unfollow(self, agent_id: str) -> Dict[str, Any]:
        res = self._api_delete(f"/v1/agents/{agent_id}/follow", role="agent")
        res.raise_for_status()
        return res.json()
