package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 价格分布 - 新API: unit_price_bins (6级) + total_price_bins (6级)
 */
data class PriceDistribution(
    @SerializedName("unit_price_bins") val unitPriceBins: List<PriceBin>?,
    @SerializedName("total_price_bins") val totalPriceBins: List<PriceBin>?
)

data class PriceBin(
    @SerializedName("range") val range: String?,
    @SerializedName("count") val count: Int
)
