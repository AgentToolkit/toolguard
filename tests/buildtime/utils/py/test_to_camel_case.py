from toolguard.buildtime.utils.py import to_py_class_name


def test_basic_snake_case():
    assert to_py_class_name("hello_world") == "HelloWorld"


def test_multiple_underscores():
    assert to_py_class_name("many_words_here") == "ManyWordsHere"


def test_hyphen_replaced_with_underscore():
    assert to_py_class_name("hello-world") == "Hello_World"


def test_special_characters_replaced():
    assert to_py_class_name("price$amount%") == "Price_Amount_"


def test_apostrophes_and_commas():
    assert to_py_class_name("john's,book") == "John_S_Book"


def test_percents():
    txt = "Apply 10% Discount for Gold Users When Scheduling Appointments"
    assert (
        to_py_class_name(txt)
        == "Apply10_DiscountForGoldUsersWhenSchedulingAppointments"
    )
