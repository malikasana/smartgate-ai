import hashlib
import json
from .ai import AIValidator
from .storage import Storage


class Pipeline:
    def __init__(
        self,
        ai_validator: AIValidator,
        storage: Storage,
        database,
        index_fields: list,
        rejection_threshold: int = 5,
        queue_limit: int = 100,
        max_data_size: int = 1024,
        send_rejection_reason: bool = True,
    ):
        self.ai = ai_validator
        self.storage = storage
        self.database = database
        self.index_fields = index_fields
        self.rejection_threshold = rejection_threshold
        self.queue_limit = queue_limit
        self.max_data_size = max_data_size
        self.send_rejection_reason = send_rejection_reason
        self.current_queue = 0

        print(f"⚙️ [PIPELINE] Initialized with:")
        print(f"   rejection_threshold = {rejection_threshold}")
        print(f"   queue_limit = {queue_limit}")
        print(f"   max_data_size = {max_data_size}")
        print(f"   send_rejection_reason = {send_rejection_reason}")
        print(f"   index_fields = {index_fields}")

    def process(self, ip: str, data: dict) -> dict:
        print(f"\n{'='*50}")
        print(f"📥 [PIPELINE] New request from IP: {ip}")
        print(f"📥 [PIPELINE] Data: {data}")

        # ── Layer 1: IP check ─────────────────────────────────
        print(f"\n🔒 [LAYER 1] IP Check...")
        count = self.storage.get_rejection_count(ip)
        print(f"🔒 [LAYER 1] Rejection count for {ip}: {count}")
        if count >= self.rejection_threshold:
            print(f"🚫 [LAYER 1] IP BLOCKED: {ip}")
            return self._reject("Too many rejections from your IP")

        # ── Layer 2: Queue check ──────────────────────────────
        print(f"\n🔒 [LAYER 2] Queue Check...")
        print(f"🔒 [LAYER 2] Current queue: {self.current_queue}/{self.queue_limit}")
        if self.current_queue >= self.queue_limit:
            print(f"🚫 [LAYER 2] Queue full")
            return {"status": "wait", "reason": "Server busy, please try again later"}
        self.current_queue += 1
        print(f"✅ [LAYER 2] Queue passed. Size now: {self.current_queue}")

        try:
            # ── Layer 3: Size check ───────────────────────────
            print(f"\n🔒 [LAYER 3] Size Check...")
            raw = json.dumps(data)
            data_size = len(raw)
            print(f"🔒 [LAYER 3] Data size: {data_size} bytes (limit: {self.max_data_size})")
            if data_size > self.max_data_size:
                print(f"🚫 [LAYER 3] Data too large")
                self.storage.increment_rejection(ip)
                return self._reject(f"Data too large: {data_size} bytes")
            print(f"✅ [LAYER 3] Size check passed")

            # ── Layer 4: Hash duplicate check ─────────────────
            print(f"\n🔒 [LAYER 4] Hash Duplicate Check...")
            data_hash = self._hash(data)
            existing_hashes = self.storage.get_hashes()
            print(f"🔒 [LAYER 4] Existing hashes: {len(existing_hashes)}")
            if data_hash in existing_hashes:
                print(f"🚫 [LAYER 4] Exact duplicate detected")
                self.storage.increment_rejection(ip)
                return self._reject("Exact duplicate data")
            print(f"✅ [LAYER 4] Hash check passed")

            # ── Layer 5: AI semantic validation ───────────────
            print(f"\n🔒 [LAYER 5] AI Semantic Validation...")
            existing_index = self.storage.get_index()
            ai_result = self.ai.validate(data, existing_index)

            if not ai_result.get("allowed"):
                print(f"🚫 [LAYER 5] AI rejected: {ai_result.get('reason')}")
                self.storage.increment_rejection(ip)
                return self._reject(ai_result.get("reason", "Data rejected by AI"))
            print(f"✅ [LAYER 5] AI validation passed")

            # ── Layer 6: Save to database ──────────────────────
            print(f"\n💾 [LAYER 6] Saving to database...")
            self.database.save(data)
            self.storage.add_hash(data_hash)
            index_entry = {field: data.get(field, "") for field in self.index_fields}
            self.storage.add_to_index(index_entry)
            print(f"✅ [LAYER 6] Saved successfully")
            print(f"✅ [PIPELINE] ACCEPTED")

            return {"status": "accepted", "reason": "Data saved successfully"}

        except Exception as e:
            print(f"🚨 [PIPELINE] Unexpected error: {e}")
            return {"status": "error", "reason": f"Internal error: {str(e)}"}

        finally:
            self.current_queue -= 1
            print(f"🔒 [QUEUE] Queue back to: {self.current_queue}")

    def _hash(self, data: dict) -> str:
        raw = json.dumps(data, sort_keys=True)
        hash_value = hashlib.sha256(raw.encode()).hexdigest()
        print(f"🔍 [HASH] Generated: {hash_value[:16]}...")
        return hash_value

    def _reject(self, reason: str) -> dict:
        if self.send_rejection_reason:
            return {"status": "rejected", "reason": reason}
        return {"status": "rejected"}