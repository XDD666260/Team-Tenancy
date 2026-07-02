package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 面积分布 - 新API: bins (5级: 60以下~150以上)
 */
data class AreaDistribution(
    @SerializedName("bins") val bins: List<AreaBin>?
)

data class AreaBin(
    @SerializedName("range") val range: String?,
    @SerializedName("count") val count: Int
)
