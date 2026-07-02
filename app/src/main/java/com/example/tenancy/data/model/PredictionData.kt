package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 房价预测 v2 - models / feature_importance / created_at
 */
data class PredictionData(
    @SerializedName("models") val models: Map<String, ModelInfo>?,
    @SerializedName("feature_importance") val featureImportance: Map<String, List<FeatureRank>>?,
    @SerializedName("created_at") val createdAt: String?
)

data class ModelInfo(
    @SerializedName("unit") val unit: String?,
    @SerializedName("target") val target: String?,
    @SerializedName("model_type") val modelType: String?,
    @SerializedName("test_r2") val testR2: Double?,
    @SerializedName("test_mae") val testMae: Double?,
    @SerializedName("test_rmse") val testRmse: Double?,
    @SerializedName("cv_r2_mean") val cvR2Mean: Double?
)

data class FeatureRank(
    @SerializedName("rank") val rank: Int,
    @SerializedName("feature") val feature: String,
    @SerializedName("feature_cn") val featureCn: String,
    @SerializedName("importance") val importance: Double
)
