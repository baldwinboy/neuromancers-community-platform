from django.db.utils import IntegrityError
from django.test import TestCase

from apps.accounts.models import User


class UserTestCase(TestCase):
    def setUp(self):
        self.user_attributes = {
            "first_name": "Dana",
            "last_name": "Franklin",
            "password": "!#_butter_Flight_789",
            "email": "danafranklin@kindred.org",
        }

    def test_username_banned_words_check_fail(self):
        """
        Usernames with banned words surrounded by a single character cannot be created
        """
        username = "admin_"

        with self.assertRaises(IntegrityError):
            User.objects.create(**self.user_attributes, username=username)

    def test_username_banned_words_check_pass(self):
        """
        Usernames other than banned words surrounded by a single character can be created
        """
        username = "external_admins"

        User.objects.create(**self.user_attributes, username=username)
