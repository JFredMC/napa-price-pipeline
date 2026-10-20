"""Exporta los marts de DuckDB a JSON para el tablero estático (docs/data)."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb

QUERIES = {
    "index_by_store": """
        select store_id, cast(snapshot_date as varchar) as date,
               round(sum(price_index * offers) / sum(offers), 2) as price_index,
               sum(offers) as offers
        from mart_price_index group by all order by store_id, date""",
    "index_by_category": """
        select store_id, category, cast(snapshot_date as varchar) as date, price_index, offers,
               avg_discount_pct
        from mart_price_index order by category, store_id, date""",
    "category_snapshot": """
        select f.category, f.store_id, count(*) as offers,
               round(median(f.price)) as median_price, round(avg(f.discount_pct), 2) as avg_discount_pct,
               sum(case when f.discount_pct > 0 then 1 else 0 end) as discounted
        from fct_daily_price f
        where f.snapshot_date = (select max(snapshot_date) from fct_daily_price)
        group by all order by f.category, f.store_id""",
    "top_discounts": """
        select p.title, p.brand, f.store_id, f.category, f.price, f.list_price, f.discount_pct, p.url
        from fct_daily_price f join dim_product p using (offer_id)
        where f.snapshot_date = (select max(snapshot_date) from fct_daily_price)
          and f.discount_pct > 0
        order by f.discount_pct desc, f.price desc limit 25""",
    "price_changes": """
        select title, store_id, category, cast(prev_date as varchar) as prev_date,
               cast(change_date as varchar) as change_date, prev_price, new_price, change_pct
        from mart_price_changes order by change_date desc, abs(change_pct) desc limit 50""",
    "best_day": """
        select store_id, category, day_name, avg_vs_mean_pct, days_sampled, is_reliable
        from mart_best_day_to_buy where is_best_day order by store_id, category""",
}


def _default(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(type(o))


def export(db_path: str, out_dir: Path) -> dict:
    con = duckdb.connect(db_path, read_only=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {}
    for name, sql in QUERIES.items():
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        payload[name] = [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
    days = con.execute(
        "select cast(min(snapshot_date) as varchar), cast(max(snapshot_date) as varchar), "
        "count(distinct snapshot_date) from fct_daily_price"
    ).fetchone()
    payload["summary"] = {
        "first_date": days[0],
        "last_date": days[1],
        "days": days[2],
        "offers": con.execute("select count(*) from dim_product").fetchone()[0],
        "observations": con.execute("select count(*) from fct_daily_price").fetchone()[0],
        "stores": [
            r[0] for r in con.execute("select distinct store_id from dim_product order by 1").fetchall()
        ],
        "categories": con.execute("select count(distinct category) from dim_product").fetchone()[0],
        "price_changes": con.execute("select count(*) from mart_price_changes").fetchone()[0],
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "https://napa-api.onrender.com/api/search (solo ofertas source=live)",
    }
    (out_dir / "dashboard.json").write_text(
        json.dumps(payload, ensure_ascii=False, default=_default, indent=1)
    )
    return payload["summary"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="warehouse/napa.duckdb")
    ap.add_argument("--out", default="docs/data")
    a = ap.parse_args()
    print(export(a.db, Path(a.out)))
