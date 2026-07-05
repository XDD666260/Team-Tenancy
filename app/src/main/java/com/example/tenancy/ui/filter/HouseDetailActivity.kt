package com.example.tenancy.ui.filter

import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.viewpager2.widget.ViewPager2
import com.bumptech.glide.Glide
import com.example.tenancy.R
import com.example.tenancy.data.model.HouseItem
import com.example.tenancy.data.remote.NetworkResult
import com.example.tenancy.data.repository.HouseRepository


import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class HouseDetailActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_HOUSE_ID = "house_id"
    }

    private lateinit var imageContainer: ViewGroup
    private lateinit var indicatorContainer: LinearLayout
    private lateinit var btnBack: ImageView
    private lateinit var detailTitle: TextView
    private lateinit var detailAddress: TextView
    private lateinit var detailPrice: TextView
    private lateinit var detailUnitPrice: TextView
    private lateinit var featureGrid: ViewGroup

    private val repository = HouseRepository()
    private var currentHouse: HouseItem? = null
    private var currentDotIndex = 0
    private val dots = mutableListOf<View>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_house_detail)

        imageContainer = findViewById(R.id.imageGallery)
        indicatorContainer = findViewById(R.id.indicatorContainer)
        btnBack = findViewById(R.id.btnBack)
        detailTitle = findViewById(R.id.detailTitle)
        detailAddress = findViewById(R.id.detailAddress)
        detailPrice = findViewById(R.id.detailPrice)
        detailUnitPrice = findViewById(R.id.detailUnitPrice)
        featureGrid = findViewById(R.id.featureGrid)

        btnBack.setOnClickListener { finish() }

        val houseId = intent.getIntExtra(EXTRA_HOUSE_ID, -1)
        if (houseId > 0) {
            loadHouseDetail(houseId)
        }
    }

    private fun loadHouseDetail(houseId: Int) {
        lifecycleScope.launch {
            withContext(Dispatchers.IO) {
                repository.getHouseDetail(houseId)
            }.let { result ->
                when (result) {
                    is NetworkResult.Success -> {
                        bindHouse(result.data)
                    }
                    is NetworkResult.Error -> {
                        detailTitle.text = "加载失败"
                        detailTitle.visibility = View.VISIBLE
                    }
                    is NetworkResult.Loading -> {}
                }
            }
        }
    }

    private fun bindHouse(house: HouseItem) {
        currentHouse = house

        val context = this

        detailTitle.text = house.title ?: house.community ?: "房源详情"
        detailAddress.text = house.community ?: house.address ?: ""
        detailPrice.text = formatPrice(house.totalPrice)+"万"

        val unitPriceText = house.unitPrice?.let { "单价 ¥${it.toInt()}/m²" } ?: ""
        detailUnitPrice.text = unitPriceText
        detailUnitPrice.visibility = if (unitPriceText.isNotEmpty()) View.VISIBLE else View.GONE

        // 图片轮播
        setupImageGallery(house.imageUrls)

        // 特征网格
        setupFeatureGrid(house)
    }

    private fun setupImageGallery(imageUrls: List<String>?) {
        val urls = imageUrls.orEmpty().filter { it.isNotBlank() }
        if (urls.isEmpty()) {
            // 没有图片，显示占位
            val placeholder = ImageView(this).apply {
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )
                scaleType = ImageView.ScaleType.CENTER_CROP
                setImageResource(R.drawable.ic_house)
            }
            (imageContainer as? ViewGroup)?.addView(placeholder, 0)
            return
        }

        val viewPager = findViewById<ViewPager2>(R.id.viewPagerImages)
        viewPager.adapter = ImagePagerAdapter(this, urls)
        viewPager.visibility = View.VISIBLE

        // 指示器点
        if (urls.size > 1) {
            indicatorContainer.removeAllViews()
            dots.clear()
            for (i in urls.indices) {
                val dot = View(this).apply {
                    layoutParams = ViewGroup.LayoutParams(8, 8).apply {
                        if (i > 0) {
                            (this as ViewGroup.MarginLayoutParams).marginStart = 6
                        }
                    }
                    setBackgroundResource(
                        if (i == 0) android.R.drawable.presence_online
                        else android.R.drawable.presence_offline
                    )
                }
                indicatorContainer.addView(dot)
                dots.add(dot)
            }
            currentDotIndex = 0

            viewPager.registerOnPageChangeCallback(object : ViewPager2.OnPageChangeCallback() {
                override fun onPageSelected(position: Int) {
                    dots.getOrNull(currentDotIndex)?.setBackgroundResource(
                        android.R.drawable.presence_offline
                    )
                    dots.getOrNull(position)?.setBackgroundResource(
                        android.R.drawable.presence_online
                    )
                    currentDotIndex = position
                }
            })
        }
    }

    private fun setupFeatureGrid(house: HouseItem) {
        val features = mutableListOf<Pair<String, String>>()

        // 户型
        val layoutText = buildLayoutText(house)
        if (layoutText.isNotEmpty()) features.add("户型" to layoutText)

        // 面积
        house.area?.let { features.add("面积" to "${it.toInt()}m²") }

        // 楼层
        val floorDesc = house.floorDesc
        val totalFloors = house.totalFloors
        val floorText = buildString {
            if (floorDesc != null) append(floorDesc)
            if (totalFloors != null) append("（${totalFloors}层）")
        }
        if (floorText.isNotEmpty()) features.add("楼层" to floorText)

        // 朝向
        house.orientation?.let {
            if (it.isNotEmpty()) features.add("朝向" to it)
        }

        // 装修
        house.decoration?.let {
            if (it.isNotEmpty()) features.add("装修" to it)
        }

        // 区县
        house.district?.let {
            if (it.isNotEmpty()) features.add("区县" to it)
        }

        // 来源
        house.source?.let {
            if (it.isNotEmpty()) features.add("来源" to it)
        }

        // 建造年份
        house.buildYear?.let {
            features.add("建造年份" to "${it}年")
        }

        featureGrid.removeAllViews()
        featureGrid.visibility = View.VISIBLE

        for ((label, value) in features) {
            val itemView = layoutInflater.inflate(R.layout.item_detail_feature, featureGrid, false)
            itemView.findViewById<TextView>(android.R.id.text1).text = label
            itemView.findViewById<TextView>(android.R.id.text2).text = value
            featureGrid.addView(itemView)
        }
    }

    private fun buildLayoutText(house: HouseItem): String {
        val rooms = house.rooms?.let { "${it}室" } ?: ""
        val halls = house.halls?.let { "${it}厅" } ?: ""
        val bathrooms = house.bathrooms?.let { "${it}卫" } ?: ""
        val layout = house.layout ?: ""
        return when {
            layout.isNotEmpty() -> layout
            rooms.isNotEmpty() -> "$rooms$halls$bathrooms"
            else -> ""
        }
    }

    private fun formatPrice(price: Double?): String {
        if (price == null) return ""
        return if (price >= 10000) {
            String.format("¥%.0f万", price / 10000)
        } else {
            String.format("¥%.0f", price)
        }
    }
}



