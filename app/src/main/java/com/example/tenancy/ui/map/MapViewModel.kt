package com.example.tenancy.ui.map

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.tenancy.data.remote.NetworkResult
import com.example.tenancy.data.repository.HouseRepository
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

    private val repository = HouseRepository()
    private val gson = Gson()

    private val _uiState = MutableStateFlow(MapUiState())
    val uiState: StateFlow<MapUiState> = _uiState.asStateFlow()

    private var allPoints: List<PointData> = emptyList()
    private var allDistricts: List<String> = emptyList()

    init {
        loadHouses()
    }

    fun loadHouses() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)

            // 使用专门的地图接口，不传任何过滤参数
            val result = repository.getAllHousesForMap()
            when (result) {
                is NetworkResult.Success -> {
                    val houses = result.data

                    allDistricts = houses.mapNotNull { it.district }
                        .filter { it.isNotBlank() }
                        .distinct()
                        .sorted()

                    allPoints = houses
                        .filter { (it.lng ?: 0.0) > 0.0 && (it.lat ?: 0.0) > 0.0 }
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

                    val json = gson.toJson(allPoints)
                    val districtsJson = gson.toJson(allDistricts)

                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        pointsJson = gson.toJson(allPoints),
                        districtsJson = gson.toJson(allDistricts),
                        districts = allDistricts,
                        totalCount = houses.size,
                        coordinateCount = allPoints.size
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = result.message ?: "HTTP ${result.code}"
                    )
                }
                else -> {
                    _uiState.value = _uiState.value.copy(isLoading = false)
                }
            }
        }
    }

    fun filterByDistrict(district: String?) {
        val filtered = if (district.isNullOrBlank()) {
            allPoints
        } else {
            allPoints.filter { it.district == district }
        }
        _uiState.value = _uiState.value.copy(
            selectedDistrict = district,
            pointsJson = gson.toJson(filtered)
        )
    }
}