from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    phone_number: str = Field(..., json_schema_extra={"example": "09123456789"})
    full_name: str = Field(..., json_schema_extra={"example": "علی رضایی"})
    password: str = Field(..., min_length=6, json_schema_extra={"example": "password123"})
    role: Optional[str] = Field("SEEKER", json_schema_extra={"example": "SEEKER"})
    scholar_status: Optional[str] = "NONE"
    mosque_name: Optional[str] = None
    mosque_address: Optional[str] = None
    mosqueName: Optional[str] = None
    mosqueAddress: Optional[str] = None
    madhhab: Optional[str] = Field("شیعه اثناعشری", json_schema_extra={"example": "شیعه اثناعشری"})
    age: Optional[int] = None
    gender: Optional[str] = None
    education: Optional[str] = None
    interests: Optional[List[str]] = Field(default_factory=list)
    knowledge_level: Optional[str] = "GENERAL"
    learning_goals: Optional[str] = None
    avatar: Optional[str] = None


class UserLoginRequest(BaseModel):
    phone_number: str = Field(..., json_schema_extra={"example": "09123456789"})
    password: str = Field(..., json_schema_extra={"example": "password123"})


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user_id: str
    role: str
    full_name: str
    scholar_status: Optional[str] = "NONE"
    scholarStatus: Optional[str] = "NONE"
    mosque_name: Optional[str] = None
    mosque_address: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str
    phone_number: str
    full_name: str
    role: str
    scholar_status: Optional[str] = "NONE"
    scholarStatus: Optional[str] = "NONE"
    mosque_name: Optional[str] = None
    mosque_address: Optional[str] = None
    madhhab: str
    age: Optional[int] = None
    gender: Optional[str] = None
    education: Optional[str] = None
    interests: List[str] = []
    knowledgeLevel: str = "GENERAL"
    learningGoals: Optional[str] = None
    avatar: Optional[str] = None


class UpdateUserProfileRequest(BaseModel):
    fullName: Optional[str] = None
    madhhab: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    education: Optional[str] = None
    interests: Optional[List[str]] = None
    knowledgeLevel: Optional[str] = None  # GENERAL, ACADEMIC, SEMINARY
    learningGoals: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None
    scholarStatus: Optional[str] = None
    mosqueName: Optional[str] = None
    mosqueAddress: Optional[str] = None


class InterestCategoryDTO(BaseModel):
    id: str
    title: str
    description: str
    iconName: str
    isPrimary: bool = False


class BotRolePresetDTO(BaseModel):
    key: str
    title: str
    description: str
    defaultTone: str
    defaultAvatar: Optional[str] = None
    systemRoleDescription: str


class AvailableInterestsAndPresetsResponse(BaseModel):
    interestCategories: List[InterestCategoryDTO]
    knowledgeLevels: List[Dict[str, str]]
    educationLevels: List[str]
    genders: List[Dict[str, str]]
    botRolePresets: List[BotRolePresetDTO]


class SendOtpRequest(BaseModel):
    phone_number: str = Field(..., json_schema_extra={"example": "09123456789"})


class VerifyOtpRequest(BaseModel):
    phone_number: str = Field(..., json_schema_extra={"example": "09123456789"})
    code: str = Field(..., min_length=4, max_length=8, json_schema_extra={"example": "12345"})

