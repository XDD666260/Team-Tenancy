package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 更新历史记录项 - GET /api/update/history
 */
data class UpdateHistoryItem(
    @SerializedName("id") val id: Int,
    @SerializedName("source") val source: String?,
    @SerializedName("district") val district: String?,
    @SerializedName("page") val page: Int?,
    @SerializedName("houses_found") val housesFound: Int,
    @SerializedName("new_added") val newAdded: Int,
    @SerializedName("updated") val updated: Int,
    @SerializedName("status") val status: String?,
    @SerializedName("message") val message: String?,
    @SerializedName("crawl_time") val crawlTime: String?
)
