import os
import dryable
import logging
import sys


class DryRunHelper:

    disclaimer_message = """
===
DRY RUN
gh-action_release has been invoked with input `dry_run=true`.
It won't actually do anything having impacts, but will still report what would have been done.
===
    """

    @staticmethod
    def init():
        dry_run: bool = DryRunHelper.is_dry_run_enabled()
        if dry_run:
            DryRunHelper.__print_disclaimer()
            dryable.set(True)

            console = logging.StreamHandler(sys.stdout)
            console.setLevel(logging.INFO)
            formatter = logging.Formatter('%(message)s (--dry-run)')  # custom format, avoid having the datetime,log level printed
            console.setFormatter(formatter)
            logging.getLogger("dryable").setLevel(logging.INFO)
            logging.getLogger("dryable").addHandler(console)

    @staticmethod
    def is_dry_run_enabled():
        return os.environ.get('INPUT_DRY_RUN', 'false').lower() == "true"

    @classmethod
    def __print_disclaimer(cls):
        print(cls.disclaimer_message)
