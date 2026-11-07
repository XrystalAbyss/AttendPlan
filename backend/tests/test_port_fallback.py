"""Tests for backend port discovery, collision handling, and loopback fallback."""
from __future__ import annotations

import socket

from launcher import find_available_port, is_port_in_use


def test_free_port_selection() -> None:
    """When preferred port is free, find_available_port returns preferred port."""
    # Find a guaranteed free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]

    # Outside the 'with' block, the port is free
    assert not is_port_in_use("127.0.0.1", free_port)
    selected = find_available_port("127.0.0.1", preferred_port=free_port, max_port=free_port + 5)
    assert selected == free_port


def test_port_collision_fallback() -> None:
    """When preferred port is occupied by another application, fallback finds next free port."""
    # Occupy a primary port
    sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock1.bind(("127.0.0.1", 0))
    port1 = sock1.getsockname()[1]
    sock1.listen(1)

    try:
        assert is_port_in_use("127.0.0.1", port1)
        # Search starting from port1 with a max_port range
        selected = find_available_port("127.0.0.1", preferred_port=port1, max_port=port1 + 10)
        assert selected != port1, "Must not return occupied port!"
        assert selected > port1
        assert not is_port_in_use("127.0.0.1", selected)
    finally:
        sock1.close()


def test_multiple_port_collision_fallback() -> None:
    """When multiple sequential ports are occupied, fallback skips all occupied ports."""
    # Occupy two consecutive ports if possible
    sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock1.bind(("127.0.0.1", 0))
    port1 = sock1.getsockname()[1]
    sock1.listen(1)

    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock2.bind(("127.0.0.1", port1 + 1))
        sock2.listen(1)
        two_bound = True
    except OSError:
        two_bound = False

    try:
        if two_bound:
            selected = find_available_port("127.0.0.1", preferred_port=port1, max_port=port1 + 10)
            assert selected not in (port1, port1 + 1)
            assert not is_port_in_use("127.0.0.1", selected)
    finally:
        sock1.close()
        sock2.close()

