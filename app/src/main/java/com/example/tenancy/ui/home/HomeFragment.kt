package com.example.tenancy.ui.home

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.tenancy.R
import com.example.tenancy.data.model.DistrictStat
import com.example.tenancy.data.model.OverviewData
import com.example.tenancy.databinding.FragmentHomeBinding
import kotlinx.coroutines.launch
import java.util.Locale

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!

    private val viewModel: HomeViewModel by viewModels()
    private lateinit var nearbyAdapter: NearbyHouseAdapter
    private lateinit var recommendAdapter: RecommendHouseAdapter

    // 运行时权限请求 launcher
    private val locationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { permissions ->
            val granted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true
                    || permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
            if (granted) {
                // 权限已授予，触发定位和数据加载
                viewModel.refresh()
            } else {
                // 权限被拒绝，使用默认位置
                viewModel.loadWithDefaultLocation()
            }
        }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        setupRecyclerViews()
        setupListeners()
        observeState()
        checkAndRequestLocationPermission()
    }

    private fun checkAndRequestLocationPermission() {
        val hasFineLocation = ContextCompat.checkSelfPermission(
            requireContext(), Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val hasCoarseLocation = ContextCompat.checkSelfPermission(
            requireContext(), Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (hasFineLocation || hasCoarseLocation) {
            viewModel.refresh()
        } else {
            locationPermissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                )
            )
        }
    }

    private fun setupRecyclerViews() {
        nearbyAdapter = NearbyHouseAdapter { item ->
            Toast.makeText(requireContext(), item.house.title ?: item.house.community, Toast.LENGTH_SHORT).show()
        }
        binding.rvNearbyHouses.apply {
            layoutManager = LinearLayoutManager(requireContext(), LinearLayoutManager.HORIZONTAL, false)
            adapter = nearbyAdapter
        }

        recommendAdapter = RecommendHouseAdapter { house ->
            Toast.makeText(requireContext(), house.title ?: house.community, Toast.LENGTH_SHORT).show()
        }
        binding.rvRecommendHouses.apply {
            layoutManager = LinearLayoutManager(requireContext(), LinearLayoutManager.VERTICAL, false)
            adapter = recommendAdapter
        }
    }

    private fun setupListeners() {
        binding.ivRefreshLocation.setOnClickListener {
            checkAndRequestLocationPermission()
        }

        binding.tvNearbyMore.setOnClickListener {
            Toast.makeText(requireContext(), "View all nearby houses", Toast.LENGTH_SHORT).show()
        }

        binding.tvRecommendMore.setOnClickListener {
            Toast.makeText(requireContext(), "View all recommended houses", Toast.LENGTH_SHORT).show()
        }
    }

    private fun observeState() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE
                    binding.tvLocationAddress.text = state.locationText

                    nearbyAdapter.submitList(state.nearbyHouses)
                    recommendAdapter.submitList(state.recommendHouses)

                    // 总览数据绑定
                    bindOverviewData(state.overviewData)

                    state.error?.let { error ->
                        if (error.isNotEmpty()) {
                            Toast.makeText(requireContext(), error, Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
        }
    }

    private fun bindOverviewData(data: OverviewData?) {
        val overviewRoot = binding.layoutOverview.root
        if (data == null) {
            overviewRoot.visibility = View.GONE
            return
        }
        overviewRoot.visibility = View.VISIBLE

        // 关键指标卡片
        binding.layoutOverview.tvTotalHouses.text = formatCount(data.totalHouses)
        binding.layoutOverview.tvAvgPrice.text = formatPrice(data.avgUnitPrice)
        binding.layoutOverview.tvDistrictCount.text = data.districtCount.toString()
        binding.layoutOverview.tvMaxPrice.text = formatPrice(data.maxUnitPrice)
        binding.layoutOverview.tvMinPrice.text = formatPrice(data.minUnitPrice)

        // 各区县统计列表
        buildDistrictList(data.byDistrict)

        // 数据来源占比
        buildSourceBars(data.bySource)

        // 更新时间
        if (data.updateTime.isNotEmpty()) {
            binding.layoutOverview.tvOverviewUpdateTime.text = "更新于 ${data.updateTime}"
            binding.layoutOverview.tvOverviewUpdateTime.visibility = View.VISIBLE
        } else {
            binding.layoutOverview.tvOverviewUpdateTime.visibility = View.GONE
        }
    }

    private fun buildDistrictList(districts: List<DistrictStat>) {
        val container = binding.layoutOverview.overviewDistrictList
        container.removeAllViews()

        if (districts.isEmpty()) {
            container.addView(createEmptyText("暂无区县数据"))
            return
        }

        // 只显示前8条
        val displayList = districts.take(8)
        for ((index, item) in displayList.withIndex()) {
            val row = LinearLayout(requireContext()).apply {
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(0, dp(6), 0, dp(6))
            }

            // 序号
            row.addView(TextView(requireContext()).apply {
                text = "${index + 1}"
                textSize = 12f
                setTextColor(ContextCompat.getColor(requireContext(), R.color.textHint))
                layoutParams = LinearLayout.LayoutParams(dp(20), ViewGroup.LayoutParams.WRAP_CONTENT)
            })

            // 区县名
            row.addView(TextView(requireContext()).apply {
                text = item.district
                textSize = 14f
                setTextColor(ContextCompat.getColor(requireContext(), R.color.textPrimary))
                layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
            })

            // 房源数
            row.addView(TextView(requireContext()).apply {
                text = "${item.count}套"
                textSize = 12f
                setTextColor(ContextCompat.getColor(requireContext(), R.color.textSecondary))
                gravity = Gravity.END
                layoutParams = LinearLayout.LayoutParams(dp(50), ViewGroup.LayoutParams.WRAP_CONTENT)
            })

            // 均价
            row.addView(TextView(requireContext()).apply {
                text = formatPrice(item.avgUnitPrice)
                textSize = 12f
                setTextColor(ContextCompat.getColor(requireContext(), R.color.priceColor))
                gravity = Gravity.END
                layoutParams = LinearLayout.LayoutParams(dp(80), ViewGroup.LayoutParams.WRAP_CONTENT)
            })

            container.addView(row)
        }
    }

    private fun buildSourceBars(sources: Map<String, Int>) {
        val container = binding.layoutOverview.overviewSourceBars
        container.removeAllViews()

        if (sources.isEmpty()) {
            container.addView(createEmptyText("暂无数据来源信息"))
            return
        }

        val total = sources.values.sum().toFloat()
        if (total == 0f) return

        for ((name, count) in sources) {
            val percent = (count / total * 100).toInt()

            val itemLayout = LinearLayout(requireContext()).apply {
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
                orientation = LinearLayout.VERTICAL
                setPadding(0, dp(4), 0, dp(4))
            }

            // 标签行：名称 + 占比
            val labelRow = LinearLayout(requireContext()).apply {
                orientation = LinearLayout.HORIZONTAL
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            }

            labelRow.addView(TextView(requireContext()).apply {
                text = name
                textSize = 13f
                setTextColor(ContextCompat.getColor(requireContext(), R.color.textPrimary))
                layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
            })

            labelRow.addView(TextView(requireContext()).apply {
                text = "${count}套 · ${percent}%"
                textSize = 12f
                setTextColor(ContextCompat.getColor(requireContext(), R.color.textSecondary))
                gravity = Gravity.END
            })

            itemLayout.addView(labelRow)

            // 进度条背景
            val barBg = View(requireContext()).apply {
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, dp(6)
                ).apply {
                    topMargin = dp(4)
                }
                setBackgroundColor(Color.parseColor("#FFEEEEEE"))
            }

            // 进度条前景（在 FrameLayout 中叠加）
            val barLayout = android.widget.FrameLayout(requireContext()).apply {
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, dp(6)
                ).apply {
                    topMargin = dp(4)
                }
                setBackgroundColor(Color.parseColor("#FFEEEEEE"))
            }

            val barFg = View(requireContext()).apply {
                layoutParams = android.widget.FrameLayout.LayoutParams(0, dp(6)).apply {
                    gravity = Gravity.START
                }
                val barColor = when (name) {
                    "安居客" -> Color.parseColor("#FF4CAF50")
                    "链家" -> Color.parseColor("#FF2196F3")
                    else -> Color.parseColor("#FFFF9800")
                }
                setBackgroundColor(barColor)
            }

            barLayout.addView(barFg)
            itemLayout.addView(barLayout)

            // 推迟设置宽度，等 post
            barFg.post {
                val totalWidth = barLayout.width
                if (totalWidth > 0) {
                    barFg.layoutParams = (barFg.layoutParams as android.widget.FrameLayout.LayoutParams).apply {
                        width = (totalWidth * percent / 100).coerceAtLeast(dp(2))
                    }
                }
            }

            container.addView(itemLayout)
        }
    }

    private fun createEmptyText(message: String): TextView {
        return TextView(requireContext()).apply {
            text = message
            textSize = 13f
            setTextColor(ContextCompat.getColor(requireContext(), R.color.textHint))
            gravity = Gravity.CENTER
            setPadding(0, dp(8), 0, dp(8))
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }
    }

    private fun formatCount(count: Int): String {
        return if (count >= 10000) {
            String.format(Locale.getDefault(), "%.1f万", count / 10000.0)
        } else {
            count.toString()
        }
    }

    private fun formatPrice(price: Double): String {
        return when {
            price >= 10000 -> String.format(Locale.getDefault(), "%.1f万", price / 10000.0)
            price >= 1000 -> String.format(Locale.getDefault(), "%.0f", price)
            else -> String.format(Locale.getDefault(), "%.0f", price)
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
