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