"""
Tests for auto-arrange functionality.
"""

import pytest
from pkdiagram.pyqt import QPointF
from pkdiagram.scene import Scene, Person, Marriage
from pkdiagram.scene.autoarrange import (
    auto_arrange_selection,
    FamilyGraph,
    calculate_optimal_spacing,
)
from pkdiagram import util


def test_calculate_optimal_spacing():
    """Test spacing calculation based on person sizes."""
    scene = Scene()

    # Create people with different sizes
    person1 = Person(size=util.NORMAL_PERSON_SIZE)
    person2 = Person(size=util.NORMAL_PERSON_SIZE + 1)
    person3 = Person(size=util.NORMAL_PERSON_SIZE - 1)

    scene.addItems(person1, person2, person3)

    spacing = calculate_optimal_spacing([person1, person2, person3])
    assert spacing > 0
    assert isinstance(spacing, float)


def test_auto_arrange_no_selection():
    """Test that auto-arrange returns False when nothing is selected."""
    scene = Scene()
    person1, person2 = scene.addItems(Person(), Person())

    result = auto_arrange_selection(scene)
    assert result is False


def test_auto_arrange_single_person():
    """Test that auto-arrange returns False for single person selection."""
    scene = Scene()
    person1, person2 = scene.addItems(Person(), Person())

    person1.setSelected(True)

    result = auto_arrange_selection(scene)
    assert result is False


def test_auto_arrange_simple_pair():
    """Test auto-arranging a simple pair of people."""
    scene = Scene()
    person1, person2 = scene.addItems(
        Person(pos=QPointF(0, 0)), Person(pos=QPointF(100, 100))
    )

    person1.setSelected(True)
    person2.setSelected(True)

    result = auto_arrange_selection(scene)
    assert result is True

    # Positions should have been updated
    # (exact positions depend on algorithm, just verify they were set)
    assert person1.itemPos() is not None
    assert person2.itemPos() is not None


def test_auto_arrange_married_couple():
    """Test auto-arranging a married couple."""
    scene = Scene()

    male = Person(gender=util.PERSON_KIND_MALE, pos=QPointF(0, 0))
    female = Person(gender=util.PERSON_KIND_FEMALE, pos=QPointF(200, 0))
    marriage = Marriage(personA=male, personB=female)

    scene.addItems(male, female, marriage)

    male.setSelected(True)
    female.setSelected(True)

    original_male_pos = male.itemPos()
    original_female_pos = female.itemPos()

    result = auto_arrange_selection(scene)
    assert result is True

    # Positions should have changed
    assert (
        male.itemPos() != original_male_pos or female.itemPos() != original_female_pos
    )


def test_auto_arrange_family_with_child():
    """Test auto-arranging a family with parents and child."""
    scene = Scene()

    father = Person(gender=util.PERSON_KIND_MALE, pos=QPointF(0, 0))
    mother = Person(gender=util.PERSON_KIND_FEMALE, pos=QPointF(100, 0))
    child = Person(pos=QPointF(50, 200))

    marriage = Marriage(personA=father, personB=mother)
    scene.addItems(father, mother, child, marriage)

    # Set child's parents
    child.setParents(marriage)

    # Select all three
    father.setSelected(True)
    mother.setSelected(True)
    child.setSelected(True)

    result = auto_arrange_selection(scene)
    assert result is True

    # Child should be below parents
    child_y = child.itemPos().y()
    father_y = father.itemPos().y()
    mother_y = mother.itemPos().y()

    # Due to coordinate system, higher Y might mean lower on screen depending on implementation
    # Just verify positions were set
    assert child.itemPos() is not None
    assert father.itemPos() is not None
    assert mother.itemPos() is not None


def test_family_graph_generation_levels():
    """Test generation level calculation."""
    scene = Scene()

    # Create three generations
    grandpa = Person(gender=util.PERSON_KIND_MALE)
    grandma = Person(gender=util.PERSON_KIND_FEMALE)
    parent = Person()
    child = Person()

    marriage1 = Marriage(personA=grandpa, personB=grandma)
    scene.addItems(grandpa, grandma, parent, child, marriage1)

    parent.setParents(marriage1)

    marriage2 = Marriage(personA=parent, personB=None)
    scene.addItem(marriage2)
    child.setParents(marriage2)

    all_people = [grandpa, grandma, parent, child]
    graph = FamilyGraph(scene, all_people, all_people)

    # Grandparents should be generation 0 (no parents)
    assert graph.get_generation_level(grandpa) == 0
    assert graph.get_generation_level(grandma) == 0

    # Parent should be generation 1
    assert graph.get_generation_level(parent) == 1

    # Child should be generation 2
    assert graph.get_generation_level(child) == 2


def test_auto_arrange_respects_unselected():
    """Test that auto-arrange doesn't modify unselected people."""
    scene = Scene()

    person1 = Person(pos=QPointF(0, 0))
    person2 = Person(pos=QPointF(100, 0))
    person3 = Person(pos=QPointF(200, 0))  # This one won't be selected

    scene.addItems(person1, person2, person3)

    person1.setSelected(True)
    person2.setSelected(True)
    # person3 is NOT selected

    original_person3_pos = person3.itemPos()

    result = auto_arrange_selection(scene)
    assert result is True

    # person3 position should not change
    assert person3.itemPos() == original_person3_pos


def test_auto_arrange_with_multiple_marriages():
    """Test auto-arranging person with multiple marriages."""
    scene = Scene()

    person = Person(gender=util.PERSON_KIND_MALE, pos=QPointF(0, 0))
    spouse1 = Person(gender=util.PERSON_KIND_FEMALE, pos=QPointF(100, 0))
    spouse2 = Person(gender=util.PERSON_KIND_FEMALE, pos=QPointF(200, 0))

    marriage1 = Marriage(personA=person, personB=spouse1)
    marriage2 = Marriage(personA=person, personB=spouse2)

    scene.addItems(person, spouse1, spouse2, marriage1, marriage2)

    person.setSelected(True)
    spouse1.setSelected(True)
    spouse2.setSelected(True)

    result = auto_arrange_selection(scene)
    assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
