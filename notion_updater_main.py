from absl import app
from absl import flags
from absl import logging
import time

from notion_updater import NotionTodoUpdater

FLAGS = flags.FLAGS
flags.DEFINE_string("notion_token", None, "Notion API token", required=True)
flags.DEFINE_string("database_id", None, "Notion database ID", required=True)
flags.DEFINE_integer(
  "update_frequency_minutes", 5, "Update frequency in minutes"
)
flags.DEFINE_enum(
  "log_level", "info", [
    "debug",
    "info",
    "warning",
    "error",
  ], "Logging level"
)


def main(argv: list[str]) -> None:
  """Main entry point.

    Args:
        argv: Command line arguments.
    """
  updater = NotionTodoUpdater(
    notion_token=FLAGS.notion_token,
    database_id=FLAGS.database_id,
  )

  while True:
    logging.info("Running update cycle...")
    updater.update_todo_list()
    logging.info(
      "Update cycle completed. Sleeping for %d minutes...",
      FLAGS.update_frequency_minutes,
    )
    time.sleep(FLAGS.update_frequency_minutes * 60)


if __name__ == "__main__":
  app.run(main)
