from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

# Local Imports
from .. import crud, schemas
from ..database import get_db
from ..utils.limiter import limiter

router = APIRouter(
    prefix="/search",
    tags=["Search"],
)

@router.get("/course", response_model=List[schemas.CourseSearchResult])
@limiter.limit("15/minute")
async def search_courses_endpoint(
    request: Request,
    q: str = Query(..., min_length=2, description="Partial course code or name"),
    db: AsyncSession = Depends(get_db)
):
    courses = await crud.search_courses(db, query=q)
    if not courses:
         raise HTTPException(status_code=404, detail="No courses found.")
    
    return [schemas.CourseSearchResult.from_orm(c) for c in courses]

@router.get("/prof", response_model=List[schemas.InstructorSearchResult])
@limiter.limit("15/minute")
async def search_profs_endpoint(
    request: Request, 
    q: str = Query(..., min_length=3, description="Partial professor name"),
    db: AsyncSession = Depends(get_db)
):
    instructors = await crud.search_instructors(db, query=q)
    if not instructors:
         raise HTTPException(status_code=404, detail="No professors found.")
    
    return [schemas.InstructorSearchResult.from_orm(i) for i in instructors]