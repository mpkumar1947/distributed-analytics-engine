import logging
from typing import List, Dict, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from constants import (
    COURSE_SEARCH_MODE, PROF_SEARCH_MODE, CANCEL, BACK_TO_MAIN,
    COURSE_SELECT_PREFIX, PROF_SELECT_PREFIX, VIEW_PROF_COURSES_PREFIX, YEAR_SEM_SELECT_PREFIX,
    BACK_TO_TYPING_COURSE, BACK_TO_TYPING_PROF,
    BACK_TO_PROF_SEARCH_LIST, BACK_TO_COURSE_SEARCH_LIST,
    BACK_TO_PROF_COURSE_LIST_PREFIX, BACK_TO_YEAR_SEM_SELECT_PREFIX,
    ITEMS_PER_PAGE,
    PAGE_COURSE_SEARCH_RESULTS_PREFIX, PAGE_PROF_SEARCH_RESULTS_PREFIX,
    PAGE_PROF_COURSE_LIST_PREFIX, PAGE_YEAR_SEMESTER_PREFIX,
    BACK_TO_COURSE_LIST_FROM_PLOT_PREFIX,
    FEEDBACK_TYPE_BUG, FEEDBACK_TYPE_SUGGESTION, FEEDBACK_TYPE_GENERAL,
    CONFIRM_SEND_FEEDBACK, CANCEL_FEEDBACK
)

logger = logging.getLogger(__name__)

# ==============================================================================
# MAIN NAVIGATION KEYBOARDS
# ==============================================================================

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Initial search mode selection."""
    keyboard = [
        [InlineKeyboardButton("📚 Search by Course (Code/Title)", callback_data=COURSE_SEARCH_MODE)],
        [InlineKeyboardButton("🧑‍🏫 Search by Professor", callback_data=PROF_SEARCH_MODE)]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Generic cancel button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)]])

def get_restart_keyboard() -> InlineKeyboardMarkup:
    """Button to restart the search flow."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Restart Search", callback_data=BACK_TO_MAIN)]])

# ==============================================================================
# PAGINATION HELPERS
# ==============================================================================

def _add_pagination_buttons(
    keyboard: List[List[InlineKeyboardButton]],
    current_page: int,
    total_items: int,
    base_callback_prefix: str,
    payload_parts: Optional[List[str]] = None
) -> None:
    if total_items <= ITEMS_PER_PAGE:
        return 

    total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    row = []
    
    payload_str = "_".join(map(str, payload_parts)) + "_" if payload_parts else ""

    if current_page > 0:
        row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"{base_callback_prefix}{payload_str}{current_page - 1}"))

    if current_page < total_pages - 1:
        row.append(InlineKeyboardButton("Next ➡️", callback_data=f"{base_callback_prefix}{payload_str}{current_page + 1}"))

    if row:
        keyboard.append(row)

# ==============================================================================
# DYNAMIC SELECTION KEYBOARDS
# ==============================================================================

def create_search_results_keyboard(
    all_results: List[Dict],
    search_type: str,
    current_page: int = 0
) -> InlineKeyboardMarkup:
    keyboard = []
    prefix = COURSE_SELECT_PREFIX if search_type == 'course' else PROF_SELECT_PREFIX
    
    # Slice results for current page
    start = current_page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = all_results[start:end]

    for item in page_items:
        if search_type == 'course':
            item_id = item.get('code')
            title = item.get('name', item_id)
            text = f"{item_id} - {title}" if title and title != item_id else item_id
        else:
            item_id = item.get('id')
            text = item.get('name', f"Prof ID {item_id}")

        if item_id:
            keyboard.append([InlineKeyboardButton(text[:60], callback_data=f"{prefix}{item_id}")])

    # Pagination
    pg_prefix = PAGE_COURSE_SEARCH_RESULTS_PREFIX if search_type == 'course' else PAGE_PROF_SEARCH_RESULTS_PREFIX
    _add_pagination_buttons(keyboard, current_page, len(all_results), pg_prefix)

    # Navigation Footer
    back_cb = BACK_TO_TYPING_COURSE if search_type == 'course' else BACK_TO_TYPING_PROF
    keyboard.append([
         InlineKeyboardButton("⬅️ Re-enter Search", callback_data=back_cb),
         InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)
    ])
    return InlineKeyboardMarkup(keyboard)

