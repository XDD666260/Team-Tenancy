package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 聚类分析 v2 - clustering / created_at
 */
data class ClusteringData(
    @SerializedName("clustering") val clustering: ClusteringResult?,
    @SerializedName("created_at") val createdAt: String?
)

data class ClusteringResult(
    @SerializedName("n_clusters") val nClusters: Int,
    @SerializedName("silhouette_score") val silhouetteScore: Double,
    @SerializedName("cluster_stats") val clusterStats: List<ClusterStat>
)

data class ClusterStat(
    @SerializedName("cluster_id") val clusterId: Int,
    @SerializedName("count") val count: Int,
    @SerializedName("pct") val pct: Double,
    @SerializedName("avg_unit_price") val avgUnitPrice: Double,
    @SerializedName("avg_total_price") val avgTotalPrice: Double,
    @SerializedName("avg_area") val avgArea: Double,
    @SerializedName("avg_rooms") val avgRooms: Double,
    @SerializedName("avg_house_age") val avgHouseAge: Double,
    @SerializedName("dominant_floor") val dominantFloor: String?,
    @SerializedName("dominant_decoration") val dominantDecoration: String?,
    @SerializedName("top_districts") val topDistricts: Map<String, Int>?
)
