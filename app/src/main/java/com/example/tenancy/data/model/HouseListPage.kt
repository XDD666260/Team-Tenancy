package com.example.tenancy.data.model

/**
 * 房源列表分页结果
 */
data class HouseListPage(
    val houses: List<HouseItem>,
    val total: Int
)
