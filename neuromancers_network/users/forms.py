from allauth.account.forms import SignupForm

from neuromancers_network.users.validators import validate_username_not_blocked


class UserSignupForm(SignupForm):
    """
    Form rendered on the user sign up screen.

    Default fields are added automatically from ``ACCOUNT_SIGNUP_FIELDS``.
    """

    def clean_username(self) -> str:
        username = super().clean_username()
        validate_username_not_blocked(username)
        return username
