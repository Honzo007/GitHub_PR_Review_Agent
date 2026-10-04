from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class Finding(BaseModel):
    """One issue. Every finding from the AI must have exactly this shape."""
    file: str
    line: int = 1
    severity: Literal["critical", "high", "medium", "low"]
    title: str
    explanation: str
    fix: str

    @field_validator("severity", mode="before")
    @classmethod
    def clean_severity(cls, value):
        return str(value).strip().lower()      # 'HIGH' becomes 'high'

    @field_validator("line", mode="before")
    @classmethod
    def clean_line(cls, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 1


class AnalysisResult(BaseModel):
    findings: List[Finding] = Field(default_factory=list)
