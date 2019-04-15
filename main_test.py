from unittest import TestCase

import main


def availability_response():
    with open('reservation_test.txt') as file:
        return file.read()


def test_parse_for_time():
    time = main.parse_for_time(availability_response())
    TestCase().assertCountEqual(
        time, [
            '8:45 AM',
        ],
    )
