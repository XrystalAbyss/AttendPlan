"""No credentials: model actual multi-tab challenge selection behavior."""
from types import SimpleNamespace

import pytest

from app.adapters.portal_session import select_authentication_page
from app.domain.totp_models import TotpOriginSecurityError
from app.services.login_orchestrator import is_authenticated_student_page


class Page:
    def __init__(self,url,otp=False,mobile=False):
        self.url=url
        self.otp=otp
        self.mobile=mobile
    def query_selector(self,selector):
        visible=self.otp if "otp" in selector else self.mobile
        return SimpleNamespace(is_visible=lambda:True) if visible else None


def test_visible_otp_tab_wins_over_preexisting_portal_tab():
    dashboard=Page("https://mrei.icloudems.com/corecampus/student/student_index.php")
    otp=Page("https://usermanagement.icloudems.com/auth/login",otp=True)
    assert select_authentication_page([dashboard,otp],require_otp=True) is otp


def test_hidden_or_absent_challenge_never_generates_a_target():
    dashboard=Page("https://mrei.icloudems.com/corecampus/student/grades/new/myreportcard.php")
    assert select_authentication_page([dashboard],require_otp=True) is None


def test_lookalike_origin_cannot_receive_an_otp():
    evil=Page("https://mrei.icloudems.com.attacker.invalid/login",otp=True)
    assert select_authentication_page([evil],require_otp=True) is None
    assert is_authenticated_student_page(Page("https://attacker.invalid/corecampus/student/student_dashboard.php")) is False


def test_multiple_challenges_stop_for_user_selection():
    pages=[Page("https://usermanagement.icloudems.com/auth/login",otp=True) for _ in range(2)]
    with pytest.raises(TotpOriginSecurityError):
        select_authentication_page(pages,require_otp=True)
