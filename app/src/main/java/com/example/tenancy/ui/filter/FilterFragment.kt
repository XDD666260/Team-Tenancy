package com.example.tenancy.ui.filter

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.tenancy.R
import com.example.tenancy.databinding.FragmentFilterBinding
import kotlinx.coroutines.launch

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.view.animation.DecelerateInterpolator

class FilterFragment : Fragment() {

    private var _binding: FragmentFilterBinding? = null
    private val binding get() = _binding!!

    private val viewModel: FilterViewModel by viewModels()
    private lateinit var adapter: FilterHouseAdapter
    private var spinnersReady = false
    private var isAnimating = false

    // 筛选选项
    private val districts = arrayOf("全部", "两江新区", "渝中区", "南岸区", "沙坪坝区", "九龙坡区",
        "巴南区", "北碚区", "大渡口区", "璧山区", "永川区", "万州区","江津区","合川区","铜梁区","涪陵区",
        "长寿区","荣昌区","綦江区","南川区","大足区","潼南区","开州区","垫江县","梁平区","万盛区","奉节县",
        "云阳县","忠县","巫溪县","黔江区","武隆区","巫山县","城口县","彭水县","秀山县","石柱县","酉阳县","丰都县")

    private val roomOptions = arrayOf("全部", "一室", "两室", "三室", "四室", "五室及以上")
    private val roomValues = arrayOf<Int?>(null, 1, 2, 3, 4, 5)

    private val decorationOptions = arrayOf("全部", "毛坯", "简装", "精装")

    private val orientationOptions = arrayOf("全部", "东", "南", "西", "北", "南北")

    private val sourceOptions = arrayOf("全部", "安居客", "链家", "贝壳", "我爱我家")
    private val sourceValueMap = mapOf(
        "安居客" to "anjuke",
        "链家" to "lianjia",
        "贝壳" to "beike",
        "我爱我家" to "woaiwojia"
    )

    // 面积分段
    private val areaLabels = arrayOf("不限", "50m²以下", "50-70m²", "70-90m²", "90-120m²", "120-150m²", "150-200m²", "200m²以上")
    private val areaMins = arrayOf<Double?>(null, 0.0, 50.0, 70.0, 90.0, 120.0, 150.0, 200.0)
    private val areaMaxs = arrayOf<Double?>(null, 50.0, 70.0, 90.0, 120.0, 150.0, 200.0, null)

    private val areaOptions = arrayOf("不限", "50m²以下", "50-70m²", "70-90m²", "90-120m²", "120-150m²", "150-200m²", "200m²以上")
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentFilterBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        setupSpinners()

        setupListeners()
        setupRecyclerView()
        observeState()

