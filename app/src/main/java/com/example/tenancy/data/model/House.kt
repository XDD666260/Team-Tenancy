package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 房源信息 - 新API
 */
data class HouseItem(
    @SerializedName("id") val id: Int,
    @SerializedName("title") val title: String?,
    @SerializedName("district") val district: String?,
    @SerializedName("community") val community: String?,
    @SerializedName("address") val address: String?,
    @SerializedName("total_price") val totalPrice: Double?,
    @SerializedName("unit_price") val unitPrice: Double?,
    @SerializedName("area") val area: Double?,
    @SerializedName("layout") val layout: String?,
    @SerializedName("rooms") val rooms: Int?,
    @SerializedName("halls") val halls: Int?,
    @SerializedName("bathrooms") val bathrooms: Int?,
    @SerializedName("floor_desc") val floorDesc: String?,
    @SerializedName("floor_type") val floorType: String?,
    @SerializedName("total_floors") val totalFloors: Int?,
    @SerializedName("orientation") val orientation: String?,
    @SerializedName("decoration") val decoration: String?,
    @SerializedName("build_year") val buildYear: Int?,
    @SerializedName("lng") val lng: Double?,
    @SerializedName("lat") val lat: Double?,
    @SerializedName("source") val source: String?,
    @SerializedName("has_coords") val hasCoords: Boolean?,
    @SerializedName("has_images") val hasImages: Boolean?
)
