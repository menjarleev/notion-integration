"""Notion Todo List Updater with recurring task support."""

from __future__ import annotations

from datetime import datetime
import enum
from typing import Any, Callable

from absl import logging
from dateutil.relativedelta import relativedelta
from notion_client import Client

import field_keys

# Properties of todo list
# keep-sorted start
RECURRING_FREQUENCY = 'recurring frequency'
DUE_DATE = 'Due Date'
RECURRENCE_SCHEDULED = '_recurrence_scheduled'
# keep-sorted end


def _maybe_update_old_page_status(page: dict[str, Any], notion_client: Client):
  """Updates the original page if it has the recurrence scheduled property."""
  if RECURRENCE_SCHEDULED in page[field_keys.PROPERTIES]:
    notion_client.pages.update(
      page_id=page[field_keys.ID],
      properties={RECURRENCE_SCHEDULED: {
        field_keys.CHECKBOX: True
      }},
    )


class Frequency(enum.Enum):
  """Enum for task frequencies."""

  UNDEFINED = "undefined"
  DAY = "day"
  MONTH = "month"
  WEEK = "week"
  YEAR = "year"

  @property
  def next_occurrence(self) -> Callable[[datetime], datetime]:
    """Get the function to calculate next occurrence for this frequency."""
    return {
      Frequency.DAY: lambda dt: dt + relativedelta(days=1),
      Frequency.MONTH: lambda dt: dt + relativedelta(months=1),
      Frequency.WEEK: lambda dt: dt + relativedelta(weeks=1),
      Frequency.YEAR: lambda dt: dt + relativedelta(years=1),
    }[self]

  @classmethod
  def from_string(cls, value: str) -> Frequency:
    """Convert string to Frequency enum value.

    Args:
        value: The string value to convert.

    Returns:
        Frequency enum value or None if invalid.
    """
    try:
      return cls(value.lower())
    except ValueError:
      raise ValueError(f"Invalid frequency: {value}")


class NotionTodoUpdater:
  """Updates the todo list in Notion.

  Checks for any recurring tasks and create new ones as needed.
  """

  def __init__(self, notion_token: str, database_id: str) -> None:
    """Initialize the updater.

    Args:
      notion_token: Notion API token.
      database_id: ID of the Notion database to update.
    """
    self.notion = Client(auth=notion_token)
    self.database_id = database_id

  def get_due_date(self, page: dict[str, Any]) -> datetime | None:
    """Extract due date from a page.

    Args:
      page: The Notion page object.

    Returns:
      The due date if present, None otherwise.
    """
    try:
      due_date = page[field_keys.PROPERTIES][DUE_DATE][field_keys.DATE]
      return datetime.fromisoformat(due_date[field_keys.START])
    except KeyError:
      logging.info(f"Due Date is not set for page {page[field_keys.ID]}")
      return None

  def extract_frequency(self, page: dict[str, Any]) -> Frequency:
    """Extract recurring frequncy from a page.

    Args:
      page: The Notion page object.

    Returns:
      The recurring frequency.
    """
    try:
      return Frequency.from_string(
        page[field_keys.PROPERTIES][RECURRING_FREQUENCY][field_keys.SELECT][
          field_keys.NAME]
      )
    except KeyError:
      logging.info(
        "No frequency found for page %s, return undefined instead",
        page[field_keys.ID]
      )
      return Frequency.UNDEFINED

  def calculate_next_due_date(
    self,
    current_due: datetime,
    frequency: Frequency,
  ) -> datetime:
    """Calculate the next due date based on frequency.

    Args:
      current_due: Current due date.
      frequency: Frequency enum value.

    Returns:
      Next due date.
    """
    return frequency.next_occurrence(current_due)

  def should_create_next_occurrence(
    self,
    due_date: datetime,
    frequency: Frequency,
    already_scheduled: bool,
  ) -> bool:
    """Returns true if `due_date` is in the range of [now, next_due_date].

    Args:
      due_date: The due date to check.
      frequency: Frequency enum value.
      page: The Notion page object to check for recurrence status.

    Returns:
      True if next occurrence should be created.
    """
    if already_scheduled:
      return False
    now = datetime.now()
    next_due_date = frequency.next_occurrence(now)
    return next_due_date >= due_date >= now

  def create_next_occurrence(
    self,
    todo_page_to_copy: dict[str, Any],
    frequency: Frequency,
  ) -> None:
    """Create a new task with updated due date based on frequency.

    Args:
      todo_page_to_copy: The Notion page object to copy.
      frequency: Frequency enum value.
    """
    current_due_date = self.get_due_date(todo_page_to_copy)
    if not current_due_date:
      logging.warning("No due date found for task: %s", todo_page_to_copy["id"])
      return
    new_due_date = self.calculate_next_due_date(
      current_due=current_due_date,
      frequency=frequency,
    )

    new_page_data = {
      "parent": {
        "database_id": self.database_id
      },
      field_keys.PROPERTIES: todo_page_to_copy[field_keys.PROPERTIES].copy(),
    }
    new_page_data[field_keys.PROPERTIES][DUE_DATE][field_keys.DATE][
      field_keys.START] = new_due_date.isoformat()

    if RECURRENCE_SCHEDULED not in todo_page_to_copy[field_keys.PROPERTIES]:
      new_page_data[field_keys.PROPERTIES][RECURRENCE_SCHEDULED] = {
        field_keys.CHECKBOX: {}
      }
    else:
      new_page_data[field_keys.PROPERTIES][RECURRENCE_SCHEDULED] = {
        field_keys.CHECKBOX: False
      }
    if field_keys.ICON in todo_page_to_copy:
      new_page_data[field_keys.ICON] = todo_page_to_copy[field_keys.ICON]
    new_page = self.notion.pages.create(**new_page_data)
    assert isinstance(new_page, dict), f"New page is not a dict: {new_page}"
    _maybe_update_old_page_status(page=new_page, notion_client=self.notion)

    logging.info(
      "Created new recurring task: %s with due date %s",
      new_page[field_keys.ID],
      new_due_date.isoformat(),
    )

  def update_todo_list(self) -> None:
    """Scan through database and create recurring tasks as needed."""
    logging.info("Using database ID: %s", self.database_id)
    response = self.notion.databases.query(
      database_id=self.database_id,
      filter={
        "and": [
          {
            field_keys.PROPERTY: RECURRING_FREQUENCY,
            field_keys.SELECT: {
              "is_not_empty": True
            },
          },
          {
            field_keys.PROPERTY: DUE_DATE,
            field_keys.DATE: {
              "is_not_empty": True
            },
          },
        ]
      },
    )
    assert isinstance(response, dict), f"Response is not a dict: {response}"
    for page in response[field_keys.RESULTS]:
      due_date = self.get_due_date(page)
      if not due_date:
        continue
      frequency = self.extract_frequency(page=page)
      if frequency == Frequency.UNDEFINED:
        continue
      if self.should_create_next_occurrence(
          due_date=due_date,
          frequency=frequency,
          already_scheduled=page[field_keys.PROPERTIES][RECURRENCE_SCHEDULED][
            field_keys.CHECKBOX],
      ):
        self.create_next_occurrence(todo_page_to_copy=page, frequency=frequency)
