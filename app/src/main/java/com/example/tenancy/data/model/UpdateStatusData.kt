package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 更新状态 - GET /api/update/status
 */
data class UpdateStatusData(
    @SerializedName("running") val running: Boolean,
    @SerializedName("last_run") val lastRun: String?,
    @SerializedName("last_result") val lastResult: String?,
    @SerializedName("last_crawl_log") val lastCrawlLog: CrawlLogItem?,
    @SerializedName("last_db_update") val lastDbUpdate: String?,
    @SerializedName("recent_24h") val recent24h: Recent24hStat?
)

data class CrawlLogItem(
    @SerializedName("source") val source: String?,
    @SerializedName("district") val district: String?,
    @SerializedName("houses_found") val housesFound: Int,
    @SerializedName("new_added") val newAdded: Int,
    @SerializedName("updated") val updated: Int,
    @SerializedName("status") val status: String?,
    @SerializedName("message") val message: String?,
    @SerializedName("crawl_time") val crawlTime: String?
)

data class Recent24hStat(
    @SerializedName("new") val newCount: Double,
    @SerializedName("updated") val updated: Double
)
