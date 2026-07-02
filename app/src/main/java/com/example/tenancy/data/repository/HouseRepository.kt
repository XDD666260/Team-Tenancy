package com.example.tenancy.data.repository

import com.example.tenancy.data.model.*
import com.example.tenancy.data.remote.ApiService
import com.example.tenancy.data.remote.NetworkResult
import com.example.tenancy.data.remote.RetrofitClient
import com.example.tenancy.util.DistanceCalculator

/**
 * 房源数据仓库
 * 负责协调网络数据源，统一处理API响应
 */
class HouseRepository {

    private val api: ApiService = RetrofitClient.apiService

    private suspend fun <T> safeApiCall(call: suspend () -> ApiResponse<T>): NetworkResult<T> {
        return try {
            val response = call()
            if ((response.code == 200 || response.code == 0) && response.data != null) {
                NetworkResult.Success(response.data)
            } else {
                NetworkResult.Error(response.code, response.message)
            }
        } catch (e: Exception) {
            NetworkResult.Error(-1, e.message ?: "未知网络错误")
        }
    }

    /** 首页概览统计 */
    suspend fun getOverview(): NetworkResult<OverviewData> =
        safeApiCall { api.getOverview() }

    /** 房源列表 */
    suspend fun getHouses(
        district: String? = null,
        minPrice: Double? = null,
        maxPrice: Double? = null,
        minArea: Double? = null,
        maxArea: Double? = null,
        rooms: Int? = null,
        floorType: String? = null,
        decoration: String? = null,
        orientation: String? = null,
        source: String? = null,
        hasCoords: Boolean? = null,
        hasImages: Boolean? = null,
        page: Int = 1,
        pageSize: Int = 20
    ): NetworkResult<List<HouseItem>> =
        safeApiCall {
            api.getHouses(district, minPrice, maxPrice, minArea, maxArea, rooms, floorType, decoration, orientation, source, hasCoords, hasImages, page, pageSize)
        }

    /** 房源详情 */
    suspend fun getHouseDetail(houseId: Int): NetworkResult<HouseItem> =
        safeApiCall { api.getHouseDetail(houseId) }

    /** 区县详细统计 */
    suspend fun getDistrictStats(districtName: String): NetworkResult<DistrictStats> =
        safeApiCall { api.getDistrictStats(districtName) }

    /** 价格分布 */
    suspend fun getPriceDistribution(): NetworkResult<PriceDistribution> =
        safeApiCall { api.getPriceDistribution() }

    /** 户型分布 */
    suspend fun getLayoutDistribution(): NetworkResult<LayoutDistribution> =
        safeApiCall { api.getLayoutDistribution() }

    /** 面积分布 */
    suspend fun getAreaDistribution(): NetworkResult<AreaDistribution> =
        safeApiCall { api.getAreaDistribution() }

    /** 房价预测 (v2实测通过) */
    suspend fun getPrediction(): NetworkResult<PredictionData> =
        safeApiCall { api.getPrediction() }

    /** 聚类分析 (v2实测通过) */
    suspend fun getClustering(): NetworkResult<ClusteringData> =
        safeApiCall { api.getClustering() }

    /** 关联规则 (v2实测通过) */
    suspend fun getRules(): NetworkResult<RulesData> =
        safeApiCall { api.getRules() }

    /** 快速统计摘要 (v2新增) */
    suspend fun getQuickStats(): NetworkResult<QuickStatsData> =
        safeApiCall { api.getQuickStats() }

    /** 触发增量更新 */
    suspend fun triggerUpdate(): NetworkResult<Any> =
        safeApiCall { api.triggerUpdate() }

    /** 更新状态 (v2新增) */
    suspend fun getUpdateStatus(): NetworkResult<UpdateStatusData> =
        safeApiCall { api.getUpdateStatus() }

    /** 更新历史 (v2新增) */
    suspend fun getUpdateHistory(): NetworkResult<List<UpdateHistoryItem>> =
        safeApiCall { api.getUpdateHistory() }

    /** 获取所有房源（用于地图，不带任何筛选条件） */
    suspend fun getAllHousesForMap(): NetworkResult<List<HouseItem>> =
        safeApiCall {
            api.getHouses(
                district = null,
                minPrice = null, maxPrice = null,
                minArea = null, maxArea = null,
                rooms = null, floorType = null,
                decoration = null, orientation = null,
                source = null,
                hasCoords = true, hasImages = null,
                page = 1, pageSize = 50
            )
        }

    /**
     * 获取房源列表并按距离排序（离用户最近的排最前）
     */
    suspend fun getHousesSortedByDistance(
        userLat: Double,
        userLng: Double,
        maxDistanceKm: Double? = null,
        page: Int = 1,
        pageSize: Int = 20
    ): NetworkResult<List<HouseWithDistance>> {
        val result = getHouses(page = page, pageSize = pageSize)
        if (result !is NetworkResult.Success) {
            @Suppress("UNCHECKED_CAST")
            return result as NetworkResult<List<HouseWithDistance>>
        }
        val houses = result.data
            .map { house ->
            val lng = house.lng ?: 0.0
            val lat = house.lat ?: 0.0
            val distance = DistanceCalculator.distanceBetween(
                userLat, userLng, lat, lng
            )
            HouseWithDistance(
                house = house,
                distanceMeters = distance,
                distanceText = DistanceCalculator.formatDistance(distance)
            )
        }.let { list ->
            if (maxDistanceKm != null) {
                list.filter { it.distanceMeters <= maxDistanceKm * 1000 }
            } else list
        }.sortedBy { it.distanceMeters }

        return NetworkResult.Success(houses)
    }
}