        // 初始加载
        viewModel.search()
        spinnersReady = true
    }

    /**
     * 触发搜索（筛选条件已由各控件在触发前单独设置好）
     */
    private fun triggerSearch() {
        viewModel.search()
        viewModel.setPriceFilter(binding.etMinPrice.text.toString().toDoubleOrNull(), binding.etMaxPrice.text.toString().toDoubleOrNull())
    }

    private fun setupRecyclerView() {
        adapter = FilterHouseAdapter { house ->
            val intent = Intent(requireContext(), HouseDetailActivity::class.java)
            intent.putExtra(HouseDetailActivity.EXTRA_HOUSE_ID, house.id)
            startActivity(intent)
        }
        binding.rvHouses.apply {
            layoutManager = LinearLayoutManager(requireContext(), LinearLayoutManager.VERTICAL, false)
            adapter = this@FilterFragment.adapter
        }
    }

    private fun setupSpinners() {
        val context = requireContext()

        // 区县
        binding.spDistrict.adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, districts)
        binding.spDistrict.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                //viewModel.setFilter(district = districts[position])
                viewModel.setDistrictFilter(districts[position])
                if (spinnersReady) triggerSearch()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        // 面积
        binding.spArea.adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, areaOptions)
        binding.spArea.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                //viewModel.setFilter(minArea = areaMins[position], maxArea = areaMaxs[position])
                viewModel.setAreaFilter(areaMins[position],areaMaxs[position])
                if (spinnersReady) triggerSearch()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        // 户型
        binding.spLayout.adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, roomOptions)
        binding.spLayout.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (position == 0) {
                    //viewModel.setFilter(rooms = null)
                    viewModel.setRoomFilter(null)
                } else {
                    //viewModel.setFilter(rooms = roomValues[position])
                    viewModel.setRoomFilter(roomValues[position])
                }
                if (spinnersReady) triggerSearch()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }


        // 装修
        binding.spDecoration.adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, decorationOptions)
        binding.spDecoration.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                //viewModel.setFilter(decoration = if (position == 0) null else decorationOptions[position])
                viewModel.setDecorationFilter(if (position == 0) null else decorationOptions[position])
                if (spinnersReady) triggerSearch()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        // 朝向
        binding.spOrientation.adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, orientationOptions)
        binding.spOrientation.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                //viewModel.setFilter(orientation = if (position == 0) null else orientationOptions[position])
                viewModel.setOrientationFilter(if (position == 0) null else orientationOptions[position])
                if (spinnersReady) triggerSearch()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }

        // 来源
        binding.spSource.adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, sourceOptions)
        binding.spSource.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                //viewModel.setFilter(source = if (position == 0) null else sourceOptions[position])
                viewModel.setSourceFilter(if (position == 0) null else sourceValueMap[sourceOptions[position]])
                if (spinnersReady) triggerSearch()
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
    }

    private fun setupListeners() {
        // 展开/收起筛选面板（带动画）
        binding.btnToggleFilter.setOnClickListener {
            if (!isAnimating) toggleFilterPanel()
        }
        // 搜索按钮（用于手动提交价格区间）
        binding.btnSearch.setOnClickListener {
            val minPrice = binding.etMinPrice.text.toString().toDoubleOrNull()
            val maxPrice = binding.etMaxPrice.text.toString().toDoubleOrNull()
            viewModel.setPriceFilter(minPrice, maxPrice)
            viewModel.search()
        }

        // 重置按钮
        binding.btnReset.setOnClickListener {
            spinnersReady = false  // 重置过程中不触发自动搜索
            binding.spDistrict.setSelection(0)
            binding.spLayout.setSelection(0)
            //binding.spFloor.setSelection(0)
            binding.spDecoration.setSelection(0)
            binding.spOrientation.setSelection(0)
            binding.spSource.setSelection(0)
            binding.spArea.setSelection(0)
            binding.etMinPrice.text.clear()
            binding.etMaxPrice.text.clear()
            viewModel.resetFilters()
            viewModel.search()  // 统一触发一次搜索
            spinnersReady = true
        }

        // 分页按钮
        binding.btnPrevPage.setOnClickListener { viewModel.prevPage() }
        binding.btnNextPage.setOnClickListener { viewModel.nextPage() }
        binding.btnLoadMore.setOnClickListener { viewModel.loadMore() }
    }

    private fun observeState() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    // 更新列表
                    adapter.submitList(state.houses)

                    // 更新加载状态
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE

                    // 更新结果信息
                    updateResultInfo(state)

                    // 更新分页器
                    updatePagination(state)

                    // 错误提示
                    state.error?.let { error ->
                        if (error.isNotEmpty()) {
                            Toast.makeText(requireContext(), error, Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
        }
    }

    private fun updateResultInfo(state: FilterUiState) {
        binding.tvResultInfo.text = when {
            state.isFirstLoad -> "正在加载数据…"
            state.isLoading -> "正在搜索…"
            state.total > 0 -> "共找到 ${state.total} 套房源"
            else -> "暂无符合条件的房源"
        }
    }

    private fun updatePagination(state: FilterUiState) {
        if (state.isFirstLoad || state.total == 0) {
            binding.paginationBar.visibility = View.GONE
            return
        }

        binding.paginationBar.visibility = View.VISIBLE
        binding.tvPageInfo.text = "${state.currentPage}/${state.totalPages}页"
        binding.btnPrevPage.isEnabled = state.hasPrevPage
        binding.btnNextPage.isEnabled = state.hasNextPage

        // 加载更多按钮：最后一页或只有1页时隐藏
        binding.btnLoadMore.visibility = if (state.hasNextPage) View.VISIBLE else View.GONE
    }


    // ===== 折叠/展开动画 =====  

    private fun toggleFilterPanel() {
        if (binding.filterPanel.visibility == View.VISIBLE) {
            collapseFilterPanel()
        } else {
            expandFilterPanel()
        }
    }

    private fun collapseFilterPanel() {
        val startHeight = binding.filterPanel.height
        if (startHeight <= 0) return

        isAnimating = true

        // 按钮旋转动画
        ObjectAnimator.ofFloat(binding.btnToggleFilter, View.ROTATION, binding.btnToggleFilter.rotation, 0f)
            .apply {
                duration = 280L
                interpolator = DecelerateInterpolator()
                start()
            }

        // 面板高度收缩动画
        ValueAnimator.ofInt(startHeight, 0).apply {
            addUpdateListener { anim ->
                binding.filterPanel.layoutParams.height = anim.animatedValue as Int
                binding.filterPanel.requestLayout()
            }
            addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    binding.filterPanel.visibility = View.GONE
                    binding.filterPanel.layoutParams.height = ViewGroup.LayoutParams.WRAP_CONTENT
                    binding.filterPanel.alpha = 1f
                    isAnimating = false
                }
            })
            duration = 280L
            interpolator = DecelerateInterpolator()
            start()
        }

        // 淡出
        binding.filterPanel.animate()
            .alpha(0f)
            .setDuration(200L)
            .setInterpolator(DecelerateInterpolator())
            .start()
    }

    private fun expandFilterPanel() {
        isAnimating = true

        // 先设为可见但透明、高度0
        binding.filterPanel.visibility = View.VISIBLE
        binding.filterPanel.alpha = 0f
        binding.filterPanel.layoutParams.height = 0

        // 手动测量面板获得完整高度
        val widthSpec = View.MeasureSpec.makeMeasureSpec(
            (binding.filterPanel.parent as View).width,
            View.MeasureSpec.EXACTLY
        )
        binding.filterPanel.measure(widthSpec, View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
        val targetHeight = binding.filterPanel.measuredHeight
        binding.filterPanel.layoutParams.height = 0

        // 按钮旋转动画
        ObjectAnimator.ofFloat(binding.btnToggleFilter, View.ROTATION, binding.btnToggleFilter.rotation, 180f)
            .apply {
                duration = 280L
                interpolator = DecelerateInterpolator()
                start()
            }

        // 面板高度展开动画
        ValueAnimator.ofInt(0, targetHeight).apply {
            addUpdateListener { anim ->
                binding.filterPanel.layoutParams.height = anim.animatedValue as Int
                binding.filterPanel.requestLayout()
            }
            addListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    binding.filterPanel.layoutParams.height = ViewGroup.LayoutParams.WRAP_CONTENT
                    isAnimating = false
                }
            })
            duration = 280L
            interpolator = DecelerateInterpolator()
            start()
        }

        // 淡入
        binding.filterPanel.animate()
            .alpha(1f)
            .setDuration(220L)
            .setStartDelay(60L)
            .setInterpolator(DecelerateInterpolator())
            .start()
    }
    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
