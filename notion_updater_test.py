from collections.abc import Mapping
import datetime
from re import I
from typing import Any, Tuple
import unittest
from unittest import mock

from parameterized import param
from parameterized import parameterized

import notion_updater


def _param(**kwargs: Any) -> Tuple[Any, ...]:
  return tuple(dict(**kwargs).values())


class NotionTodoUpdaterTest(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    # Use enterContext to automatically clean up mocks after each test
    self._mock_client = self.enterContext(
      mock.patch("notion_client.Client", autospec=True)
    )
    self._updater = notion_updater.NotionTodoUpdater(
      notion_token='fake_token',
      database_id='fake_db_id',
    )

  def test_extract_frequency_returns_correct_name(self):
    test_page = {
      'properties': {
        'recurring frequency': {
          'select': {
            'name': 'week'
          }
        }
      }
    }
    frequency = self._updater.extract_frequency(test_page)
    self.assertEqual(frequency, notion_updater.Frequency.WEEK)

  def test_extract_frequency_no_key_returns_undefined(self):
    test_page = {'properties': {}, 'id': 'fake_id'}
    self.assertEqual(
      self._updater.extract_frequency(test_page),
      notion_updater.Frequency.UNDEFINED
    )

  @parameterized.expand([
    _param(
      test_case_name='due_within_day_freq_day_returns_true',
      due_date=datetime.datetime(2025, 6, 11, 1),
      frequency=notion_updater.Frequency.DAY,
      expected_output=True
    ),
    _param(
      test_case_name='due_exceeds_day_freq_day_returns_false',
      due_date=datetime.datetime(2025, 6, 10, 23),
      frequency=notion_updater.Frequency.DAY,
      expected_output=False
    ),
    _param(
      test_case_name='due_within_month_freq_month_returns_true',
      due_date=datetime.datetime(2025, 7, 1, 1),
      frequency=notion_updater.Frequency.MONTH,
      expected_output=True,
    ),
    _param(
      test_case_name='due_exceeds_month_freq_month_returns_false',
      due_date=datetime.datetime(2025, 7, 20, 23),
      frequency=notion_updater.Frequency.MONTH,
      expected_output=False,
    ),
  ])
  def test_should_create_next_occurrence(
    self,
    _,
    due_date,
    frequency,
    expected_output,
  ):
    with mock.patch.object(
        notion_updater,
        'datetime',
        autospec=True,
    ) as mock_datetime:
      mock_datetime.now.return_value = datetime.datetime(
        year=2025,
        month=6,
        day=11,
      )
      self.assertEqual(
        self._updater.should_create_next_occurrence(
          due_date=due_date,
          frequency=frequency,
          already_scheduled=False,
        ),
        expected_output,
      )


if __name__ == '__main__':
  unittest.main()
