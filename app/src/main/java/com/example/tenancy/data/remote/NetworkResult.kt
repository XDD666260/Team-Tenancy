package com.example.tenancy.data.remote

/**
 * 网络请求结果封装
 * Success - 请求成功，携带数据
 * Error - 请求失败，携带错误信息
 * Loading - 请求中
 */
sealed class NetworkResult<out T> {
    data class Success<T>(val data: T) : NetworkResult<T>()
    data class Error(val code: Int, val message: String) : NetworkResult<Nothing>()
    data object Loading : NetworkResult<Nothing>()
}
