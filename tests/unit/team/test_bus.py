from agent_factory.team.bus import MessageBus


def test_message_bus_send_receive_and_process() -> None:
    bus = MessageBus()
    sent = bus.send(
        sender="researcher",
        receiver="writer",
        task_ref="handoff-1",
        payload="research notes",
        message_id="msg-1",
    )

    assert sent.status == "pending"
    received = bus.receive("writer")
    assert len(received) == 1
    assert received[0].message_id == "msg-1"
    assert received[0].status == "delivered"

    processed = bus.mark_processed("msg-1")
    assert processed.status == "processed"
    assert bus.get("msg-1") is not None
    assert bus.get("msg-1").status == "processed"
