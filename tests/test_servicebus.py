from azure.servicebus import ServiceBusClient, ServiceBusMessage

from conftest import SERVICEBUS_CONN, require_port


def test_servicebus_queue_roundtrip():
    require_port(5672, "Service Bus")
    with ServiceBusClient.from_connection_string(SERVICEBUS_CONN) as client:
        with client.get_queue_sender("app-work-queue") as sender:
            sender.send_messages(ServiceBusMessage("locadev-smoke"))
        with client.get_queue_receiver("app-work-queue", max_wait_time=10) as receiver:
            msgs = receiver.receive_messages(max_message_count=1, max_wait_time=10)
            assert msgs, "expected a message on app-work-queue"
            body = str(msgs[0])
            assert "locadev-smoke" in body or msgs[0].body is not None
            receiver.complete_message(msgs[0])
