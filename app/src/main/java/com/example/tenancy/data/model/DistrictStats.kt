package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 区县详细统计 v2
 */
data class DistrictStats(
    @SerializedName("house_count") val houseCount: Int,
    @SerializedName("avg_unit_price") val avgUnitPrice: Double,
    @SerializedName("avg_total_price") val avgTotalPrice: Double,
    @SerializedName("avg_area") val avgArea: Double,
    @SerializedName("max_price") val maxPrice: Double,
    @SerializedName("min_price") val minPrice: Double,
    @SerializedName("decoration_distribution") val decorationDistribution: List<DecorationDist>?,
    @SerializedName("layout_distribution") val layoutDistribution: List<LayoutDist>?,
    @SerializedName("price_distribution") val priceDistribution: List<PriceDist>?,
    @SerializedName("area_distribution") val areaDistribution: List<AreaDist>?,
    @SerializedName("top_communities") val topCommunities: List<CommunityItem>?
)

data class DecorationDist(
    @SerializedName("type") val type: String?,
    @SerializedName("count") val count: Int
)

data class LayoutDist(
    @SerializedName("rooms") val rooms: Int,
    @SerializedName("count") val count: Int
)

data class PriceDist(
    @SerializedName("range") val range: String?,
    @SerializedName("count") val count: Int
)

data class AreaDist(
    @SerializedName("range") val range: String?,
    @SerializedName("count") val count: Int
)

data class CommunityItem(
    @SerializedName("name") val name: String?,
    @SerializedName("count") val count: Int,
    @SerializedName("avg_price") val avgPrice: Double
)
