package com.example.tenancy.ui.filter

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.tenancy.data.model.HouseItem
import com.example.tenancy.data.remote.NetworkResult
import com.example.tenancy.data.repository.HouseRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class FilterUiState(
    val isLoading: Boolean = false,
    val houses: List<HouseItem> = emptyList(),
    val total: Int = 0,
    val currentPage: Int = 1,
    val pageSize: Int = 20,
    val error: String? = null,
    val isFirstLoad: Boolean = true,

    // 筛选条件
    val district: String? = null,
    val minPrice: Double? = null,
    val maxPrice: Double? = null,
    val minArea: Double? = null,
    val maxArea: Double? = null,
    val rooms: Int? = null,
    val floorType: String? = null,
    val decoration: String? = null,
    val orientation: String? = null,
    val source: String? = null
) {
    val totalPages: Int
        get() = if (total > 0 && pageSize > 0) (total + pageSize - 1) / pageSize else 0

    val hasNextPage: Boolean
        get() = currentPage < totalPages

    val hasPrevPage: Boolean
        get() = currentPage > 1
}

class FilterViewModel : ViewModel() {

    private val repository = HouseRepository()
    private val _uiState = MutableStateFlow(FilterUiState())
    val uiState: StateFlow<FilterUiState> = _uiState.asStateFlow()

    /**
     * 设置筛选条件
     */
    fun setFilter(
        district: String? = null,
        minPrice: Double? = null,
        maxPrice: Double? = null,
        minArea: Double? = null,
        maxArea: Double? = null,
        rooms: Int? = null,
        floorType: String? = null,
        decoration: String? = null,
        orientation: String? = null,
        source: String? = null
    ) {
        _uiState.value = _uiState.value.copy(
            district = if (district == "全部" || district == null) null else district,
            minPrice = minPrice,
            maxPrice = maxPrice,
            minArea = minArea,
            maxArea = maxArea,
            rooms = rooms,
            floorType = if (floorType == "全部" || floorType == null) null else floorType,
            decoration = if (decoration == "全部" || decoration == null) null else decoration,
            orientation = if (orientation == "全部" || orientation == null) null else orientation,
            source = if (source == "全部" || source == null) null else source
        )
    }

    fun setAreaFilter(minArea: Double? = null, maxArea: Double? = null,){
        _uiState.value = _uiState.value.copy(
            minArea=minArea,
            maxArea = maxArea
        )
    }
    //区县
    fun setDistrictFilter(district: String? = null){
        _uiState.value=_uiState.value.copy(
            district =if (district == "全部" || district == null) null else district
        )
    }
    //户型
    fun setRoomFilter(rooms: Int? = null,){
        _uiState.value=_uiState.value.copy(
            rooms=rooms
        )
    }
    //装修
    fun setDecorationFilter(decoration: String? = null){
        _uiState.value=_uiState.value.copy(
            decoration = if (decoration == "全部" || decoration == null) null else decoration,
        )
    }
    //朝向
    fun setOrientationFilter(orientation: String? = null,){
        _uiState.value=_uiState.value.copy(
            orientation = if (orientation == "全部" || orientation == null) null else orientation,
        )
    }
    //来源
    fun setSourceFilter(source: String? = null){
        _uiState.value=_uiState.value.copy(
            source = if (source == "全部" || source == null) null else source
        )
    }
    /**
     * 仅更新价格筛选，不改变其他条件
     */
    fun setPriceFilter(minPrice: Double?, maxPrice: Double?) {
        _uiState.value = _uiState.value.copy(
            minPrice = minPrice,
            maxPrice = maxPrice
        )
    }

    /**
     * 重置所有筛选条件
     */
    fun resetFilters() {
        _uiState.value = _uiState.value.copy(
            district = null,
            minPrice = null,
            maxPrice = null,
            minArea = null,
            maxArea = null,
            rooms = null,
            floorType = null,
            decoration = null,
            orientation = null,
            source = null,
            currentPage = 1
        )
    }

    /**
     * 执行搜索（从第1页开始）
     */
    fun search() {
        _uiState.value = _uiState.value.copy(currentPage = 1)
        loadHouses()
    }

    /**
     * 加载下一页（跳转）
     */
    fun nextPage() {
        val state = _uiState.value
        if (state.hasNextPage && !state.isLoading) {
            _uiState.value = state.copy(currentPage = state.currentPage + 1)
            loadHouses()
        }
    }

    /**
     * 加载上一页（跳转）
     */
    fun prevPage() {
        val state = _uiState.value
        if (state.hasPrevPage && !state.isLoading) {
            _uiState.value = state.copy(currentPage = state.currentPage - 1)
            loadHouses()
        }
    }

    /**
     * 加载更多（翻一页，追加到当前列表）
     */
    fun loadMore() {
        val state = _uiState.value
        if (state.hasNextPage && !state.isLoading) {
            _uiState.value = state.copy(currentPage = state.currentPage + 1)
            loadHouses()
        }
    }

    private fun loadHouses() {
        val state = _uiState.value
        _uiState.value = state.copy(isLoading = true, error = null)

        viewModelScope.launch {
            when (val result = repository.getHousesPage(
                district = state.district,
                minPrice = state.minPrice,
                maxPrice = state.maxPrice,
                minArea = state.minArea,
                maxArea = state.maxArea,
                rooms = state.rooms,
                floorType = state.floorType,
                decoration = state.decoration,
                orientation = state.orientation,
                source = state.source,
                page = state.currentPage,
                pageSize = state.pageSize
            )) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        houses = result.data.houses,
                        total = result.data.total,
                        isLoading = false,
                        isFirstLoad = false,
                        error = null
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.message
                    )
                }
                is NetworkResult.Loading -> {}
            }
        }
    }
}
