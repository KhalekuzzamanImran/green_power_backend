from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Tuple

from bson import ObjectId


PERIODS = {
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
    "yearly": timedelta(days=365),
}


def parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def get_time_range(period: str, start: str | None, end: str | None) -> Tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)

    if end:
        end_dt = parse_datetime(end)
    else:
        end_dt = now

    if start:
        start_dt = parse_datetime(start)
    elif period == "till-date":
        start_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
    else:
        delta = PERIODS.get(period, PERIODS["daily"])
        start_dt = end_dt - delta

    return start_dt, end_dt


def truncate_datetime(value: datetime, bucket: str) -> datetime:
    if bucket == "hourly":
        return value.replace(minute=0, second=0, microsecond=0)
    if bucket == "daily":
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
    return value


def aggregate_docs(
    docs: Iterable[Dict[str, Any]],
    bucket: str,
    timestamp_field: str,
    timestamp_is_epoch_ms: bool,
    exclude_keys: set[str],
) -> list[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}

    for doc in docs:
        ts = doc.get(timestamp_field)
        if timestamp_is_epoch_ms and isinstance(ts, (int, float)):
            ts_dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        elif isinstance(ts, datetime):
            ts_dt = ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        else:
            continue

        bucket_dt = truncate_datetime(ts_dt, bucket)
        bucket_key = bucket_dt.isoformat()
        entry = buckets.setdefault(
            bucket_key,
            {
                "bucket": bucket_dt.isoformat(),
                "count": 0,
                "_sums": {},
                "_list_sums": {},
                "_list_counts": {},
            },
        )
        entry["count"] += 1

        for key, value in doc.items():
            if key in exclude_keys:
                continue
            if isinstance(value, (int, float)):
                entry["_sums"][key] = entry["_sums"].get(key, 0.0) + float(value)
            elif isinstance(value, list) and value and all(isinstance(i, (int, float)) for i in value):
                sums = entry["_list_sums"].setdefault(key, [0.0] * len(value))
                counts = entry["_list_counts"].setdefault(key, [0] * len(value))
                if len(value) > len(sums):
                    sums.extend([0.0] * (len(value) - len(sums)))
                    counts.extend([0] * (len(value) - len(counts)))
                for idx, item in enumerate(value):
                    sums[idx] += float(item)
                    counts[idx] += 1

    results: list[Dict[str, Any]] = []
    for entry in buckets.values():
        averages: Dict[str, Any] = {}
        count = max(entry["count"], 1)
        for key, total in entry["_sums"].items():
            averages[key] = total / count
        for key, sums in entry["_list_sums"].items():
            counts = entry["_list_counts"].get(key, [])
            averages[key] = [
                (sums[idx] / counts[idx]) if idx < len(counts) and counts[idx] else None
                for idx in range(len(sums))
            ]
        results.append({"bucket": entry["bucket"], "count": entry["count"], "averages": averages})

    results.sort(key=lambda item: item["bucket"], reverse=True)
    return results


def serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    return value


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {k: serialize_value(v) for k, v in doc.items()}


def serialize_docs(docs: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [serialize_doc(doc) for doc in docs]
