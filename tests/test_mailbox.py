"""Tests for SQLite-backed mailbox."""

import threading

from agentkit.mailbox import Mailbox, TaskStatus


def test_enqueue_and_dequeue(tmp_path):
    mb = Mailbox(tmp_path / "data" / "test.db")
    task_id = mb.enqueue("do something", source="test")
    assert task_id == 1
    task = mb.dequeue()
    assert task is not None
    assert task["content"] == "do something"
    assert task["source"] == "test"
    assert task["status"] == TaskStatus.PROCESSING


def test_dequeue_empty(tmp_path):
    mb = Mailbox(tmp_path / "data" / "test.db")
    assert mb.dequeue() is None


def test_complete_task(tmp_path):
    mb = Mailbox(tmp_path / "data" / "test.db")
    task_id = mb.enqueue("task", source="test")
    mb.dequeue()
    mb.complete(task_id, result="done")
    history = mb.history()
    assert history[0]["status"] == TaskStatus.DONE
    assert history[0]["result"] == "done"


def test_fail_task(tmp_path):
    mb = Mailbox(tmp_path / "data" / "test.db")
    task_id = mb.enqueue("task", source="test")
    mb.dequeue()
    mb.fail(task_id, error="something broke")
    history = mb.history()
    assert history[0]["status"] == TaskStatus.FAILED
    assert history[0]["result"] == "something broke"


def test_fifo_order(tmp_path):
    mb = Mailbox(tmp_path / "data" / "test.db")
    mb.enqueue("first", source="test")
    mb.enqueue("second", source="test")
    mb.enqueue("third", source="test")
    assert mb.dequeue()["content"] == "first"
    assert mb.dequeue()["content"] == "second"
    assert mb.dequeue()["content"] == "third"
    assert mb.dequeue() is None


def test_concurrent_dequeue_no_duplicates(tmp_path):
    """Two threads dequeue simultaneously — each task grabbed at most once."""
    mb = Mailbox(tmp_path / "data" / "test.db")
    for i in range(10):
        mb.enqueue(f"task-{i}", source="test")

    results: list[dict | None] = []
    lock = threading.Lock()

    def worker():
        while True:
            task = mb.dequeue()
            if task is None:
                break
            with lock:
                results.append(task)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Every task dequeued exactly once
    contents = sorted(t["content"] for t in results)
    assert contents == [f"task-{i}" for i in range(10)]
