"""Ingesta diaria de precios desde la API pública de Ñapa (solo lectura).

Consulta /api/search con una canasta de términos, conserva solo ofertas con
source == "live" (precios reales leídos de la tienda) y escribe una partición
append-only: data/raw/snapshot_date=YYYY-MM-DD/offers.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = os.environ.get("NAPA_API", "https://napa-api.onrender.com/api")
USER_AGENT = "napa-price-pipeline/0.1 (+https://github.com/JFredMC/napa-price-pipeline)"

# Canasta de búsqueda: productos de consumo frecuente en Colombia.
BASKET = [
    "arroz",
    "aceite",
    "azucar",
    "sal",
    "cafe",
    "chocolate",
    "panela",
    "harina",
    "pasta",
    "frijol",
    "lenteja",
    "atun",
    "huevos",
    "leche",
    "queso",
    "yogurt",
    "mantequilla",
    "pan",
    "galletas",
    "cereal",
    "gaseosa",
    "agua",
    "jugo",
    "cerveza",
    "detergente",
    "jabon",
    "suavizante",
    "papel higienico",
    "cloro",
    "lavaloza",
    "shampoo",
    "crema dental",
    "desodorante",
    "pañales",
    "toallitas",
    "concentrado perro",
]

COLUMNS = [
    "snapshot_date",
    "offer_id",
    "product_key",
    "store_id",
    "title",
    "brand",
    "category",
    "price",
    "list_price",
    "size_amount",
    "size_unit",
    "seller",
    "stock",
    "url",
    "observed_at",
    "query",
]


def fetch_json(path: str, params: dict[str, Any] | None = None, retries: int = 3) -> Any:
    url = f"{API}/{path}" + (f"?{urlencode(params)}" if params else "")
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(req, timeout=90) as resp:  # noqa: S310 - URL fija y pública
                return json.load(resp)
        except Exception as exc:  # pragma: no cover - red
            if attempt == retries - 1:
                raise
            print(f"reintento {attempt + 1} para {url}: {exc}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return None


def normalize(offer: dict[str, Any], snapshot_date: str, query: str) -> dict[str, Any] | None:
    """Convierte una Offer de Ñapa en una fila plana. Devuelve None si no es un precio real."""
    if offer.get("source") != "live":
        return None
    price = offer.get("price")
    if not isinstance(price, (int, float)) or price <= 0:
        return None
    size = offer.get("size") or {}
    return {
        "snapshot_date": snapshot_date,
        "offer_id": offer["id"],
        "product_key": offer.get("productKey", offer["id"]),
        "store_id": offer["storeId"],
        "title": (offer.get("title") or "").strip(),
        "brand": (offer.get("brand") or "").strip(),
        "category": offer.get("category", ""),
        "price": price,
        "list_price": offer.get("listPrice") or price,
        "size_amount": size.get("amount", ""),
        "size_unit": size.get("unit", ""),
        "seller": offer.get("seller", ""),
        "stock": offer.get("stock", ""),
        "url": offer.get("url", ""),
        "observed_at": offer.get("observedAt", ""),
        "query": query,
    }


def dedupe(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Una fila por oferta y día (la primera consulta que la encontró gana)."""
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        seen.setdefault(row["offer_id"], row)
    return sorted(seen.values(), key=lambda r: (r["store_id"], r["offer_id"]))


def write_partition(rows: list[dict[str, Any]], root: Path, snapshot_date: str) -> Path:
    part = root / f"snapshot_date={snapshot_date}"
    part.mkdir(parents=True, exist_ok=True)
    out = part / "offers.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--date", help="Fecha del snapshot (por defecto hoy en Bogotá)")
    ap.add_argument("--sleep", type=float, default=1.0, help="Pausa entre consultas (cortesía)")
    args = ap.parse_args(argv)

    bogota_now = datetime.now(UTC).astimezone(timezone(timedelta(hours=-5)))
    snapshot_date = args.date or bogota_now.date().isoformat()

    sources = fetch_json("sources")
    live = sorted(s["storeId"] for s in sources if s.get("mode") == "live")
    if not live:
        print("Ñapa no reporta tiendas con precios reales; no se escribe snapshot.", file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    for term in BASKET:
        data = fetch_json("search", {"q": term, "stores": ",".join(live), "limit": 48})
        for offer in data.get("offers", []):
            row = normalize(offer, snapshot_date, term)
            if row:
                rows.append(row)
        time.sleep(args.sleep)

    rows = dedupe(rows)
    if not rows:
        print("La API no devolvió ofertas reales; no se escribe snapshot.", file=sys.stderr)
        return 1
    out = write_partition(rows, Path(args.out), snapshot_date)
    meta = {
        "snapshot_date": snapshot_date,
        "live_stores": live,
        "offers": len(rows),
        "sources": sources,
        "ingested_at": datetime.now(UTC).isoformat(),
    }
    (out.parent / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"{len(rows)} ofertas reales de {live} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
