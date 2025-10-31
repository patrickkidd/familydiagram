"""
Auto-arrange algorithm for family diagram layout.

This module provides intelligent automatic arrangement of selected people in a family diagram,
respecting the positions of unselected people and maintaining proper family relationships.
"""

import logging
from typing import List, Set, Dict, Tuple, Optional
from collections import defaultdict

from pkdiagram.pyqt import QPointF
from pkdiagram import util

log = logging.getLogger(__name__)


class FamilyGraph:
    """Represents the family relationship graph for layout calculation."""

    def __init__(self, scene, selected_people, all_people):
        self.scene = scene
        self.selected_people = set(selected_people)
        self.all_people = set(all_people)
        self.unselected_people = self.all_people - self.selected_people

        # Build relationship maps
        self.marriages = {}  # person -> Marriage
        self.children_of = {}  # person -> ChildOf (parents)
        self.person_children = defaultdict(set)  # person -> set of children
        self.marriage_children = defaultdict(set)  # Marriage -> set of children

        self._build_relationships()

    def _build_relationships(self):
        """Build maps of all family relationships."""
        # Map marriages
        for marriage in self.scene.marriages():
            personA = marriage.personA()
            personB = marriage.personB()
            if personA:
                self.marriages[personA] = marriage
            if personB:
                self.marriages[personB] = marriage

        # Map parent-child relationships
        for person in self.all_people:
            if person.childOf:
                self.children_of[person] = person.childOf
                marriage = person.childOf.marriage()
                if marriage:
                    self.marriage_children[marriage].add(person)
                    personA = marriage.personA()
                    personB = marriage.personB()
                    if personA:
                        self.person_children[personA].add(person)
                    if personB:
                        self.person_children[personB].add(person)

    def get_generation_level(self, person, visited=None) -> int:
        """
        Calculate generation level for a person.
        Higher values = older generations (parents/grandparents).
        Returns 0 for people with no parents.
        """
        if visited is None:
            visited = set()
        if person in visited:
            return 0  # Circular reference, shouldn't happen
        visited.add(person)

        if person not in self.children_of:
            return 0  # Root generation

        # Get parents' generation levels
        childof = self.children_of[person]
        marriage = childof.marriage()
        if not marriage:
            return 0

        parent_levels = []
        personA = marriage.personA()
        personB = marriage.personB()

        if personA and personA in self.all_people:
            parent_levels.append(self.get_generation_level(personA, visited))
        if personB and personB in self.all_people:
            parent_levels.append(self.get_generation_level(personB, visited))

        if parent_levels:
            return max(parent_levels) + 1
        return 0


def calculate_optimal_spacing(people: List) -> float:
    """Calculate optimal horizontal spacing based on person sizes."""
    if not people:
        return 300.0

    max_size = max(person.size() for person in people)
    rect = util.personRectForSize(max_size)
    # Use 2x the person width as spacing for visual breathing room
    return rect.width() * 2.5


def auto_arrange_selection(scene) -> bool:
    """
    Auto-arrange selected people in the scene.

    This uses a hierarchical layout algorithm that:
    1. Analyzes family structure (marriages, parent-child relationships)
    2. Groups people by generation level
    3. Positions married couples together
    4. Arranges children below parents
    5. Respects positions of unselected people as anchors

    Args:
        scene: The Scene instance containing the diagram

    Returns:
        bool: True if arrangement was performed, False if nothing to arrange
    """
    selected_people = scene.selectedPeople()

    if not selected_people:
        log.info("No people selected for auto-arrange")
        return False

    if len(selected_people) == 1:
        log.info("Only one person selected, nothing to arrange")
        return False

    all_people = scene.people()
    graph = FamilyGraph(scene, selected_people, all_people)

    # Group selected people by generation level
    generations = defaultdict(list)
    for person in selected_people:
        level = graph.get_generation_level(person)
        generations[level].append(person)

    # Calculate center point of selection (or diagram)
    if graph.unselected_people:
        # Use unselected people as reference
        positions = [p.scenePos() for p in graph.unselected_people]
        center_x = sum(p.x() for p in positions) / len(positions)
        center_y = sum(p.y() for p in positions) / len(positions)
        reference_center = QPointF(center_x, center_y)
    else:
        # Use current selection center
        positions = [p.scenePos() for p in selected_people]
        center_x = sum(p.x() for p in positions) / len(positions)
        center_y = sum(p.y() for p in positions) / len(positions)
        reference_center = QPointF(center_x, center_y)

    # Calculate spacing
    spacing = calculate_optimal_spacing(selected_people)
    vertical_spacing = spacing * 1.5  # More space between generations

    # Track positioned people
    positioned = {}  # person -> QPointF

    # Sort generation levels (highest = oldest = top)
    sorted_generations = sorted(generations.keys(), reverse=True)

    # Position each generation
    for gen_index, gen_level in enumerate(sorted_generations):
        people_in_gen = generations[gen_level]

        # Group into married pairs and singles
        married_pairs = []
        singles = []
        processed = set()

        for person in people_in_gen:
            if person in processed:
                continue
            marriage = graph.marriages.get(person)
            if marriage:
                spouse = (
                    marriage.personA()
                    if marriage.personB() == person
                    else marriage.personB()
                )
                if spouse and spouse in selected_people and spouse in people_in_gen:
                    # Both spouses selected in same generation
                    married_pairs.append((person, spouse))
                    processed.add(person)
                    processed.add(spouse)
                else:
                    singles.append(person)
                    processed.add(person)
            else:
                singles.append(person)
                processed.add(person)

        # Calculate how many horizontal slots we need
        num_slots = len(married_pairs) + len(singles)

        # Calculate starting X position (centered)
        total_width = (num_slots - 1) * spacing
        start_x = reference_center.x() - (total_width / 2)

        # Calculate Y position for this generation
        base_y = reference_center.y() - (gen_index * vertical_spacing)

        # Position married pairs and singles
        current_x = start_x

        # Position married pairs first
        for personA, personB in married_pairs:
            # Determine which person goes left/right
            # Typically male on left, female on right
            if personA.gender() == util.PERSON_KIND_MALE:
                left_person, right_person = personA, personB
            else:
                left_person, right_person = personB, personA

            # Position with slight offset for marriage visual
            pair_offset = spacing * 0.3
            positioned[left_person] = QPointF(current_x - pair_offset, base_y)
            positioned[right_person] = QPointF(current_x + pair_offset, base_y)
            current_x += spacing

        # Position singles
        for person in singles:
            positioned[person] = QPointF(current_x, base_y)
            current_x += spacing

    # Adjust positions based on children constraints
    # If a selected person has unselected children, try to stay above them
    # If a selected person has selected children, make sure children are below
    adjustments_made = True
    iterations = 0
    max_iterations = 3

    while adjustments_made and iterations < max_iterations:
        adjustments_made = False
        iterations += 1

        for person in selected_people:
            if person not in positioned:
                continue

            children = graph.person_children.get(person, set())
            if not children:
                continue

            person_pos = positioned[person]

            # Check children positions
            for child in children:
                if child in selected_people and child in positioned:
                    child_pos = positioned[child]
                    # Child should be below parent
                    if child_pos.y() <= person_pos.y():
                        # Move child down
                        positioned[child] = QPointF(
                            child_pos.x(), person_pos.y() + vertical_spacing
                        )
                        adjustments_made = True

    # Apply positions with undo support
    with scene.macro("AI Arrange", undo=True):
        for person, pos in positioned.items():
            person.setItemPos(pos, undo=True)
            log.debug(f"Positioned {person} at {pos}")

    log.info(f"Auto-arranged {len(positioned)} people")
    return True
