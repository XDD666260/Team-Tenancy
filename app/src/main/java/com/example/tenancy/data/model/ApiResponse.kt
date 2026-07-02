package com.example.tenancy.data.model

import com.google.gson.annotations.SerializedName

/**
 * 统一API响应包装
 */
data class ApiResponse<T>(
    @SerializedName("code") val code: Int,
    @SerializedName("message") val message: String,
    @SerializedName("data") val data: T?,
    @SerializedName("total") val total: Int? = null
)
