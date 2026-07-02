package com.example.tenancy.ui.home

import android.app.Application
import android.location.Address
import android.location.Geocoder
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.tenancy.data.model.HouseItem
import com.example.tenancy.data.model.HouseWithDistance
import com.example.tenancy.data.model.OverviewData
import com.example.tenancy.data.model.DistrictStat
import com.example.tenancy.data.remote.NetworkResult
import com.example.tenancy.data.repository.HouseRepository
import com.example.tenancy.util.LocationHelper
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import java.util.Locale

data class HomeUiState(
    val isLoading: Boolean = false,
    val locationText: String = "Locating\u2026",
    val userLat: Double = 0.0,
    val userLng: Double = 0.0,
    val isLocating: Boolean = true,
    val locationError: String? = null,
    val nearbyHouses: List<HouseWithDistance> = emptyList(),
    val recommendHouses: List<HouseItem> = emptyList(),
    val error: String? = null,
    val overviewData: OverviewData? = null,
    val isOverviewLoading: Boolean = false
)

class HomeViewModel(application: Application) : AndroidViewModel(application) {

    private val TAG = "HomeViewModel"
    private val repository = HouseRepository()

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    /** 权限被拒，直接用默认位置加载数据 */
    fun loadWithDefaultLocation() {
        val defaultLat = 39.9042
        val defaultLng = 116.4074
        Log.d(TAG, "loadWithDefaultLocation: lat=defaultLat, lng=defaultLng")
        _uiState.value = _uiState.value.copy(
            isLoading = true,
            locationText = "Beijing \u00b7 Dongcheng District",
            userLat = defaultLat,
            userLng = defaultLng,
            isLocating = false,
            error = null
        )
        loadHouseData(defaultLat, defaultLng)
    }

