"""Mini employee-hub tools, as plain functions (see gen_spec's fn_to_toolinfo)."""

from typing import Any, Dict, List, Optional


def get_bank_account(user_id: int) -> Optional[Dict[str, Any]]:
    """Return the employee's bank account, or None if none is set.

    Args:
        user_id (int): The employee whose bank account is read.

    Returns:
        Optional[Dict[str, Any]]: Account number, routing number and IBAN.
    """
    raise NotImplementedError("signature-only fixture: never executed")


def get_direct_reports(user_id: int) -> List[Dict[str, Any]]:
    """Return the employees who report directly to user_id.

    Args:
        user_id (int): The manager whose direct reports are listed.

    Returns:
        List[Dict[str, Any]]: One employee record per direct report.
    """
    raise NotImplementedError("signature-only fixture: never executed")


def update_employee(
    user_id: int,
    home_address: Optional[str] = None,
    email: Optional[str] = None,
    organization: Optional[str] = None,
    salary: Optional[float] = None,
) -> Dict[str, Any]:
    """Update the provided employee fields, leaving the others unchanged.

    Args:
        user_id (int): The employee to update.
        home_address (Optional[str]): New home address.
        email (Optional[str]): New work email.
        organization (Optional[str]): New organization.
        salary (Optional[float]): New salary amount.

    Returns:
        Dict[str, Any]: The updated employee record.
    """
    raise NotImplementedError("signature-only fixture: never executed")


def update_passport(
    user_id: int,
    issue_date: Optional[str] = None,
    expiry_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Update the provided passport fields for an employee.

    Args:
        user_id (int): The employee whose passport is updated.
        issue_date (Optional[str]): New issue date, YYYY-MM-DD.
        expiry_date (Optional[str]): New expiration date, YYYY-MM-DD.

    Returns:
        Dict[str, Any]: The updated passport record.
    """
    raise NotImplementedError("signature-only fixture: never executed")


def create_time_off_request(
    user_id: int, leave_type: str, start_date: str, end_date: str
) -> Dict[str, Any]:
    """Create a Pending time-off request.

    Args:
        user_id (int): The employee the request is created for.
        leave_type (str): One of Vacation, Sick, Paternity.
        start_date (str): First day of leave, YYYY-MM-DD.
        end_date (str): Last day of leave, YYYY-MM-DD, not before start_date.

    Returns:
        Dict[str, Any]: The created time-off request.
    """
    raise NotImplementedError("signature-only fixture: never executed")
