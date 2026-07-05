package com.example.tenancy.ui.map

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.tenancy.data.model.HouseItem
import com.example.tenancy.data.remote.NetworkResult
import com.example.tenancy.data.repository.HouseRepository
import com.example.tenancy.data.repository.MapLoadProgress
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PointData(
    val lng: Double,
    val lat: Double,
    val count: Int = 1,
    val title: String?,
    val community: String?,
    val district: String?,
    @SerializedName("total_price") val totalPrice: Double?,
    @SerializedName("unit_price") val unitPrice: Double?,
    val area: Double?,
    val layout: String?
)

data class MapUiState(
    val isLoading: Boolean = false,
    val pointsJson: String = "[]",
    val districtsJson: String = "[]",
    val selectedDistrict: String? = null,
    val totalCount: Int = 0,
    val coordinateCount: Int = 0,
    val districts: List<String> = emptyList(),
    val error: String? = null
)

class MapViewModel : ViewModel() {

    companion object {
        private const val MAX_MAP_POINTS = 500
    }

    private val repository = HouseRepository()
    private val gson = Gson()

    private val _uiState = MutableStateFlow(MapUiState())
    val uiState: StateFlow<MapUiState> = _uiState.asStateFlow()

    private var accumulatedItems: List<HouseItem> = emptyList()
    private var accumulatedDistricts: List<String> = emptyList()
    private var accumulatedSelectedDistrict: String? = null

    init {
        loadHouses()
    }

    fun loadHouses() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)

            repository.getAllHousesForMapFlow().collect { progress ->
                accumulatedItems = progress.items

                if (accumulatedDistricts.isEmpty()) {
                    accumulatedDistricts = progress.items.mapNotNull { it.district }
                        .filter { it.isNotBlank() }
                        .distinct()
                        .sorted()
                }

                val points = progress.items
                    .filter { it.lng != null && it.lat != null && it.lng!!.isFinite() && it.lat!!.isFinite() }
                    .map { h ->
                        PointData(
                            lng = h.lng!!,
                            lat = h.lat!!,
                            title = h.title,
                            community = h.community,
                            district = h.district,
                            totalPrice = h.totalPrice,
                            unitPrice = h.unitPrice,
                            area = h.area,
                            layout = h.layout
                        )
                    }

                val displayPoints = (if (accumulatedSelectedDistrict.isNullOrBlank()) {
                    points
                } else {
                    points.filter { it.district == accumulatedSelectedDistrict }
                }).take(MAX_MAP_POINTS)

                _uiState.value = _uiState.value.copy(
                    isLoading = !progress.isCompleted,
                    pointsJson = gson.toJson(displayPoints),
                    districtsJson = gson.toJson(accumulatedDistricts),
                    districts = accumulatedDistricts,
                    selectedDistrict = accumulatedSelectedDistrict,
                    totalCount = minOf(displayPoints.size, MAX_MAP_POINTS),
                    coordinateCount = minOf(displayPoints.size, MAX_MAP_POINTS)
                )
            }
        }
    }

    fun filterByDistrict(district: String?) {
        accumulatedSelectedDistrict = district
        val filtered = if (district.isNullOrBlank()) {
            accumulatedItems
        } else {
            accumulatedItems.filter { it.district == district }
        }
        val points = filtered
            .filter { it.lng != null && it.lat != null && it.lng!!.isFinite() && it.lat!!.isFinite() }
            .map { h ->
                PointData(
                    lng = h.lng!!,
                    lat = h.lat!!,
                    title = h.title,
                    community = h.community,
                    district = h.district,
                    totalPrice = h.totalPrice,
                    unitPrice = h.unitPrice,
                    area = h.area,
                    layout = h.layout
                )
            }
            .take(MAX_MAP_POINTS)
        _uiState.value = _uiState.value.copy(
            selectedDistrict = district,
            pointsJson = gson.toJson(points),
            totalCount = minOf(points.size, MAX_MAP_POINTS),
            coordinateCount = minOf(points.size, MAX_MAP_POINTS)
        )
    }
}