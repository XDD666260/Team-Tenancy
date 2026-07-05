package com.example.tenancy.ui.chart

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.tenancy.R
import com.example.tenancy.data.model.AreaBin
import com.example.tenancy.data.model.PriceDistribution
import com.example.tenancy.data.model.LayoutDistribution
import com.example.tenancy.data.model.AreaDistribution
import com.example.tenancy.databinding.FragmentChartBinding
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.components.Legend
import com.github.mikephil.charting.data.*
import com.github.mikephil.charting.formatter.IndexAxisValueFormatter
import com.github.mikephil.charting.formatter.PercentFormatter
import com.github.mikephil.charting.formatter.ValueFormatter
import kotlinx.coroutines.launch
import java.util.Locale

class ChartFragment : Fragment() {

    private var _binding: FragmentChartBinding? = null
    private val binding get() = _binding!!

    private val viewModel: ChartViewModel by viewModels()

    private var isTotalPriceMode = false
    private var isAreaBarMode = false

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentChartBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        setupCharts()
        setupToggleListeners()
        observeState()
    }

    private fun setupCharts() {
        binding.barChartPrice.apply {
            description.isEnabled = false
            setDrawGridBackground(false)
            setDrawBarShadow(false)
            setScaleEnabled(false)
            setPinchZoom(false)
            setFitBars(true)
            animateY(800)
            legend.isEnabled = true
            legend.textSize = 12f
            xAxis.apply {
                position = XAxis.XAxisPosition.BOTTOM
                setDrawGridLines(false)
                granularity = 1f
                textSize = 11f
                labelRotationAngle = -45f
            }
            axisLeft.apply {
                setDrawGridLines(true)
                gridColor = Color.parseColor("#FFEEEEEE")
                textSize = 11f
                axisMinimum = 0f
            }
            axisRight.isEnabled = false
        }

        binding.combinedChartLayout.apply {
            description.isEnabled = false
            setDrawGridBackground(false)
            setScaleEnabled(false)
            setPinchZoom(false)
            animateY(800)
            legend.isEnabled = true
            legend.textSize = 12f
            xAxis.apply {
                position = XAxis.XAxisPosition.BOTTOM
                setDrawGridLines(false)
                granularity = 1f
                textSize = 11f
            }
            axisLeft.apply {
                setDrawGridLines(true)
                gridColor = Color.parseColor("#FFEEEEEE")
                textSize = 11f
                axisMinimum = 0f
            }
            axisRight.apply {
                isEnabled = true
                setDrawGridLines(false)
                textSize = 11f
                axisMinimum = 0f
            }
        }

        binding.pieChartArea.apply {
            description.isEnabled = false
            // 由 PieDataSet 控制标签位置，饼图自身不绘制入口标签
            setDrawEntryLabels(false)
            setUsePercentValues(true)
            setCenterText("面积分布")
            setCenterTextSize(14f)
            setCenterTextTypeface(Typeface.DEFAULT_BOLD)
            setHoleRadius(40f)
            setTransparentCircleRadius(45f)
            animateY(800)
            legend.isEnabled = true
            legend.textSize = 12f
            legend.orientation = Legend.LegendOrientation.HORIZONTAL
            legend.verticalAlignment = Legend.LegendVerticalAlignment.BOTTOM
            legend.horizontalAlignment = Legend.LegendHorizontalAlignment.CENTER
        }

        binding.barChartArea.apply {
            description.isEnabled = false
            setDrawGridBackground(false)
            setDrawBarShadow(false)
            setScaleEnabled(false)
            setPinchZoom(false)
            setFitBars(true)
            animateY(800)
            legend.isEnabled = true
            legend.textSize = 12f
            xAxis.apply {
                position = XAxis.XAxisPosition.BOTTOM
                setDrawGridLines(false)
                granularity = 1f
                textSize = 11f
                labelRotationAngle = -30f
            }
            axisLeft.apply {
                setDrawGridLines(true)
                gridColor = Color.parseColor("#FFEEEEEE")
                textSize = 11f
                axisMinimum = 0f
            }
            axisRight.isEnabled = false
        }
    }

    private fun setupToggleListeners() {
        binding.togglePrice.addOnButtonCheckedListener { _, checkedId, isChecked ->
            if (!isChecked) return@addOnButtonCheckedListener
            isTotalPriceMode = checkedId == R.id.btnTotalPrice
            refreshPriceChart()
        }
        binding.toggleArea.addOnButtonCheckedListener { _, checkedId, isChecked ->
            if (!isChecked) return@addOnButtonCheckedListener
            isAreaBarMode = checkedId == R.id.btnAreaBar
            refreshAreaChart()
        }
    }

    private fun observeState() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    if (state.error != null) {
                        binding.tvError.visibility = View.VISIBLE
                        binding.tvError.text = state.error
                    } else {
                        binding.tvError.visibility = View.GONE
                    }
                    if (!state.isPriceLoading && state.priceDistribution != null) {
                        bindPriceChart(state.priceDistribution)
                    }
                    if (!state.isLayoutLoading && state.layoutDistribution != null) {
                        bindLayoutChart(state.layoutDistribution)
                    }
                    if (!state.isAreaLoading && state.areaDistribution != null) {
                        bindAreaChart(state.areaDistribution)
                    }
                }
            }
        }
    }

    // ==================== 价格柱状图 ====================

    private fun refreshPriceChart() {
        val data = viewModel.uiState.value.priceDistribution ?: return
        bindPriceChart(data)
    }

    private fun bindPriceChart(data: PriceDistribution) {
        val bins = if (isTotalPriceMode) data.totalPriceBins else data.unitPriceBins
        if (bins.isNullOrEmpty()) return
        val entries = bins.mapIndexed { index, bin -> BarEntry(index.toFloat(), bin.count.toFloat()) }
        val labels = bins.map { it.range ?: "" }
        val dataSet = BarDataSet(entries, if (isTotalPriceMode) "总价区间" else "单价区间").apply {
            color = Color.parseColor("#FF2196F3")
            valueTextSize = 11f
            valueFormatter = object : ValueFormatter() {
                override fun getFormattedValue(value: Float): String = value.toInt().toString()
            }
        }
        binding.barChartPrice.apply {
            xAxis.valueFormatter = IndexAxisValueFormatter(labels)
            this.data = BarData(dataSet)
            invalidate()
        }
    }

    // ==================== 户型组合图（柱状+折线） ====================

    private fun bindLayoutChart(data: LayoutDistribution) {
        val roomsDist = data.roomsDistribution
        val avgPrice = data.avgPriceByRooms
        if (roomsDist.isNullOrEmpty()) return
        val labels = roomsDist.map { "${it.rooms}室" }
        val priceMap = avgPrice?.associateBy { it.rooms } ?: emptyMap()

        val barEntries = roomsDist.mapIndexed { index, item -> BarEntry(index.toFloat(), item.count.toFloat()) }
        val hasLineData = priceMap.isNotEmpty()
        val maxCount = barEntries.maxOfOrNull { it.y } ?: 0f

        val valueColors = barEntries.map { entry ->
            if (hasLineData && maxCount > 0f && entry.y >= maxCount * 0.20f && entry.y <= maxCount * 0.8f) {
                Color.TRANSPARENT
            } else {
                Color.parseColor("#FF1A1A1A")
            }
        }

        val barDataSet = BarDataSet(barEntries, "户型数量").apply {
            color = Color.parseColor("#FF2196F3")
            setDrawValues(true)
            valueTextSize = 11f
            setValueTextColors(valueColors)
            valueFormatter = object : ValueFormatter() {
                override fun getFormattedValue(value: Float): String = value.toInt().toString()
            }
        }
        val barData = BarData(barDataSet).apply { barWidth = 0.5f }
        val combinedData = CombinedData()
        combinedData.setData(barData)

        if (priceMap.isNotEmpty()) {
            val lineEntries = roomsDist.mapIndexed { index, item ->
                val price = priceMap[item.rooms]?.avgUnitPrice ?: 0.0
                Entry(index.toFloat(), price.toFloat())
            }
            val lineDataSet = LineDataSet(lineEntries, "均价(元/㎡)").apply {
                color = Color.parseColor("#FFE53935")
                valueTextSize = 11f
                setCircleColor(Color.parseColor("#FFE53935"))
                circleRadius = 4f
                setDrawValues(true)
                valueFormatter = object : ValueFormatter() {
                    override fun getFormattedValue(value: Float): String =
                        String.format(Locale.getDefault(), "%.0f", value)
                }
                lineWidth = 2f
                setDrawFilled(false)
            }
            combinedData.setData(LineData(lineDataSet))
        }

        binding.combinedChartLayout.apply {
            xAxis.valueFormatter = IndexAxisValueFormatter(labels)
            this.data = combinedData
            invalidate()
        }
    }

    // ==================== 面积分布 ====================

    private fun refreshAreaChart() {
        val data = viewModel.uiState.value.areaDistribution ?: return
        bindAreaChart(data)
    }

    private fun bindAreaChart(data: AreaDistribution) {
        val bins = data.bins
        if (bins.isNullOrEmpty()) return
        if (isAreaBarMode) {
            showAreaBarChart(bins)
        } else {
            showAreaPieChart(bins)
        }
    }

    private fun showAreaPieChart(bins: List<AreaBin>) {
        val total = bins.sumOf { it.count }
        if (total == 0) return

        val entries = bins.map { bin ->
            PieEntry(bin.count.toFloat(), bin.range ?: "")
        }

        val pieColors = listOf(
            Color.parseColor("#FF4CAF50"),
            Color.parseColor("#FF2196F3"),
            Color.parseColor("#FFFF9800"),
            Color.parseColor("#FFE53935"),
            Color.parseColor("#FF9C27B0")
        )

        val minPercent = 0.05f
        val textColors = entries.map { entry ->
            if (entry.value / total < minPercent) Color.TRANSPARENT
            else Color.WHITE
        }

        val dataSet = PieDataSet(entries, "").apply {
            colors = pieColors
            valueTextSize = 12f
            setValueTextColors(textColors)
            valueFormatter = PercentFormatter(binding.pieChartArea)
            sliceSpace = 2f
            // 区间名写在扇区内部，百分比重在外部连线标注
            setXValuePosition(PieDataSet.ValuePosition.INSIDE_SLICE)
            setYValuePosition(PieDataSet.ValuePosition.INSIDE_SLICE)
            // 外部标签连线配置
            valueLinePart1Length = 0.4f
            valueLinePart2Length = 0.6f
            valueLineColor = Color.parseColor("#FF999999")
            // 扇区内文字用白色
            
        }

        binding.pieChartArea.apply {
            this.data = PieData(dataSet)
            setCenterText("面积分布\n${total}套")
            visibility = View.VISIBLE
            invalidate()
        }
        binding.barChartArea.visibility = View.GONE
    }

    private fun showAreaBarChart(bins: List<AreaBin>) {
        val entries = bins.mapIndexed { index, bin -> BarEntry(index.toFloat(), bin.count.toFloat()) }
        val labels = bins.map { it.range ?: "" }
        val barColors = listOf(
            Color.parseColor("#FF4CAF50"),
            Color.parseColor("#FF2196F3"),
            Color.parseColor("#FFFF9800"),
            Color.parseColor("#FFE53935"),
            Color.parseColor("#FF9C27B0")
        )
        val dataSet = BarDataSet(entries, "面积区间").apply {
            colors = barColors
            valueTextSize = 11f
            valueFormatter = object : ValueFormatter() {
                override fun getFormattedValue(value: Float): String = value.toInt().toString()
            }
        }
        binding.barChartArea.apply {
            xAxis.valueFormatter = IndexAxisValueFormatter(labels)
            this.data = BarData(dataSet)
            visibility = View.VISIBLE
            invalidate()
        }
        binding.pieChartArea.visibility = View.GONE
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
