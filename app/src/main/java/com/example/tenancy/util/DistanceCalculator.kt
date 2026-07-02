package com.example.tenancy.util

import android.location.Location

/**
 * 距离计算工具类
 */
object DistanceCalculator {

    /**
     * 计算两点间的距离（米）
     * 使用Android原生 Location.distanceTo，基于WGS84椭球体
     */
    fun distanceBetween(
        lat1: Double, lng1: Double,
        lat2: Double, lng2: Double
    ): Float {
        val results = FloatArray(1)
        Location.distanceBetween(lat1, lng1, lat2, lng2, results)
        return results[0]
    }

    /**
     * 格式化距离显示
     * < 1km 显示 "XXXm"
     * >= 1km 显示 "X.Xkm"
     */
    fun formatDistance(distanceMeters: Float): String {
        return when {
            distanceMeters < 1000 -> "${distanceMeters.toInt()}m"
            else -> String.format("%.1fkm", distanceMeters / 1000)
        }
    }
}
