from flaskerize import register_custom_function, registered_funcs


def test_register_custom_function():
    def f1():
        return 1

    @register_custom_function
    def f2():
        return 42

    assert len(registered_funcs) == 1
    assert registered_funcs[0]() == f2()
    assert registered_funcs[0]() != f1()
