from toolguard.buildtime.utils.py import to_py_func_name


def test_basic_spaces():
    assert to_py_func_name("Hello World") == "hello_world"


def test_hyphens_converted():
    assert to_py_func_name("hello-world-test") == "hello_world_test"


def test_mixed_special_characters():
    assert to_py_func_name("Price, Amount%") == "price__amount_"


def test_apostrophes_and_unicode_apostrophe():
    assert to_py_func_name("John’s book") == "john_s_book"


def test_dollar_sign_replacement():
    assert to_py_func_name("Total $ Cost") == "total___cost"


def test_percents():
    txt = "Apply 10% Discount for Gold Users When Scheduling Appointments"
    assert (
        to_py_func_name(txt)
        == "apply_10__discount_for_gold_users_when_scheduling_appointments"
    )
