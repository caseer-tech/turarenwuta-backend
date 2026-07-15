from pydantic import BaseModel, EmailStr, Field
from typing import Literal


class CheckoutInitRequest(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    phone: str = Field(min_length=10)
    payment_method: Literal["card", "bank_transfer"]


class CheckoutInitResponse(BaseModel):
    ticket_ref: str
    authorization_url: str


class CapacityResponse(BaseModel):
    capacity: int
    sold: int
    remaining: int
    sold_out: bool


class TicketStatusResponse(BaseModel):
    ticket_ref: str
    payment_status: Literal["pending", "paid", "failed"]
    name: str


class CheckinRequest(BaseModel):
    ticket_ref: str
    token: str


class CheckinResponse(BaseModel):
    valid: bool
    already_checked_in: bool
    name: str | None = None
    message: str
