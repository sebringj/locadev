#!/usr/bin/env python3
"""Service Bus publish/consume on app-events, Topaz-gated."""

from __future__ import annotations

import sys

from azure.servicebus import ServiceBusClient, ServiceBusMessage

import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topaz_client import require

CONN = (
    "Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;"
    "SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;"
)


def publish(user: str, body: str) -> None:
    require(user, "publish")
    with ServiceBusClient.from_connection_string(CONN) as client:
        with client.get_topic_sender("app-events") as sender:
            sender.send_messages(ServiceBusMessage(body))


def consume(user: str) -> str | None:
    require(user, "consume")
    with ServiceBusClient.from_connection_string(CONN) as client:
        with client.get_subscription_receiver(
            "app-events", "app-events-sub", max_wait_time=10
        ) as receiver:
            msgs = receiver.receive_messages(max_message_count=1, max_wait_time=10)
            if not msgs:
                return None
            receiver.complete_message(msgs[0])
            return str(msgs[0])


def main() -> int:
    publish("alice@example.com", "event-1")
    _ = consume("bob@example.com")
    try:
        publish("bob@example.com", "nope")
        print("FAIL: bob publish should be denied")
        return 1
    except PermissionError:
        print("OK: alice publish, bob consume, bob publish denied")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
