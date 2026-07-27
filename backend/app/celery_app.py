from celery import Celery
from app.config import settings

celery_app = Celery(
    "crypto_intel",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "technical-lane-btc": {
            "task": "app.tasks.run_technical_lane",
            "schedule": 60.0,
            "args": ("BTCUSDT",),
        },
        "technical-lane-eth": {
            "task": "app.tasks.run_technical_lane",
            "schedule": 60.0,
            "args": ("ETHUSDT",),
        },
        "technical-lane-sol": {
            "task": "app.tasks.run_technical_lane",
            "schedule": 60.0,
            "args": ("SOLUSDT",),
        },
        "flow-lane-btc": {
            "task": "app.tasks.run_flow_lane",
            "schedule": 120.0,
            "args": ("BTCUSDT",),
        },
        "flow-lane-eth": {
            "task": "app.tasks.run_flow_lane",
            "schedule": 120.0,
            "args": ("ETHUSDT",),
        },
        "flow-lane-sol": {
            "task": "app.tasks.run_flow_lane",
            "schedule": 120.0,
            "args": ("SOLUSDT",),
        },
        "narrative-lane": {
            "task": "app.tasks.run_narrative_lane",
            "schedule": 300.0,
        },
        "macro-lane": {
            "task": "app.tasks.run_macro_lane",
            "schedule": 600.0,
        },
        "synthesizer-btc": {
            "task": "app.tasks.run_synthesizer",
            "schedule": 120.0,
            "args": ("BTCUSDT",),
        },
        "synthesizer-eth": {
            "task": "app.tasks.run_synthesizer",
            "schedule": 120.0,
            "args": ("ETHUSDT",),
        },
        "synthesizer-sol": {
            "task": "app.tasks.run_synthesizer",
            "schedule": 120.0,
            "args": ("SOLUSDT",),
        },
        "ingest-price-btc": {
            "task": "app.tasks.ingest_price_data",
            "schedule": 10.0,
            "args": ("BTCUSDT",),
        },
        "ingest-price-eth": {
            "task": "app.tasks.ingest_price_data",
            "schedule": 10.0,
            "args": ("ETHUSDT",),
        },
        "ingest-price-sol": {
            "task": "app.tasks.ingest_price_data",
            "schedule": 10.0,
            "args": ("SOLUSDT",),
        },
    },
)
