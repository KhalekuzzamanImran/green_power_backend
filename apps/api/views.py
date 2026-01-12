from datetime import datetime, timezone
from typing import Any, Dict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema

from config.mongodb import MongoDBClient
from .utils import aggregate_docs, get_time_range, serialize_docs


DEFAULT_LIMIT = 500
MAX_LIMIT = 5000
AGGREGATE_DEFAULT_LIMIT = 20000


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class BaseMongoView(APIView):
    collection_name = ""
    timestamp_field = "timestamp"
    timestamp_is_epoch_ms = False
    exclude_keys = {"_id", "timestamp", "time", "isend", "device_id", "timestamp_iso"}

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="period",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Time window to fetch (hourly, daily, weekly, monthly, yearly, till-date).",
            ),
            OpenApiParameter(
                name="start",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="ISO 8601 start datetime (overrides period).",
            ),
            OpenApiParameter(
                name="end",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="ISO 8601 end datetime (defaults to now).",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Max documents returned (default 500, max 5000).",
            ),
            OpenApiParameter(
                name="offset",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Skip N documents (pagination offset).",
            ),
            OpenApiParameter(
                name="aggregate",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Aggregation bucket (hourly or daily) for averages.",
            ),
            OpenApiParameter(
                name="aggregate_limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Max documents scanned for aggregation (default 20000).",
            ),
        ],
    )
    def get(self, request):
        if not self.collection_name:
            return Response({"detail": "Collection not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        period = request.query_params.get("period", "daily").lower()
        start = request.query_params.get("start")
        end = request.query_params.get("end")

        limit = _parse_int(request.query_params.get("limit"), DEFAULT_LIMIT)
        limit = max(min(limit, MAX_LIMIT), 1)
        offset = max(_parse_int(request.query_params.get("offset"), 0), 0)
        aggregate = request.query_params.get("aggregate")
        aggregate = aggregate.lower() if aggregate else None

        try:
            start_dt, end_dt = get_time_range(period, start, end)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if start_dt > end_dt:
            return Response({"detail": "start must be before end."}, status=status.HTTP_400_BAD_REQUEST)

        if self.timestamp_is_epoch_ms:
            start_value = int(start_dt.timestamp() * 1000)
            end_value = int(end_dt.timestamp() * 1000)
        else:
            start_value = start_dt
            end_value = end_dt

        db = MongoDBClient.require_db()
        collection = db[self.collection_name]

        query = {
            self.timestamp_field: {
                "$gte": start_value,
                "$lte": end_value,
            }
        }

        if aggregate:
            if aggregate not in {"hourly", "daily"}:
                return Response(
                    {"detail": "aggregate must be hourly or daily."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            aggregate_limit = _parse_int(request.query_params.get("aggregate_limit"), AGGREGATE_DEFAULT_LIMIT)
            aggregate_limit = max(min(aggregate_limit, AGGREGATE_DEFAULT_LIMIT), 1)
            cursor = collection.find(query).sort(self.timestamp_field, -1).limit(aggregate_limit)
            results = aggregate_docs(
                cursor,
                aggregate,
                self.timestamp_field,
                self.timestamp_is_epoch_ms,
                self.exclude_keys,
            )
            payload: Dict[str, Any] = {
                "period": period,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "aggregate": aggregate,
                "aggregate_limit": aggregate_limit,
                "count": len(results),
                "results": results,
            }
            return Response(payload)

        cursor = collection.find(query).sort(self.timestamp_field, -1).skip(offset).limit(limit)
        docs = list(cursor)

        if self.timestamp_is_epoch_ms:
            for doc in docs:
                ts = doc.get(self.timestamp_field)
                if isinstance(ts, int):
                    doc["timestamp_iso"] = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()

        payload: Dict[str, Any] = {
            "period": period,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "count": len(docs),
            "results": serialize_docs(docs),
        }
        return Response(payload)


@extend_schema(
    tags=["Environment"],
    summary="Environment data",
    description="Fetch raw or aggregated environment data.",
)
class EnvironmentDataView(BaseMongoView):
    collection_name = "environment_data"
    timestamp_field = "timestamp"


@extend_schema(
    tags=["Generator"],
    summary="Generator data",
    description="Fetch raw or aggregated generator data.",
)
class GeneratorDataView(BaseMongoView):
    collection_name = "generator_data"
    timestamp_field = "timestamp"
    timestamp_is_epoch_ms = True


@extend_schema(
    tags=["Grid"],
    summary="Grid realtime data",
    description="Fetch raw or aggregated grid realtime data.",
)
class GridRealtimeDataView(BaseMongoView):
    collection_name = "grid_rt_data"
    timestamp_field = "timestamp"


@extend_schema(
    tags=["Grid"],
    summary="Grid energy data",
    description="Fetch raw or aggregated grid energy (ENY NOW) data.",
)
class GridEnergyDataView(BaseMongoView):
    collection_name = "grid_eny_now"
    timestamp_field = "timestamp"


@extend_schema(
    tags=["Solar"],
    summary="Solar data",
    description="Fetch raw or aggregated solar data.",
)
class SolarDataView(BaseMongoView):
    collection_name = "solar_data"
    timestamp_field = "timestamp"
