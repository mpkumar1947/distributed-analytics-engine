import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# ==============================================================================
# BASE MODELS
# ==============================================================================
class InstructorBase(BaseModel):
    name: str

class CourseBase(BaseModel):
    code: str
    name: Optional[str] = None

# ==============================================================================
# SEARCH MODELS
# ==============================================================================
class InstructorSearchResult(InstructorBase):
    id: int
    class Config:
        from_attributes = True

class CourseSearchResult(CourseBase):
    class Config:
        from_attributes = True

# ==============================================================================
# NESTED MODELS
# ==============================================================================
class CourseInOfferingSchema(BaseModel):
    code: str
    name: Optional[str] = None
    class Config:
        from_attributes = True

class InstructorInOfferingSchema(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# ==============================================================================
# OFFERING MODELS
# ==============================================================================
class OfferingSchema(BaseModel):
    id: int
    academic_year: str
    semester: str
    total_registered: Optional[int] = None
    current_registered: Optional[int] = None
    plot_file_id: Optional[str] = None
    course: CourseInOfferingSchema
    instructors: List[InstructorInOfferingSchema] = []

    class Config:
        from_attributes = True

class OfferingTermWithInstructorsInfo(BaseModel):
    """Used for listing terms under a specific course."""
    academic_year: str
    semester: str
    instructors: List[InstructorInOfferingSchema] = []
    course: CourseInOfferingSchema

    class Config:
        from_attributes = True

class ProfCourseOfferingInfo(BaseModel):
    """Used for listing courses taught by a specific professor."""
    id: int
    course: CourseInOfferingSchema
    academic_year: str
    semester: str
    plot_file_id: Optional[str] = None

    class Config:
        from_attributes = True

# ==============================================================================
# GRADE & STATS MODELS
# ==============================================================================
class GradeSchema(BaseModel):
    grade_type: str
    count: int
    percentage: Optional[float] = None
    class Config:
        from_attributes = True

class GradeDistributionResponse(BaseModel):
    offering: OfferingSchema
    grades: List[GradeSchema] = []
    total_graded_students: int
    centric_grading: Optional[str] = None
    class Config:
        from_attributes = True

class MostTaughtCourseSchema(BaseModel):
    code: str
    count: int

class OfferingSPISchema(BaseModel):
    spi: float
    student_count: int
    academic_year: str
    semester: str
    course_code: str

class CareerStatsSchema(BaseModel):
    career_spi: float
    consistency_sigma: float
    career_centric_grading: str
    total_students_graded_career: int
    total_offerings_count: int
    most_taught_courses: List[MostTaughtCourseSchema]
    most_generous_offering: Optional[OfferingSPISchema] = None
    toughest_offering: Optional[OfferingSPISchema] = None

class ProfessorDossierSchema(BaseModel):
    instructor_name: str
    career_plot_file_id: Optional[str] = None
    stats: Optional[CareerStatsSchema] = None
    message: Optional[str] = None

# ==============================================================================
# FEEDBACK MODELS
# ==============================================================================
class FeedbackBase(BaseModel):
    feedback_type: str = Field(..., examples=["bug", "suggestion", "general"])
    message_text: str

class FeedbackCreate(FeedbackBase):
    telegram_user_id: int

class FeedbackRead(FeedbackBase):
    id: int
    submitted_at: datetime.datetime
    status: str
    telegram_user_id: Optional[int] = None
    class Config:
        from_attributes = True

# ==============================================================================
# USER MODELS
# ==============================================================================
class UserBase(BaseModel):
    telegram_user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    is_subscribed: bool
    is_blocked: bool
    subscribed_at: datetime.datetime
    last_active_at: datetime.datetime
    block_reason: Optional[str] = None
    blocked_at: Optional[datetime.datetime] = None
    class Config:
        from_attributes = True

class UserBlockStatusUpdate(BaseModel):
    is_blocked: bool
    block_reason: Optional[str] = None