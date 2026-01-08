from sqlalchemy import (
    Column, Integer, VARCHAR, ForeignKey, UniqueConstraint,
    BIGINT, BOOLEAN, TIMESTAMP, Float, Table
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# Association Table
offering_instructor_association = Table(
    'offering_instructors', Base.metadata,
    Column('offering_id', Integer, ForeignKey('offerings.id', ondelete='CASCADE'), primary_key=True),
    Column('instructor_id', Integer, ForeignKey('instructors.id', ondelete='CASCADE'), primary_key=True)
)

class Instructor(Base):
    __tablename__ = 'instructors'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(VARCHAR(255), unique=True, index=True, nullable=False)
    career_plot_file_id = Column(VARCHAR(255), nullable=True, index=True)
    
    offerings = relationship(
        "Offering",
        secondary=offering_instructor_association,
        back_populates="instructors"
    )

class Course(Base):
    __tablename__ = 'courses'
    
    code = Column(VARCHAR(20), primary_key=True, index=True)
    name = Column(VARCHAR(255), nullable=True, index=True)
    
    offerings = relationship("Offering", back_populates="course")

class Offering(Base):
    __tablename__ = 'offerings'
    
    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(VARCHAR(20), ForeignKey('courses.code', ondelete='CASCADE'), nullable=False, index=True)
    academic_year = Column(VARCHAR(10), nullable=False, index=True)
    semester = Column(VARCHAR(10), nullable=False, index=True)
    total_registered = Column(Integer, nullable=True)
    current_registered = Column(Integer, nullable=True)
    total_drop = Column(Integer, nullable=True)
    accepted_drop = Column(Integer, nullable=True)
    plot_file_id = Column(VARCHAR(255), nullable=True, index=True)

    __table_args__ = (UniqueConstraint('course_code', 'academic_year', 'semester', name='uq_offering'),)
    
    course = relationship("Course", back_populates="offerings")
    instructors = relationship(
        "Instructor",
        secondary=offering_instructor_association,
        back_populates="offerings"
    )
    grades = relationship("Grade", back_populates="offering")

class Grade(Base):
    __tablename__ = 'grades'
    
    id = Column(Integer, primary_key=True, index=True)
    offering_id = Column(Integer, ForeignKey('offerings.id', ondelete='CASCADE'), nullable=False, index=True)
    grade_type = Column(VARCHAR(10), nullable=False)
    count = Column(Float, nullable=False)
    
    __table_args__ = (UniqueConstraint('offering_id', 'grade_type', name='uq_grade'),)
    
    offering = relationship("Offering", back_populates="grades")

class User(Base):
    __tablename__ = 'users'
    
    telegram_user_id = Column(BIGINT, primary_key=True, index=True)
    first_name = Column(VARCHAR(255), nullable=True)
    last_name = Column(VARCHAR(255), nullable=True)
    username = Column(VARCHAR(255), nullable=True)
    is_subscribed = Column(BOOLEAN, default=True, nullable=False)
    subscribed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_active_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    is_blocked = Column(BOOLEAN, default=False, nullable=False)
    block_reason = Column(VARCHAR(255), nullable=True)
    blocked_at = Column(TIMESTAMP(timezone=True), nullable=True)

class Feedback(Base):
    __tablename__ = 'feedback'
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BIGINT, ForeignKey('users.telegram_user_id'), nullable=False, index=True)
    feedback_type = Column(VARCHAR(50), nullable=False)
    message_text = Column(VARCHAR, nullable=False)
    submitted_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    status = Column(VARCHAR(20), default='new', nullable=False)

    user = relationship("User")