package com.example.tenancy.data.remote

import com.example.tenancy.data.model.*
import retrofit2.http.*

/**
 * API接口定义 - 14个端点 (v2实测版)
 */
interface ApiService {

    // 1. 首页概览统计
    @GET("api/stats/overview")
    suspend fun getOverview(): ApiResponse<OverviewData>

    // 2. 房源列表（支持筛选+分页）
    @GET("api/houses")
    suspend fun getHouses(
        @Query("district") district: String? = null,
        @Query("min_price") minPrice: Double? = null,
        @Query("max_price") maxPrice: Double? = null,
        @Query("min_area") minArea: Double? = null,
        @Query("max_area") maxArea: Double? = null,
        @Query("rooms") rooms: Int? = null,
        @Query("floor_type") floorType: String? = null,
        @Query("decoration") decoration: String? = null,
        @Query("orientation") orientation: String? = null,
        @Query("source") source: String? = null,
        @Query("has_coords") hasCoords: Boolean? = true,
        @Query("has_images") hasImages: Boolean? = true,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): ApiResponse<List<HouseItem>>

    // 3. 房源详情
    @GET("api/houses/{id}")
    suspend fun getHouseDetail(
        @Path("id") houseId: Int
    ): ApiResponse<HouseItem>

    // 4. 区县详细统计
    @GET("api/stats/district/{name}")
    suspend fun getDistrictStats(
        @Path("name") districtName: String
    ): ApiResponse<DistrictStats>

    // 5. 价格分布统计
    @GET("api/stats/price-distribution")
    suspend fun getPriceDistribution(): ApiResponse<PriceDistribution>

    // 6. 户型分布统计
    @GET("api/stats/layout-distribution")
    suspend fun getLayoutDistribution(): ApiResponse<LayoutDistribution>

    // 7. 面积分布统计
    @GET("api/stats/area-distribution")
    suspend fun getAreaDistribution(): ApiResponse<AreaDistribution>

    // 8. 房价预测分析 (v2实测通过)
    @GET("api/analysis/prediction")
    suspend fun getPrediction(): ApiResponse<PredictionData>

    // 9. 聚类分析 (v2实测通过)
    @GET("api/analysis/clustering")
    suspend fun getClustering(): ApiResponse<ClusteringData>

    // 10. 关联规则分析 (v2实测通过)
    @GET("api/analysis/rules")
    suspend fun getRules(): ApiResponse<RulesData>

    // 11. 快速统计摘要 (v2新增)
    @GET("api/analysis/quick-stats")
    suspend fun getQuickStats(): ApiResponse<QuickStatsData>

    // 12. 触发增量更新
    @POST("api/update")
    suspend fun triggerUpdate(): ApiResponse<Any>

    // 13. 更新状态 (v2新增)
    @GET("api/update/status")
    suspend fun getUpdateStatus(): ApiResponse<UpdateStatusData>

    // 14. 更新历史 (v2新增)
    @GET("api/update/history")
    suspend fun getUpdateHistory(): ApiResponse<List<UpdateHistoryItem>>
}
