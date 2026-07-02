package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 首页数据总览 - 新API
 */
data class OverviewData(
    @SerializedName("total_houses") val totalHouses: Int,
    @SerializedName("avg_unit_price") val avgUnitPrice: Double,
    @SerializedName("avg_total_price") val avgTotalPrice: Double,
    @SerializedName("max_unit_price") val maxUnitPrice: Double,
    @SerializedName("min_unit_price") val minUnitPrice: Double,
    @SerializedName("district_count") val districtCount: Int,
    @SerializedName("update_time") val updateTime: String,
    @SerializedName("by_source") val bySource: Map<String, Int>,
    @SerializedName("by_district") val byDistrict: List<DistrictStat>
)

data class DistrictStat(
    @SerializedName("district") val district: String,
    @SerializedName("count") val count: Int,
    @SerializedName("avg_unit_price") val avgUnitPrice: Double,
    @SerializedName("avg_total_price") val avgTotalPrice: Double
)
