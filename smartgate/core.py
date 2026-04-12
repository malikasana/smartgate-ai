import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Any
from .ai import AIValidator
from .storage import Storage
from .pipeline import Pipeline


class SmartGate:
    def __init__(
        self,
        # ── REQUIRED ────────────────────────────────────────
        ai_provider: str,
        ai_api_key: str,
        ai_instructions: str,
        database,
        index_fields: list,

        # ── OPTIONAL ────────────────────────────────────────
        rejection_threshold: int = 5,
        queue_limit: int = 100,
        max_data_size: int = 1024,
        send_rejection_reason: bool = True,
        reset_days: int = 30,
        storage_dir: str = ".",
        host: str = "0.0.0.0",
        port: int = 8000,
    ):
        print(f"\n{'='*50}")
        print(f"🚀 [SMARTGATE] Initializing...")
        print(f"{'='*50}")

        # ── Setup storage ────────────────────────────────────
        self.storage = Storage(
            storage_dir=storage_dir,
            reset_days=reset_days
        )

        # ── Setup AI ─────────────────────────────────────────
        self.ai = AIValidator(
            provider=ai_provider,
            api_key=ai_api_key,
            instructions=ai_instructions
        )

        # ── Setup pipeline ────────────────────────────────────
        self.pipeline = Pipeline(
            ai_validator=self.ai,
            storage=self.storage,
            database=database,
            index_fields=index_fields,
            rejection_threshold=rejection_threshold,
            queue_limit=queue_limit,
            max_data_size=max_data_size,
            send_rejection_reason=send_rejection_reason,
        )

        self.host = host
        self.port = port
        self.app = FastAPI()

        # ── Register routes ───────────────────────────────────
        self._register_routes()

        print(f"\n✅ [SMARTGATE] Ready!")
        print(f"{'='*50}\n")

    def _register_routes(self):

        pipeline = self.pipeline
        storage = self.storage

        # ── Submit endpoint ───────────────────────────────────
        @self.app.post("/submit")
        async def submit(request: Request, data: dict[str, Any]):
            ip = request.client.host
            return pipeline.process(ip, data)

        # ── Admin endpoints ───────────────────────────────────
        @self.app.get("/admin/bans")
        def get_bans():
            return {"bans": storage.get_all_bans()}

        @self.app.get("/admin/index")
        def get_index():
            return {"index": storage.get_index()}

        @self.app.get("/admin/hashes")
        def get_hashes():
            return {"hashes": storage.get_hashes()}

        @self.app.get("/admin/stats")
        def get_stats():
            bans = storage.get_all_bans()
            index = storage.get_index()
            hashes = storage.get_hashes()
            return {
                "total_bans": len(bans),
                "total_index_entries": len(index),
                "total_hashes": len(hashes),
                "queue_limit": self.pipeline.queue_limit,
                "rejection_threshold": self.pipeline.rejection_threshold,
            }

        @self.app.post("/admin/unblock/{ip}")
        def unblock_ip(ip: str):
            storage.unblock_ip(ip)
            return {"status": "unblocked", "ip": ip}

        @self.app.post("/admin/block/{ip}")
        def block_ip(ip: str):
            storage.block_ip(ip)
            return {"status": "blocked", "ip": ip}

        @self.app.post("/admin/clear-bans")
        def clear_bans():
            storage.clear_all_bans()
            return {"status": "cleared", "message": "All bans cleared"}

        @self.app.post("/admin/clear-index")
        def clear_index():
            storage.clear_index()
            return {"status": "cleared", "message": "Index cleared"}

    # ── Admin commands (callable from code) ───────────────────

    def print_blocked_ips(self):
        bans = self.storage.get_all_bans()
        print(f"\n🚫 BLOCKED IPS ({len(bans)}):")
        for ip, data in bans.items():
            print(f"   {ip} → count: {data['count']}, last: {data['last_rejected']}")

    def print_index(self):
        index = self.storage.get_index()
        print(f"\n📋 INDEX ({len(index)} entries):")
        for entry in index:
            print(f"   {entry}")

    def print_hashes(self):
        hashes = self.storage.get_hashes()
        print(f"\n🔍 HASHES ({len(hashes)} entries):")
        for h in hashes:
            print(f"   {h[:16]}...")

    def print_stats(self):
        self.storage.print_stats()

    def unblock_ip(self, ip: str):
        self.storage.unblock_ip(ip)

    def block_ip(self, ip: str):
        self.storage.block_ip(ip)

    def clear_all_bans(self):
        self.storage.clear_all_bans()

    def clear_index(self):
        self.storage.clear_index()

    # ── Start server ──────────────────────────────────────────

    def start(self):
        print(f"🚀 [SMARTGATE] Starting server on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port)