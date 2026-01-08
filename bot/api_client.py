import os
import logging
from typing import List, Optional, Dict, Any, Union

import httpx

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ==============================================================================
# CORE HTTP CLIENT
# ==============================================================================

async def make_api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    is_binary_response: bool = False
) -> Optional[Union[Dict, List, bytes]]:
    """
    Centralized async HTTP client for backend API communication.
    Handles headers, errors, and response parsing.
    """
    headers: Dict[str, str] = {}

    if user_id is not None:
        headers["X-Telegram-User-ID"] = str(user_id)

    if is_binary_response:
        headers["Accept"] = "*/*"

    full_url = f"{API_BASE_URL}{endpoint}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.request(
                method,
                full_url,
                params=params,
                json=json_data,
                headers=headers
            )

            # No Content
            if response.status_code == 204:
                return None

            response.raise_for_status()

            if is_binary_response:
                return response.content

            if not response.content:
                return None

            return response.json()

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text[:200]
            try:
                error_detail = e.response.json().get("detail", error_detail)
            except Exception:
                pass

            logger.warning(
                f"API HTTP {e.response.status_code} at {endpoint}: {error_detail}"
            )
            raise

        except httpx.RequestError as e:
            logger.error(f"API request error at {endpoint}: {e}")
            raise

        except Exception as e:
            logger.error(
                f"Unexpected API client error at {endpoint}: {e}",
                exc_info=True
            )
            raise


# ==============================================================================
# SEARCH & DATA FETCHING
# ==============================================================================

async def search_items_api(query: str, search_type: str, user_id: int) -> Optional[List[Dict]]:
    endpoint = "/search/course" if search_type == "course" else "/search/prof"
    try:
        result = await make_api_request(
            "GET",
            endpoint,
            params={"q": query},
            user_id=user_id
        )
        return result if isinstance(result, list) else None
    except Exception:
        return None


async def get_offerings_for_course_api(course_code: str, user_id: int) -> Optional[List[Dict]]:
    try:
        return await make_api_request(
            "GET",
            f"/grades/offering/by_course/{course_code}",
            user_id=user_id
        )
    except Exception:
        return None


async def get_offerings_for_prof_api(instructor_id: int, user_id: int) -> Optional[List[Dict]]:
    try:
        return await make_api_request(
            "GET",
            f"/grades/offering/by_prof/{instructor_id}",
            user_id=user_id
        )
    except Exception:
        return None


async def get_offering_details_api(
    course_code: str,
    academic_year: str,
    semester: str,
    user_id: int
) -> Optional[Dict]:
    params = {
        "course_code": course_code,
        "academic_year": academic_year,
        "semester": semester
    }
    try:
        return await make_api_request(
            "GET",
            "/grades/offering/details",
            params=params,
            user_id=user_id
        )
    except Exception:
        return None


async def get_grades_distribution_api(offering_id: int, user_id: int) -> Optional[Dict]:
    try:
        return await make_api_request(
            "GET",
            f"/grades/offering/{offering_id}",
            user_id=user_id
        )
    except Exception:
        return None


async def get_professor_dossier_api(prof_id: int, user_id: int) -> Optional[Dict]:
    try:
        return await make_api_request(
            "GET",
            f"/professors/{prof_id}/dossier",
            user_id=user_id
        )
    except Exception:
        return None


# ==============================================================================
# USER ACTIONS
# ==============================================================================

async def subscribe_user_api(
    tg_user_id: int,
    first_name: Optional[str],
    last_name: Optional[str],
    username: Optional[str]
) -> Optional[Dict]:
    payload = {
        "telegram_user_id": tg_user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username
    }
    try:
        return await make_api_request(
            "POST",
            "/users/subscribe",
            json_data=payload,
            user_id=tg_user_id
        )
    except Exception:
        return None


async def unsubscribe_user_api(tg_user_id: int) -> Optional[Dict]:
    """
    Marks a user as unsubscribed.
    This endpoint mutates state, so POST is correct.
    """
    try:
        return await make_api_request(
            "POST",
            f"/users/{tg_user_id}/unsubscribe",
            user_id=tg_user_id
        )
    except Exception:
        return None


async def submit_feedback_api(
    tg_user_id: int,
    feedback_type: str,
    message_text: str,
    username: Optional[str]=None
) -> Optional[Dict]:
    payload = {
        "telegram_user_id": tg_user_id,
        "feedback_type": feedback_type,
        "message_text": message_text,
        "username":username
    }
    try:
        return await make_api_request(
            "POST",
            "/feedback/",
            json_data=payload,
            user_id=tg_user_id
        )
    except Exception:
        return None


# ==============================================================================
# ADMIN ACTIONS
# ==============================================================================

async def get_user_status_api(
    target_user_id: Union[str, int],
    admin_user_id: int
) -> Optional[Dict]:
    try:
        return await make_api_request(
            "GET",
            f"/admin/users/{target_user_id}",
            user_id=admin_user_id
        )
    except Exception:
        return None


async def set_user_block_status_api(
    target_user_id: Union[str, int],
    block: bool,
    reason: Optional[str],
    admin_user_id: int
) -> Optional[Dict]:
    payload = {
        "is_blocked": block,
        "block_reason": reason
    }
    try:
        return await make_api_request(
            "PUT",
            f"/admin/users/{target_user_id}/block_status",
            json_data=payload,
            user_id=admin_user_id
        )
    except Exception:
        return None


async def initiate_broadcast_api(message_text: str, admin_user_id: int) -> Optional[Dict]:
    payload = {"message_text": message_text}
    try:
        return await make_api_request(
            "POST",
            "/admin/broadcast/",
            json_data=payload,
            user_id=admin_user_id
        )
    except Exception:
        return None
