package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 户型分布 v2 - rooms_distribution + avg_price_by_rooms (rooms字段为Int)
 */
data class LayoutDistribution(
    @SerializedName("rooms_distribution") val roomsDistribution: List<RoomsDist>?,
    @SerializedName("avg_price_by_rooms") val avgPriceByRooms: List<AvgPriceByRooms>?
)

data class RoomsDist(
    @SerializedName("rooms") val rooms: Int,
    @SerializedName("count") val count: Int
)

data class AvgPriceByRooms(
    @SerializedName("rooms") val rooms: Int,
    @SerializedName("avg_unit_price") val avgUnitPrice: Double
)
