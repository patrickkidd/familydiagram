from pkdiagram import version


def test_greaterThan():

    assert version.greaterThan("1.0.0b4", "1.0.0b5") == False
    assert version.greaterThan("1.0.0b5", "1.0.0b4")
    assert version.greaterThan("1.0.0b4", "1.0.0b4") == False

    assert version.greaterThan("1.0.1b4", "1.0.0b5")
    assert version.greaterThan("1.0.1", "1.0.0b5")
    assert version.greaterThan("1.1.9", "1.2.3b4") == False


def test_greaterThanOrEqual():

    assert version.greaterThanOrEqual("1.0.0b4", "1.0.0b5") == False
    assert version.greaterThanOrEqual("1.0.0b5", "1.0.0b4")
    assert version.greaterThanOrEqual("1.0.0b4", "1.0.0b4")

    assert version.greaterThanOrEqual("1.0.1b4", "1.0.0b5")
    assert version.greaterThanOrEqual("1.0.1", "1.0.0b5")
    assert version.greaterThanOrEqual("1.1.9", "1.2.3b4") == False

    assert version.greaterThanOrEqual("1.2.6", "1.2.6")


def test_lessThanOrEqual():
    assert version.lessThanOrEqual("1.2.6", "1.2.6") == True
    assert version.lessThanOrEqual("1.2.5", "1.2.6") == True
    assert version.lessThanOrEqual("1.2.7", "1.2.6") == False
