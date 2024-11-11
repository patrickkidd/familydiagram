from pkdiagram import ItemDetails


def test_no_mainText_and_extraLines_still_shown():
    item = ItemDetails(None)
    item.setText("")
    assert item.isEmpty() == True

    item.setText("", ["something: 1"])
    assert item.isEmpty() == False


def test_mainText_no_extraLines_still_shown():
    item = ItemDetails(None)
    item.setText("")
    assert item.isEmpty() == True

    item.setText("spomething")
    assert item.isEmpty() == False
