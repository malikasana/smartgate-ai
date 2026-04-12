import json
import os
from datetime import datetime, timedelta


class Storage:
    def __init__(self, storage_dir: str = ".", reset_days: int = 30):
        self.storage_dir = storage_dir
        self.reset_days = reset_days

        self.bans_file = os.path.join(storage_dir, "sg_bans.json")
        self.hashes_file = os.path.join(storage_dir, "sg_hashes.json")
        self.index_file = os.path.join(storage_dir, "sg_index.json")

        self._init_file(self.bans_file, {"bans": {}})
        self._init_file(self.hashes_file, {"hashes": []})
        self._init_file(self.index_file, {"index": []})

        print(f"💾 [STORAGE] Initialized at: {storage_dir}")

    def _init_file(self, path: str, default: dict):
        if not os.path.exists(path):
            with open(path, 'w') as f:
                json.dump(default, f, indent=2)
            print(f"💾 [STORAGE] Created: {path}")

    def _read(self, path: str) -> dict:
        with open(path, 'r') as f:
            return json.load(f)

    def _write(self, path: str, data: dict):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    # ── IP Ban Management ─────────────────────────────────────

    def get_rejection_count(self, ip: str) -> int:
        data = self._read(self.bans_file)
        entry = data["bans"].get(ip)
        if not entry:
            return 0
        if self._is_expired(entry["last_rejected"]):
            self.clear_ip(ip)
            return 0
        return entry["count"]

    def increment_rejection(self, ip: str):
        data = self._read(self.bans_file)
        if ip not in data["bans"]:
            data["bans"][ip] = {"count": 0, "last_rejected": ""}
        data["bans"][ip]["count"] += 1
        data["bans"][ip]["last_rejected"] = datetime.now().isoformat()
        self._write(self.bans_file, data)
        print(f"💾 [STORAGE] IP {ip} rejection count: {data['bans'][ip]['count']}")

    def block_ip(self, ip: str):
        data = self._read(self.bans_file)
        data["bans"][ip] = {
            "count": 9999,
            "last_rejected": datetime.now().isoformat()
        }
        self._write(self.bans_file, data)
        print(f"💾 [STORAGE] IP {ip} manually blocked")

    def unblock_ip(self, ip: str):
        data = self._read(self.bans_file)
        if ip in data["bans"]:
            del data["bans"][ip]
            self._write(self.bans_file, data)
            print(f"💾 [STORAGE] IP {ip} unblocked")

    def clear_ip(self, ip: str):
        data = self._read(self.bans_file)
        if ip in data["bans"]:
            del data["bans"][ip]
            self._write(self.bans_file, data)

    def clear_all_bans(self):
        self._write(self.bans_file, {"bans": {}})
        print(f"💾 [STORAGE] All bans cleared")

    def get_all_bans(self) -> dict:
        return self._read(self.bans_file)["bans"]

    def _is_expired(self, last_rejected: str) -> bool:
        if not last_rejected:
            return True
        last = datetime.fromisoformat(last_rejected)
        return datetime.now() - last > timedelta(days=self.reset_days)

    # ── Hash Management ───────────────────────────────────────

    def get_hashes(self) -> list:
        return self._read(self.hashes_file)["hashes"]

    def add_hash(self, hash_value: str):
        data = self._read(self.hashes_file)
        data["hashes"].append(hash_value)
        self._write(self.hashes_file, data)

    def clear_hashes(self):
        self._write(self.hashes_file, {"hashes": []})
        print(f"💾 [STORAGE] All hashes cleared")

    # ── Index Management ──────────────────────────────────────

    def get_index(self) -> list:
        return self._read(self.index_file)["index"]

    def add_to_index(self, fields: dict):
        data = self._read(self.index_file)
        data["index"].append(fields)
        self._write(self.index_file, data)

    def clear_index(self):
        self._write(self.index_file, {"index": []})
        print(f"💾 [STORAGE] Index cleared")

    # ── Stats ─────────────────────────────────────────────────

    def print_stats(self):
        bans = self.get_all_bans()
        hashes = self.get_hashes()
        index = self.get_index()
        print(f"\n{'='*40}")
        print(f"📊 SMARTGATE STORAGE STATS")
        print(f"{'='*40}")
        print(f"Banned IPs: {len(bans)}")
        print(f"Saved hashes: {len(hashes)}")
        print(f"Index entries: {len(index)}")
        print(f"{'='*40}\n")