    /** 先获取GPS定位，再用真实坐标加载数据 */
    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                isLoading = true,
                isLocating = true,
                error = null
            )
            Log.d(TAG, "refresh: starting location fetch")

            // 先获取定位
            val (lat, lng, addressText) = fetchLocation()
            _uiState.value = _uiState.value.copy(
                userLat = lat,
                userLng = lng,
                locationText = addressText,
                isLocating = false
            )
            Log.d(TAG, "refresh: location -> $addressText ($lat, $lng)")

            // 用真实坐标加载房源数据
            fetchHouseData(lat, lng)
        }
    }

    /** 获取定位，失败时返回默认北京坐标 */
    private suspend fun fetchLocation(): Triple<Double, Double, String> {
        val location = withTimeoutOrNull(15_000L) {
            try {
                LocationHelper.getCurrentLocation(getApplication())
            } catch (e: SecurityException) {
                Log.w(TAG, "fetchLocation: SecurityException", e)
                null
            } catch (e: Exception) {
                Log.w(TAG, "fetchLocation: ${e.message}", e)
                null
            }
        } ?: run { Log.d(TAG, "fetchLocation: timed out"); null }

        return if (location != null) {
            val lat = location.latitude
            val lng = location.longitude
            val address = withTimeoutOrNull(5_000L) {
                withContext(Dispatchers.IO) { getAddressFromLocation(lat, lng) }
            } ?: String.format(Locale.getDefault(), "%.4f, %.4f", lat, lng)
            Triple(lat, lng, address)
        } else {
            Triple(39.9042, 116.4074, "Beijing \u00b7 Dongcheng District")
        }
    }

    /** 用指定坐标获取房源数据，nearby和recommend并行请求 */
    private suspend fun fetchHouseData(lat: Double, lng: Double) = coroutineScope {
        Log.d(TAG, "fetchHouseData: calling APIs lat=$lat, lng=$lng")

        // 并行请求nearby、recommend和overview
        val nearbyDeferred = async { fetchNearbyHouses(lat, lng) }
        val recommendDeferred = async { fetchRecommendHouses() }
        val overviewDeferred = async { fetchOverview() }

        val nearby = nearbyDeferred.await()
        val recommend = recommendDeferred.await()
        overviewDeferred.await()
        Log.d(TAG, "refresh: data -> nearby=${nearby?.size ?: 0}, recommend=${recommend?.size ?: 0}")
    }

    private suspend fun fetchNearbyHouses(lat: Double, lng: Double): List<HouseWithDistance>? {
        val result = repository.getHousesSortedByDistance(userLat = lat, userLng = lng, pageSize = 10)
        if (result is NetworkResult.Success) {
            Log.d(TAG, "fetchHouseData: nearby OK, count={result.data.size}")
            _uiState.value = _uiState.value.copy(nearbyHouses = result.data)
            return result.data
        } else if (result is NetworkResult.Error) {
            Log.e(TAG, "fetchHouseData: nearby FAIL code=${result.code}, msg=${result.message}")
            _uiState.value = _uiState.value.copy(error = "Nearby: ${result.message}")
        }
        return null
    }

    private suspend fun fetchRecommendHouses(): List<HouseItem>? {
        val result = repository.getHouses(page = 1, pageSize = 10)
        if (result is NetworkResult.Success) {
            val sorted = result.data.sortedByDescending { it.unitPrice ?: 0.0 }
            Log.d(TAG, "fetchHouseData: recommend OK, count=${sorted.size}")
            _uiState.value = _uiState.value.copy(
                recommendHouses = sorted,
                isLoading = false,
                error = null
            )
            return sorted
        } else if (result is NetworkResult.Error) {
            Log.e(TAG, "fetchHouseData: recommend FAIL code=${result.code}, msg=${result.message}")
            _uiState.value = _uiState.value.copy(
                isLoading = false,
                error = "Recommend: ${result.message}"
            )
        }
        return null
    }

    private suspend fun fetchOverview(): OverviewData? {
        val result = repository.getOverview()
        if (result is NetworkResult.Success) {
            Log.d(TAG, "fetchOverview: OK totalHouses=${result.data.totalHouses}")
            _uiState.value = _uiState.value.copy(
                overviewData = result.data,
                isOverviewLoading = false
            )
            return result.data
        } else if (result is NetworkResult.Error) {
            Log.e(TAG, "fetchOverview: FAIL code=${result.code}, msg=${result.message}")
            _uiState.value = _uiState.value.copy(isOverviewLoading = false)
        }
        return null
    }

    private fun loadHouseData(lat: Double, lng: Double) {
        viewModelScope.launch {
            // 总览数据
            when (val overviewResult = repository.getOverview()) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(overviewData = overviewResult.data)
                }
                else -> {}
            }

            // 就近房屋
            when (val nearbyResult = repository.getHousesSortedByDistance(
                userLat = lat, userLng = lng, pageSize = 10
            )) {
                is NetworkResult.Success -> {
                    _uiState.value = _uiState.value.copy(nearbyHouses = nearbyResult.data)
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(error = nearbyResult.message)
                }
                is NetworkResult.Loading -> {}
            }

            // 推荐房屋
            when (val recommendResult = repository.getHouses(page = 1, pageSize = 10)) {
                is NetworkResult.Success -> {
                    val sorted = recommendResult.data.sortedByDescending { it.unitPrice ?: 0.0 }
                    _uiState.value = _uiState.value.copy(
                        recommendHouses = sorted,
                        isLoading = false,
                        error = null
                    )
                }
                is NetworkResult.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = recommendResult.message
                    )
                }
                is NetworkResult.Loading -> {}
            }
        }
    }

    private suspend fun getAddressFromLocation(lat: Double, lng: Double): String {
        return try {
            val geocoder = Geocoder(getApplication(), Locale.getDefault())
            val addresses: List<Address>? = geocoder.getFromLocation(lat, lng, 1)
            if (!addresses.isNullOrEmpty()) {
                val address = addresses[0]
                val district = address.subAdminArea ?: address.locality ?: ""
                val street = address.featureName ?: address.thoroughfare ?: ""
                if (street.isNotEmpty()) "$district \u00b7 $street" else district.ifEmpty { "Current Location" }
            } else {
                String.format(Locale.getDefault(), "%.4f, %.4f", lat, lng)
            }
        } catch (e: Exception) {
            String.format(Locale.getDefault(), "%.4f, %.4f", lat, lng)
        }
    }
}
