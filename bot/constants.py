# bot/constants.py

# ==============================================================================
# CONVERSATION STATES
# ==============================================================================
(
    SELECTING_ACTION,
    TYPING_COURSE,
    TYPING_PROF,
    SELECTING_COURSE_RESULTS,
    SELECTING_PROF_RESULTS,
    SELECTING_COURSE_FOR_PROF,
    SELECTING_YEAR_SEMESTER,
    SHOWING_FINAL_GRADES,
    ASK_FEEDBACK_TYPE,
    TYPING_FEEDBACK_MESSAGE,
    CONFIRM_FEEDBACK_SUBMISSION
) = range(11)

# ==============================================================================
# CALLBACK DATA & PATTERNS
# ==============================================================================
# Search Modes
COURSE_SEARCH_MODE = "mode_course"
PROF_SEARCH_MODE = "mode_prof"

# Navigation & Actions
CANCEL = "cancel"
BACK_TO_MAIN = "back_main"
BACK_TO_TYPING_COURSE = "back_type_crs"
BACK_TO_TYPING_PROF = "back_type_prof"
BACK_TO_PROF_COURSE_LIST_PREFIX = "back_prof_crs_list_"
BACK_TO_COURSE_SEARCH_LIST = "back_crs_srch_list"
BACK_TO_PROF_SEARCH_LIST = "back_prof_srch_list"
BACK_TO_YEAR_SEM_SELECT_PREFIX = "back_ys_sel_"
BACK_TO_COURSE_LIST_FROM_PLOT_PREFIX = "back_clp_"
VIEW_PROF_COURSES_PREFIX = "vpc_"

# Selection Prefixes
COURSE_SELECT_PREFIX = "cs_"
PROF_SELECT_PREFIX = "ps_"
YEAR_SEM_SELECT_PREFIX = "ysel_"

# Pagination Prefixes
ITEMS_PER_PAGE = 8
PAGE_COURSE_SEARCH_RESULTS_PREFIX = "p_csr_"
PAGE_PROF_SEARCH_RESULTS_PREFIX = "p_psr_"
PAGE_PROF_COURSE_LIST_PREFIX = "p_pcl_"
PAGE_YEAR_SEMESTER_PREFIX = "p_ys_"

# Feedback Actions
FEEDBACK_TYPE_BUG = "fb_bug"
FEEDBACK_TYPE_SUGGESTION = "fb_suggestion"
FEEDBACK_TYPE_GENERAL = "fb_general"
CONFIRM_SEND_FEEDBACK = "fb_confirm_send"
CANCEL_FEEDBACK = "fb_cancel"