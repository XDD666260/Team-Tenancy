package com.example.tenancy.data.model

/**
 * 带距离信息的房源数据
 */
data class HouseWithDistance(
    val house: HouseItem,
    val distanceMeters: Float,
    val distanceText: String
)
