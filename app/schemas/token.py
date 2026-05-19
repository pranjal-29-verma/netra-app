from pydantic import BaseModel


class TokenUsageResponse(BaseModel):
    tokens_used: int
    daily_quota: int
    remaining: int
    usage_percentage: float
    total_tokens_used: int

    class Config:
        from_attributes = True
