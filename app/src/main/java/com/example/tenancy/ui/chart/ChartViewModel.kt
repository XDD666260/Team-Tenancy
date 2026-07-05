package com.example.tenancy.ui.chart

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.tenancy.data.model.*
import com.example.tenancy.data.remote.NetworkResult
import com.example.tenancy.data.repository.HouseRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ChartUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    // 价格分布
    val priceDistribution: PriceDistribution? = null,
    val isPriceLoading: Boolean = true,
    // 户型分布
    val layoutDistribution: LayoutDistribution? = null,
    val isLayoutLoading: Boolean = true,
    // 面积分布
    val areaDistribution: AreaDistribution? = null,
    val isAreaLoading: Boolean = true
)

class ChartViewModel : ViewModel() {

    private val repository = HouseRepository()

    private val _uiState = MutableStateFlow(ChartUiState())
    val uiState: StateFlow<ChartUiState> = _uiState.asStateFlow()

    init {
        loadAllCharts()
    }

    fun refresh() {
        loadAllCharts()
    }

    private fun loadAllCharts() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)

            // 并行请求三个接口
            val priceDeferred = async { fetchPriceDistribution() }
            val layoutDeferred = async { fetchLayoutDistribution() }
            val areaDeferred = async { fetchAreaDistribution() }

            priceDeferred.await()
            layoutDeferred.await()
            areaDeferred.await()

            _uiState.value = _uiState.value.copy(isLoading = false)
        }
    }

    private suspend fun fetchPriceDistribution() {
        when (val result = repository.getPriceDistribution()) {
            is NetworkResult.Success -> {
                _uiState.value = _uiState.value.copy(
                    priceDistribution = result.data,
                    isPriceLoading = false
                )
            }
            is NetworkResult.Error -> {
                _uiState.value = _uiState.value.copy(
                    error = result.message,
                    isPriceLoading = false
                )
            }
            else -> {}
        }
    }

    private suspend fun fetchLayoutDistribution() {
        when (val result = repository.getLayoutDistribution()) {
            is NetworkResult.Success -> {
                _uiState.value = _uiState.value.copy(
                    layoutDistribution = result.data,
                    isLayoutLoading = false
                )
            }
            is NetworkResult.Error -> {
                _uiState.value = _uiState.value.copy(
                    error = result.message,
                    isLayoutLoading = false
                )
            }
            else -> {}
        }
    }

    private suspend fun fetchAreaDistribution() {
        when (val result = repository.getAreaDistribution()) {
            is NetworkResult.Success -> {
                _uiState.value = _uiState.value.copy(
                    areaDistribution = result.data,
                    isAreaLoading = false
                )
            }
            is NetworkResult.Error -> {
                _uiState.value = _uiState.value.copy(
                    error = result.message,
                    isAreaLoading = false
                )
            }
            else -> {}
        }
    }
}
