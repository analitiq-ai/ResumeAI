from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

class SocialNetwork(BaseModel):
    network: str
    username: str

class HighlightEntry(BaseModel):
    highlights: List[str]

class EducationEntry(HighlightEntry):
    institution: str
    area: str
    degree: str
    location: str
    start_date: str  # Format: YYYY-MM
    end_date: Optional[str]  # 'present' can be used

class ExperienceEntry(HighlightEntry):
    company: str
    position: str
    location: str
    start_date: str
    end_date: Optional[str]

class ProjectEntry(HighlightEntry):
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date: Optional[str] = None
    summary: Optional[str] = None

class SkillEntry(BaseModel):
    label: str
    details: str

class PublicationEntry(BaseModel):
    title: str
    authors: List[str]
    doi: Optional[str] = None
    date: str  # Format: YYYY-MM

class ExtracurricularActivity(BaseModel):
    bullet: str

class ResumeSections(BaseModel):
    summary: List[str]
    education: List[EducationEntry]
    experience: List[ExperienceEntry]
    projects: List[ProjectEntry]
    skills: List[SkillEntry]
    publications: List[PublicationEntry]
    extracurricular_activities: List[ExtracurricularActivity]

class Resume(BaseModel):
    name: str
    location: str
    email: EmailStr
    phone: str
    social_networks: Optional[List[SocialNetwork]] = None
    sections: ResumeSections

class CVRoot(BaseModel):
    cv: Resume

class ResumeJobMatchScore(BaseModel):
    old_resume_match_score: float = Field(..., description="Score indicating how well the old resume matches the job description, ranging from 0 to 1 as a float.")
    new_resume_match_score: float = Field(..., description="Score indicating how well the new resume matches the job description, ranging from 0 to 1 as a float.")
    description: float = Field(..., description="Add here any evaluation text that you feel is important.")

class UserJobMatchScore(BaseModel):
    job_positives: str = Field(..., description="Short list of explicitly mentioned job properties that match users requirements. Do not include ")
    job_negatives: str = Field(..., description="Short list of explicitly mentioned job properties that do not match users requirements.")
    job_to_req_match_score: float = Field(..., description="Score indicating how well the job matches the user requirements, ranging from 0 to 1 as a float.")

class JobRequirements(BaseModel):
    job_requirements: str = Field(..., description="A summary of key job requirements extrapolated from the job description.")
    sentence_keywords: List[str] = Field(..., description="A list of keywords that are extracted from the job description.")

class ResumeImprovements(BaseModel):
    resume_improvements: List[str] = Field(..., description="A summary of improvements that can be made to the resume based on the job description.")
