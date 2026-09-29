"""Supabase-backed data access. One client per Streamlit user session."""
from __future__ import annotations

import os
from uuid import uuid4

from supabase import Client, create_client

BUCKET = "brand-assets"
TABLES = ("brand_profiles", "brand_colors", "brand_fonts", "brand_assets", "design_templates", "contents", "slides", "ideas")
DEFAULT_URL = "https://konervrdmmvbxadkgogv.supabase.co"
# Publishable keys are designed for public clients. Authorization lives in RLS.
DEFAULT_PUBLISHABLE_KEY = "sb_publishable_xm2okRBMCEfP_PCNiiezaw_HMSk2_Nh"


def config() -> tuple[str, str]:
    import streamlit as st
    try:
        url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", DEFAULT_URL))
        key = st.secrets.get("SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_PUBLISHABLE_KEY", DEFAULT_PUBLISHABLE_KEY))
    except Exception:
        url = os.getenv("SUPABASE_URL", DEFAULT_URL)
        key = os.getenv("SUPABASE_PUBLISHABLE_KEY", DEFAULT_PUBLISHABLE_KEY)
    return url, key


def client() -> Client:
    url, key = config()
    if not url or not key:
        raise RuntimeError("Renseignez SUPABASE_URL et SUPABASE_PUBLISHABLE_KEY dans les secrets de l'application.")
    return create_client(url, key)


class Store:
    def __init__(self, db: Client, user_id: str):
        self.db, self.user_id = db, user_id

    def list(self, table: str, order: str = "created_at", descending: bool = True) -> list[dict]:
        assert table in TABLES
        return self.db.table(table).select("*").eq("owner_id", self.user_id).order(order, desc=descending).execute().data or []

    def add(self, table: str, values: dict) -> dict:
        assert table in TABLES
        return self.db.table(table).insert({**values, "owner_id": self.user_id}).execute().data[0]

    def update(self, table: str, record_id: str, values: dict) -> None:
        assert table in TABLES
        self.db.table(table).update(values).eq("id", record_id).eq("owner_id", self.user_id).execute()

    def delete(self, table: str, record_id: str) -> None:
        assert table in TABLES
        self.db.table(table).delete().eq("id", record_id).eq("owner_id", self.user_id).execute()

    def upload(self, name: str, kind: str, mime: str, data: bytes) -> dict:
        if len(data) > 20 * 1024 * 1024:
            raise ValueError("Taille maximale : 20 Mo.")
        extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
                     "image/svg+xml": ".svg", "application/pdf": ".pdf", "text/plain": ".txt",
                     "text/markdown": ".md", "text/html": ".html"}.get(mime)
        if not extension:
            raise ValueError("Type de fichier non pris en charge.")
        path = f"{self.user_id}/{uuid4().hex}{extension}"
        self.db.storage.from_(BUCKET).upload(path, data, {"content-type": mime})
        try:
            return self.add("brand_assets", {"name": name[:200], "kind": kind, "mime": mime, "storage_path": path})
        except Exception:
            self.db.storage.from_(BUCKET).remove([path])
            raise

    def download(self, asset: dict) -> bytes:
        if asset["owner_id"] != self.user_id or not asset["storage_path"].startswith(self.user_id + "/"):
            raise ValueError("Fichier inaccessible.")
        return self.db.storage.from_(BUCKET).download(asset["storage_path"])

    def remove_asset(self, asset: dict) -> None:
        self.db.storage.from_(BUCKET).remove([asset["storage_path"]])
        self.delete("brand_assets", asset["id"])


def seed(store: Store) -> None:
    """Idempotent starting point from HYM-CHG-001; only run for an empty account."""
    if store.list("brand_profiles", "created_at"):
        return
    if not store.list("brand_colors", "sort_order", False):
        palettes = {
            "Vert": [("V-50", "#EAF7F1"), ("V-100", "#A8DECE"), ("V-300", "#4DC49A"),
                     ("V-500", "#1A9E68"), ("V-700", "#0F6E46"), ("V-900", "#073D27")],
            "Bleu": [("B-50", "#E6F2FC"), ("B-100", "#AACEF2"), ("B-400", "#2E78D5"),
                     ("B-600", "#1A52A0"), ("B-800", "#0F2D52"), ("B-950", "#071629")],
            "Orange": [("O-50", "#FFF0EB"), ("O-100", "#FFD0BC"), ("O-300", "#FF8C65"),
                       ("O-500", "#FF5C28"), ("O-700", "#CC3B0F"), ("O-900", "#7A2008")],
        }
        for i, (group, swatches) in enumerate(palettes.items()):
            for j, (token, hex_value) in enumerate(swatches):
                store.add("brand_colors", {"name": group, "token": token, "hex": hex_value, "sort_order": i * 10 + j})
        store.add("brand_colors", {"name": "Neutre", "token": "Blanc", "hex": "#FFFFFF", "sort_order": 99})
    if not store.list("brand_fonts", "family", False):
        for weight in (400, 600, 700):
            store.add("brand_fonts", {"family": "Poppins", "weight": weight})
    if not store.list("design_templates", "updated_at"):
        from rendering import DEFAULT_LAYERS
        store.add("design_templates", {"name": "Publication carrée Hympyr", "format": "Instagram",
                                       "width": 1080, "height": 1080, "background_token": "V-50", "layers": DEFAULT_LAYERS})
    store.add("brand_profiles", {
        "name": "Hympyr Energies", "descriptor": "Négoce de carburant et vente de granulés de bois",
        "territory": "Occitanie",
        "facts": ["Activité documentée : négoce de carburant et vente de granulés de bois.",
                  "La marque revendique un ancrage territorial en Occitanie."],
        "to_validate": ["Mission, vision et valeurs", "Promesse commerciale", "Audiences et preuves commerciales",
                        "Chiffres clés", "Fichiers vectoriels officiels du logo"],
    })


def import_legacy(store: Store, payload: dict) -> tuple[int, int]:
    """Move a V1 JSON export into the new content and idea tables once."""
    if store.list("contents", "updated_at") or store.list("ideas", "created_at"):
        raise ValueError("L'import V1 nécessite un espace sans contenus ni idées pour éviter les doublons.")
    contents, ideas = payload.get("contents"), payload.get("ideas")
    if not isinstance(contents, list) or not isinstance(ideas, list):
        raise ValueError("Ce fichier n'est pas un export JSON de la V1.")
    for item in contents:
        if not isinstance(item, dict) or not item.get("title"):
            raise ValueError("Contenu V1 invalide.")
    for item in ideas:
        if not isinstance(item, dict) or not item.get("title"):
            raise ValueError("Idée V1 invalide.")
    for item in contents:
        body = str(item.get("body") or "")
        publish_date = item.get("publish_date") or None
        new = store.add("contents", {"title": str(item["title"])[:240], "channel": str(item.get("content_type") or "Autre"),
                                      "body": body, "sources": str(item.get("sources") or ""),
                                      "status": str(item.get("status") or "Brouillon"),
                                      "publish_date": publish_date})
        store.add("slides", {"content_id": new["id"], "position": 1,
                             "fields": {"title": str(item["title"]), "body": body[:2000]}})
    for item in ideas:
        store.add("ideas", {"title": str(item["title"])[:240], "channel": str(item.get("channel") or "Autre"),
                            "priority": str(item.get("priority") or "Normale"),
                            "status": str(item.get("status") or "À explorer"), "notes": str(item.get("notes") or "")})
    return len(contents), len(ideas)
