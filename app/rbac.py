"""
RBAC Policy Matrix
Maps each role to the ChromaDB collection namespaces they may access.
"""

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "hr": [
        "employee_handbook",
        "hr_employee_master_data",
    ],
    "finance": [
        "financial_summary",
        "quarterly_financial_report",
    ],
    "engineering": [
        "engineering_master_doc",
        "enterprise_rag_architecture",
    ],
    "marketing": [
        "marketing_report_2024",
        "marketing_report_q1_2024",
        "marketing_report_q2_2024",
        "marketing_report_q3_2024",
        "market_report_q4_2024",
    ],
    "admin": [
        "employee_handbook",
        "hr_employee_master_data",
        "financial_summary",
        "quarterly_financial_report",
        "engineering_master_doc",
        "enterprise_rag_architecture",
        "marketing_report_2024",
        "marketing_report_q1_2024",
        "marketing_report_q2_2024",
        "marketing_report_q3_2024",
        "market_report_q4_2024",
        "rbac_access_matrix",
    ],
}


def get_allowed_namespaces(role: str) -> list[str]:
    """Return the list of document namespaces accessible for a role."""
    return ROLE_PERMISSIONS.get(role.lower(), [])


def is_authorized(role: str, namespace: str) -> bool:
    return namespace in get_allowed_namespaces(role)


def list_roles() -> list[str]:
    """Return all currently known role names."""
    return sorted(ROLE_PERMISSIONS.keys())


def role_exists(role_name: str) -> bool:
    return role_name.lower() in ROLE_PERMISSIONS


def add_role(role_name: str, namespaces: list[str] | None = None) -> str:
    """
    Register a new role in the RBAC policy matrix.
    Raises ValueError if the role already exists or the name is invalid.
    """
    role_name = role_name.strip().lower().replace(" ", "_")
    if not role_name:
        raise ValueError("Role name cannot be empty.")
    if role_name in ROLE_PERMISSIONS:
        raise ValueError(f"Role '{role_name}' already exists.")

    ROLE_PERMISSIONS[role_name] = list(namespaces or [])

    # Admin retains full visibility across every namespace, including new roles.
    for ns in ROLE_PERMISSIONS[role_name]:
        if ns not in ROLE_PERMISSIONS["admin"]:
            ROLE_PERMISSIONS["admin"].append(ns)

    return role_name