package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 关联规则 v2 - association / district_analysis / created_at
 */
data class RulesData(
    @SerializedName("association") val association: AssociationResult?,
    @SerializedName("district_analysis") val districtAnalysis: DistrictAnalysisResult?,
    @SerializedName("created_at") val createdAt: String?
)

data class AssociationResult(
    @SerializedName("conclusions") val conclusions: String?,
    @SerializedName("total_rules") val totalRules: Int
)

data class DistrictAnalysisResult(
    @SerializedName("chart") val chart: String?,
    @SerializedName("top20_avg_price") val top20AvgPrice: Map<String, Map<String, Double>>?
)
