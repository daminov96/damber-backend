"""`app/modules/admin/permissions.py::role_can` — dependency-darajasidagi
birlik testlari. `finance` moduliga hali endpoint yo'q, shuning uchun bu
xatti-harakat HTTP integratsion test orqali sinalmaydi (`tests/test_admin.py`
faqat HTTP seam'ida ishlaydi) — sof funksiya bo'lgani uchun to'g'ridan-to'g'ri
chaqirish yetarli va yagona yo'l."""

from app.modules.admin.permissions import ROLE_MATRIX, AdminModule, role_can
from app.modules.users.models import AdminRole


class TestRoleCan:
    def test_super_can_access_every_module(self):
        for module in AdminModule:
            assert role_can(AdminRole.super, module) is True

    def test_moderator_can_access_its_modules(self):
        for module in (
            AdminModule.moderation,
            AdminModule.users,
            AdminModule.bookings,
            AdminModule.analytics,
        ):
            assert role_can(AdminRole.moderator, module) is True

    def test_moderator_cannot_access_finance_or_team(self):
        assert role_can(AdminRole.moderator, AdminModule.finance) is False
        assert role_can(AdminRole.moderator, AdminModule.team) is False
        assert role_can(AdminRole.moderator, AdminModule.settings) is False
        assert role_can(AdminRole.moderator, AdminModule.content) is False

    def test_finance_scoped_to_finance_bookings_analytics(self):
        assert role_can(AdminRole.finance, AdminModule.finance) is True
        assert role_can(AdminRole.finance, AdminModule.bookings) is True
        assert role_can(AdminRole.finance, AdminModule.analytics) is True
        assert role_can(AdminRole.finance, AdminModule.moderation) is False
        assert role_can(AdminRole.finance, AdminModule.users) is False

    def test_content_scoped_to_content_moderation_analytics(self):
        assert role_can(AdminRole.content, AdminModule.content) is True
        assert role_can(AdminRole.content, AdminModule.moderation) is True
        assert role_can(AdminRole.content, AdminModule.analytics) is True
        assert role_can(AdminRole.content, AdminModule.finance) is False
        assert role_can(AdminRole.content, AdminModule.team) is False

    def test_none_role_has_no_access(self):
        for module in AdminModule:
            assert role_can(None, module) is False

    def test_role_matrix_covers_every_admin_role(self):
        assert set(ROLE_MATRIX.keys()) == set(AdminRole)
