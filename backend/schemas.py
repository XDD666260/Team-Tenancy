"""Pydantic 模型定义"""
from typing import Optional, Any
from pydantic import BaseModel


class APIResponse(BaseModel):
    """统一响应格式"""
    code: int = 200
    message: str = "success"
    data: Any = None
    total: Optional[int] = None


class HouseItem(BaseModel):
    """房源条目"""
    id: int
    title: Optional[str] = None
    district: Optional[str] = None
    community: Optional[str] = None
    address: Optional[str] = None
    total_price: Optional[float] = None
    unit_price: Optional[float] = None
    area: Optional[float] = None
    layout: Optional[str] = None
    rooms: Optional[int] = None
    halls: Optional[int] = None
    bathrooms: Optional[int] = None
    floor_desc: Optional[str] = None
    floor_type: Optional[str] = None
    total_floors: Optional[int] = None
    orientation: Optional[str] = None
    decoration: Optional[str] = None
    build_year: Optional[int] = None
    lng: Optional[float] = None
    lat: Optional[float] = None
    source: Optional[str] = None
