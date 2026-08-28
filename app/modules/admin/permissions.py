import enum

from app.modules.users.models import AdminRole


class AdminModule(enum.StrEnum):
    """Admin panelning huquq bilan qulflanadigan bo'limlari."""

    moderation = "moderation"
    users = "users"
    finance = "finance"
    bookings = "bookings"
    content = "content"
    analytics = "analytics"
    settings = "settings"
    team = "team"


# Qaysi rol qaysi bo'limga kira oladi. Super — hammasiga; moderator tarif
# narxiga (finance), moliyachi esa kontentga tegolmaydi. Frontend'dagi
# `store/admin.ts::ROLE_MATRIX` bilan bir xil mazmun — ikkalasi ham kod
# (DB emas), o'zgarganda ikkala tomon qo'lda sinxronlanadi.
ROLE_MATRIX: dict[AdminRole, frozenset[AdminModule]] = {
    AdminRole.super: frozenset(AdminModule),
    AdminRole.moderator: frozenset(
        {AdminModule.moderation, AdminModule.users, AdminModule.bookings, AdminModule.analytics}
    ),
    AdminRole.finance: frozenset(
        {AdminModule.finance, AdminModule.bookings, AdminModule.analytics}
    ),
    AdminRole.content: frozenset(
        {AdminModule.content, AdminModule.moderation, AdminModule.analytics}
    ),
}


def role_can(admin_role: AdminRole | None, module: AdminModule) -> bool:
    """Shu huquq darajasi berilgan bo'lim bilan ishlay oladimi."""
    if admin_role is None:
        return False
    return module in ROLE_MATRIX.get(admin_role, frozenset())
