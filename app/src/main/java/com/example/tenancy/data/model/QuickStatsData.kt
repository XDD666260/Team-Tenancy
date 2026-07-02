package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 快速统计摘要 - GET /api/analysis/quick-stats
 */
data class QuickStatsData(
    @SerializedName("total_listings") val totalListings: Int,
    @SerializedName("avg_unit_price") val avgUnitPrice: Double,
    @SerializedName("avg_total_price") val avgTotalPrice: Double,
    @SerializedName("avg_area") val avgArea: Double,
    @SerializedName("avg_build_year") val avgBuildYear: Double,
    @SerializedName("decoration_distribution") val decorationDistribution: List<NameCount>?,
    @SerializedName("floor_distribution") val floorDistribution: List<NameCount>?
)

data class NameCount(
    @SerializedName("name") val name: String,
    @SerializedName("count") val count: Int
)