def create_prof_course_selection_keyboard(
    courses: List[Dict], 
    prof_id_str: str,
    current_page: int = 0
) -> InlineKeyboardMarkup:
    keyboard = []
    start = current_page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    
    for item in courses[start:end]:
        code = item.get('course_code')
        title = item.get('course_name')
        if not code: continue
            
        text = f"{code} - {title}" if title and title != code else code
        # Format: cs_{code}|prof|{prof_id}
        keyboard.append([InlineKeyboardButton(text[:60], callback_data=f"{COURSE_SELECT_PREFIX}{code}|prof|{prof_id_str}")])

    _add_pagination_buttons(
        keyboard, current_page, len(courses),
        PAGE_PROF_COURSE_LIST_PREFIX, payload_parts=[prof_id_str]
    )

    keyboard.append([
        InlineKeyboardButton("⬅️ Different Professor", callback_data=BACK_TO_PROF_SEARCH_LIST),
        InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)
    ])
    return InlineKeyboardMarkup(keyboard)

def create_year_semester_keyboard(
    terms: List[Dict], 
    back_id: str, 
    mode: str, 
    current_page: int = 0
) -> InlineKeyboardMarkup:
    keyboard = []
    
    # Deduplicate terms
    unique_terms = {}
    for t in terms:
        key = (t.get('academic_year'), t.get('semester'))
        if all(key): unique_terms[key] = t
    
    # Sort terms (Newest first)
    sem_map = {'Odd': 1, 'Even': 2, 'Summer': 3}
    sorted_terms = sorted(
        unique_terms.values(),
        key=lambda x: (-int(x['academic_year'].split('-')[0]), sem_map.get(x['semester'], 99))
    )

    start = current_page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE

    for term in sorted_terms[start:end]:
        y, s = term['academic_year'], term['semester']
        # Format: ysel_{year}|{sem}|{mode}|{back_id}
        keyboard.append([InlineKeyboardButton(f"{y} ({s})", callback_data=f"{YEAR_SEM_SELECT_PREFIX}{y}|{s}|{mode}|{back_id}")])

    _add_pagination_buttons(
        keyboard, current_page, len(sorted_terms),
        PAGE_YEAR_SEMESTER_PREFIX, payload_parts=[mode, back_id]
    )

    # Back button logic
    if mode == 'course':
        back_cb = BACK_TO_COURSE_SEARCH_LIST
    else:
        back_cb = f"{BACK_TO_PROF_COURSE_LIST_PREFIX}{back_id}"

    keyboard.append([
        InlineKeyboardButton("⬅️ Back", callback_data=back_cb),
        InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)
    ])
    return InlineKeyboardMarkup(keyboard)

def get_final_options_keyboard(course_code: str, search_mode: Optional[str], prof_id: Optional[int]) -> InlineKeyboardMarkup:
    """Options displayed after showing the grade plot."""
    keyboard = []
    
    # 1. Change Semester
    keyboard.append([InlineKeyboardButton("⬅️ Select Diff. Year/Sem", callback_data=f"{BACK_TO_YEAR_SEM_SELECT_PREFIX}{course_code}")])

    # 2. Back to Course List (Context aware)
    if search_mode == 'course':
        keyboard.append([InlineKeyboardButton("⬅️ Select Diff. Course", callback_data=f"{BACK_TO_COURSE_LIST_FROM_PLOT_PREFIX}course")])
    elif search_mode == 'prof' and prof_id:
        keyboard.append([InlineKeyboardButton("⬅️ Select Diff. Course", callback_data=f"{BACK_TO_COURSE_LIST_FROM_PLOT_PREFIX}prof_{prof_id}")])

    # 3. Restart
    keyboard.append([InlineKeyboardButton("🔄 New Search", callback_data=BACK_TO_MAIN)])
    return InlineKeyboardMarkup(keyboard)

def get_dossier_keyboard(prof_id: int) -> InlineKeyboardMarkup:
    """Options displayed with Professor Dossier."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 View All Courses Taught", callback_data=f"{VIEW_PROF_COURSES_PREFIX}{prof_id}")],
        [InlineKeyboardButton("⬅️ Select Different Professor", callback_data=BACK_TO_PROF_SEARCH_LIST)],
        [InlineKeyboardButton("🔄 New Search", callback_data=BACK_TO_MAIN)]
    ])

# ==============================================================================
# FEEDBACK KEYBOARDS
# ==============================================================================

def get_feedback_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐛 Bug Report", callback_data=FEEDBACK_TYPE_BUG)],
        [InlineKeyboardButton("💡 Suggestion", callback_data=FEEDBACK_TYPE_SUGGESTION)],
        [InlineKeyboardButton("🗣️ General Feedback", callback_data=FEEDBACK_TYPE_GENERAL)],
        [InlineKeyboardButton("❌ Cancel Feedback", callback_data=CANCEL)]
    ])

def get_feedback_entry_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Cancel & Change Type", callback_data=CANCEL_FEEDBACK)]])

def get_feedback_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, send it", callback_data=CONFIRM_SEND_FEEDBACK)],
        [InlineKeyboardButton("✏️ Edit / Re-type", callback_data=CANCEL_FEEDBACK)],
        [InlineKeyboardButton("🗑️ Discard", callback_data=CANCEL)]
    ])