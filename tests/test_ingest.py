from ingest.napa_ingest import COLUMNS, dedupe, normalize, write_partition

LIVE = {
    "id": "jumbo-1",
    "productKey": "jumbo-1",
    "storeId": "jumbo",
    "title": " Arroz ",
    "brand": "ROA",
    "category": "despensa",
    "price": 4890,
    "listPrice": 5200,
    "size": {"amount": 1000, "unit": "g"},
    "source": "live",
    "observedAt": "2026-10-20T14:47:56Z",
}


def test_normalize_keeps_live_offers():
    row = normalize(LIVE, "2026-10-20", "arroz")
    assert row["title"] == "Arroz" and row["price"] == 4890 and row["size_unit"] == "g"
    assert set(row) == set(COLUMNS)


def test_normalize_drops_simulated_and_bad_prices():
    assert normalize({**LIVE, "source": "simulated"}, "2026-10-20", "x") is None
    assert normalize({**LIVE, "price": 0}, "2026-10-20", "x") is None


def test_list_price_defaults_to_price():
    row = normalize({**LIVE, "listPrice": None}, "2026-10-20", "x")
    assert row["list_price"] == 4890


def test_dedupe_one_row_per_offer():
    a = normalize(LIVE, "d", "arroz")
    b = normalize(LIVE, "d", "pan")
    assert [r["query"] for r in dedupe([a, b])] == ["arroz"]


def test_write_partition(tmp_path):
    out = write_partition([normalize(LIVE, "2026-10-20", "arroz")], tmp_path, "2026-10-20")
    assert out == tmp_path / "snapshot_date=2026-10-20" / "offers.csv"
    assert out.read_text().splitlines()[0].startswith("snapshot_date,offer_id")
