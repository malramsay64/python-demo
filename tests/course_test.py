from python_demo import course


def test_decode():
    file = "tests/activity.fit"
    points = course.decode_fit(file)

    assert isinstance(points, list)
