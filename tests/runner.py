"""Custom test runner that excludes events.models from discovery."""

import sys
from django.test.runner import DiscoverRunner


def custom_discover(self, start_dir=None, pattern=None, **kwargs):
    """Custom discover that excludes events/models directory."""
    from django.test.utils import get_installed_apps
    from unittest import TestLoader

    # Get the standard test loader
    loader = TestLoader()

    # Override _get_module_from_name to exclude events.models
    original_get_module = loader._get_module_from_name

    def custom_get_module(name):
        if name == "events.models" or name.startswith("events.models."):
            raise ImportError(f"Excluded: {name}")
        return original_get_module(name)

    loader._get_module_from_name = custom_get_module
    return loader.discover(start_dir, pattern, **kwargs)


class CustomTestRunner(DiscoverRunner):
    def run_tests(self, test_labels):
        from django.conf import settings

        # Get settings
        settings.INSTALLED_APPS = settings.INSTALLED_APPS

        # Get discover kwargs
        discover_kwargs = {}
        if self.pattern is not None:
            discover_kwargs["pattern"] = self.pattern
        if self.top_level is not None:
            discover_kwargs["top_level_dir"] = self.top_level

        # Build suite manually
        all_tests = []

        for label in (test_labels or ["."]):
            if label == "events":
                # When events is specified, directly import only events.tests
                with self.load_with_patterns():
                    from events import tests as events_tests
                    all_tests.extend(
                        self.test_loader.loadTestsFromModule(events_tests)
                    )
            else:
                tests = self.test_loader.loadTestsFromName(label)
                all_tests.extend(iter_test_cases(tests))

        suite = self.test_suite(all_tests)

        old_config = self.setup_databases()
        result = self.run_suite(suite)
        self.teardown_databases(old_config)
        return self.suite_result(suite, result)


def iter_test_cases(tests):
    """Recursively extract test cases from test suite."""
    from unittest import TestSuite, TestCase

    if isinstance(tests, TestCase):
        return [tests]
    elif isinstance(tests, TestSuite):
        result = []
        for test in tests:
            result.extend(iter_test_cases(test))
        return result
    return []