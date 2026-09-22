"""
Test Role-Based Access Control logic.
"""
import pytest
from app.rbac import get_allowed_namespaces, is_authorized


def test_hr_can_access_employee_handbook():
    assert is_authorized("hr", "employee_handbook") is True


def test_hr_can_access_hr_master_data():
    assert is_authorized("hr", "hr_employee_master_data") is True


def test_hr_cannot_access_finance():
    assert is_authorized("hr", "financial_summary") is False
    assert is_authorized("hr", "quarterly_financial_report") is False


def test_hr_cannot_access_engineering():
    assert is_authorized("hr", "engineering_master_doc") is False


def test_finance_can_access_financial_docs():
    assert is_authorized("finance", "financial_summary") is True
    assert is_authorized("finance", "quarterly_financial_report") is True


def test_finance_cannot_access_hr():
    assert is_authorized("finance", "employee_handbook") is False
    assert is_authorized("finance", "hr_employee_master_data") is False


def test_engineering_can_access_engineering_docs():
    assert is_authorized("engineering", "engineering_master_doc") is True
    assert is_authorized("engineering", "enterprise_rag_architecture") is True


def test_engineering_cannot_access_marketing():
    assert is_authorized("engineering", "marketing_report_2024") is False


def test_marketing_can_access_marketing_docs():
    assert is_authorized("marketing", "marketing_report_2024") is True
    assert is_authorized("marketing", "marketing_report_q1_2024") is True


def test_admin_can_access_all():
    namespaces = get_allowed_namespaces("admin")
    assert "employee_handbook" in namespaces
    assert "financial_summary" in namespaces
    assert "engineering_master_doc" in namespaces
    assert "marketing_report_2024" in namespaces
    assert "rbac_access_matrix" in namespaces


def test_unknown_role_gets_nothing():
    assert get_allowed_namespaces("hacker") == []
    assert is_authorized("hacker", "employee_handbook") is False
