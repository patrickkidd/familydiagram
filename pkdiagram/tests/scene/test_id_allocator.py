"""
Tests for Scene's id allocator abstraction.

Plan: doc/plans/2026-05-01--mvp-merge-fix/README.md
"""

import pytest

from pkdiagram.scene import Scene, Person


pytestmark = [pytest.mark.component("Scene")]


def test_no_allocator_uses_local_lastItemId(scene):
    """Default Scene with no allocator increments lastItemId monotonically."""
    p1 = Person()
    scene.addItem(p1)
    p1_id = p1.id

    p2 = Person()
    scene.addItem(p2)

    assert p2.id > p1_id
    assert scene.lastItemId() == p2.id


def test_allocator_delegates_id_assignment(scene):
    """Bound allocator is the source of new ids (every nextId call delegates)."""
    counter = {"n": 99}
    issued = []

    def alloc():
        counter["n"] += 1
        issued.append(counter["n"])
        return counter["n"]

    scene.setIdAllocator(alloc)

    p1 = Person()
    scene.addItem(p1)
    assert p1.id in issued, "Person id must come from allocator"
    assert p1.id >= 100, "Allocator started from 100"


def test_allocator_advances_lastItemId(scene):
    """Allocator-assigned ids bump lastItemId so the counter stays consistent."""
    counter = {"n": 499}

    def alloc():
        counter["n"] += 1
        return counter["n"]

    scene.setIdAllocator(alloc)

    p1 = Person()
    scene.addItem(p1)
    assert scene.lastItemId() >= 500


def test_unbinding_allocator_restores_local_counter(scene):
    """Removing the allocator falls back to local lastItemId behavior."""
    counter = {"n": 999}

    def alloc():
        counter["n"] += 1
        return counter["n"]

    scene.setIdAllocator(alloc)
    p1 = Person()
    scene.addItem(p1)
    last_after_alloc = scene.lastItemId()

    scene.setIdAllocator(None)
    p2 = Person()
    scene.addItem(p2)

    assert p2.id > last_after_alloc, "Local counter resumes above allocator's max"


def test_pre_existing_id_preserved(scene):
    """addItem(item) with item.id already set keeps that id unchanged."""
    counter = {"n": 1000}

    def alloc():
        counter["n"] += 1
        return counter["n"]

    scene.setIdAllocator(alloc)

    p1 = Person()
    p1.id = 42  # pre-existing id (e.g., loaded from server data)
    scene.addItem(p1)

    assert p1.id == 42, "Pre-existing id must not be replaced by allocator"
    assert scene.lastItemId() >= 42  # at least bumped to 42
