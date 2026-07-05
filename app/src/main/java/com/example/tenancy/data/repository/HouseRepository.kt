package com.example.tenancy.data.repository

import com.example.tenancy.data.model.*
import com.example.tenancy.data.remote.ApiService
import com.example.tenancy.data.remote.NetworkResult
import com.example.tenancy.data.remote.RetrofitClient
import com.example.tenancy.util.DistanceCalculator
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.sync.Semaphore


/**
 * 地图数据加载进度快照
 */
data class MapLoadProgress(
    val items: List<HouseItem>,
    val total: Int,
    val isCompleted: Boolean,
    val errorCount: Int = 0
)

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

    /**
     * 房源列表（分页，带 total 字段）
     */
    suspend fun getHousesPage(
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
    ): NetworkResult<HouseListPage> {
        return try {
            val response = api.getHouses(district, minPrice, maxPrice, minArea, maxArea, rooms, floorType, decoration, orientation, source, hasCoords, hasImages, page, pageSize)
            if ((response.code == 200 || response.code == 0) && response.data != null) {
                NetworkResult.Success(HouseListPage(response.data, response.total ?: 0))
            } else {
                NetworkResult.Error(response.code, response.message)
            }
        } catch (e: Exception) {
            NetworkResult.Error(-1, e.message ?: "未知网络错误")
        }
    }

    /**
     * 流式获取所有有坐标的房源（多页并发抓取 + 增量推送）
     */
    fun getAllHousesForMapFlow(): Flow<MapLoadProgress> = flow {
        // 第1步：请求第1页，拿到 total
        val firstResponse: ApiResponse<List<HouseItem>>
        try {
            firstResponse = api.getHouses(
                district = null,
                minPrice = null, maxPrice = null,
                minArea = null, maxArea = null,
                rooms = null, floorType = null,
                decoration = null, orientation = null,
                source = null,
                hasCoords = true, hasImages = null,
                page = 1, pageSize = 50
            )
        } catch (e: Exception) {
            emit(MapLoadProgress(emptyList(), 0, true))
            return@flow
        }

        if (firstResponse.code != 200 && firstResponse.code != 0) {
            emit(MapLoadProgress(emptyList(), 0, true))
            return@flow
        }

        val firstBatch = firstResponse.data ?: emptyList()
        val total = firstResponse.total ?: firstBatch.size

        // 立即推送第一批
        emit(MapLoadProgress(firstBatch, total, total <= firstBatch.size))
        if (total <= firstBatch.size) return@flow

        // 第2步：并发抓取剩余页，最多10页（约500条），每10个并发，每5页emit一次
        val totalPages = minOf((total + 49) / 50, 10)  // 最多取 10 页 (500 条)
        val allData = firstBatch.toMutableList()
        var errorCount = 0
        val semaphore = Semaphore(10)
        val channel = Channel<Pair<Boolean, List<HouseItem>>>(Channel.UNLIMITED)

        coroutineScope {
            for (page in 2..totalPages) {
                launch {
                    semaphore.acquire()
                    try {
                        val resp = api.getHouses(
                            district = null,
                            minPrice = null, maxPrice = null,
                            minArea = null, maxArea = null,
                            rooms = null, floorType = null,
                            decoration = null, orientation = null,
                            source = null,
                            hasCoords = true, hasImages = null,
                            page = page, pageSize = 50
                        )
                        if ((resp.code == 200 || resp.code == 0) && resp.data != null) {
                            channel.send(true to resp.data)
                        } else {
                            channel.send(false to emptyList())
                        }
                    } catch (e: Exception) {
                        channel.send(false to emptyList())
                    } finally {
                        semaphore.release()
                    }
                }
            }

            var completedPages = 0
            val totalRemaining = totalPages - 1
            repeat(totalRemaining) {
                val (success, data) = channel.receive()
                if (success) {
                    allData.addAll(data)
                } else {
                    errorCount++
                }
                completedPages++

                // 每收满5页或最后一页时emit
                if (completedPages % 5 == 0 || completedPages == totalRemaining) {
                    emit(MapLoadProgress(
                        items = allData.toList(),
                        total = total,
                        isCompleted = completedPages == totalRemaining,
                        errorCount = errorCount
                    ))
                }
            }
        }
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
