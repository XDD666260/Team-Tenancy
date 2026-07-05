package com.example.tenancy.ui.filter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.tenancy.R
import com.example.tenancy.data.model.HouseItem
import com.example.tenancy.databinding.ItemFilterHouseBinding

class FilterHouseAdapter(
    private val onItemClick: (HouseItem) -> Unit
) : RecyclerView.Adapter<FilterHouseAdapter.ViewHolder>() {

    private val items = mutableListOf<HouseItem>()

    fun submitList(list: List<HouseItem>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemFilterHouseBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size

    inner class ViewHolder(
        private val binding: ItemFilterHouseBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(house: HouseItem) {
            // 标题
            binding.tvHouseTitle.text = house.title ?: house.community ?: "未知房源"

            // 小区
            binding.tvCommunity.text = house.community ?: house.address ?: ""

            // 户型 + 面积
            val layoutText = buildLayoutText(house)
            val areaText = house.area?.let { "${it.toInt()}m²" } ?: ""
            binding.tvLayoutArea.text = buildList {
                if (layoutText.isNotEmpty()) add(layoutText)
                if (areaText.isNotEmpty()) add(areaText)
            }.joinToString(" · ")

            // 价格
            binding.tvHousePrice.text = formatPrice(house.totalPrice)+"万"

            // 标签
            var tagIndex = 0

            // 装修标签
            val decoration = house.decoration
            if (!decoration.isNullOrEmpty() && decoration != "未知") {
                binding.tagContainer.getChildAt(0).apply {
                    visibility = View.VISIBLE
                    if (this is android.widget.TextView) {
                        text = decoration
                        setTextColor(
                            when (decoration) {
                                "精装" -> android.graphics.Color.parseColor("#FF4CAF50")
                                "豪装" -> android.graphics.Color.parseColor("#FFFF9800")
                                else -> resources.getColor(R.color.colorPrimary, null)
                            }
                        )
                    }
                }
                tagIndex++
            }

            // 楼层标签
            val floorType = house.floorType
            if (!floorType.isNullOrEmpty()) {
                val floorTag = binding.tagContainer.getChildAt(1)
                floorTag.visibility = View.VISIBLE
                if (floorTag is android.widget.TextView) {
                    floorTag.text = floorType
                }
                tagIndex++
            }

            // 来源标签
            val source = house.source
            if (!source.isNullOrEmpty()) {
                val sourceTag = binding.tagContainer.getChildAt(2)
                sourceTag.visibility = View.VISIBLE
                if (sourceTag is android.widget.TextView) {
                    sourceTag.text = source
                }
                tagIndex++
            }

            // 隐藏多余的标签
            for (i in tagIndex until 3) {
                binding.tagContainer.getChildAt(i).visibility = View.GONE
            }

            // 图片加载 – Glide
            val context = binding.root.context
            if (!house.imageUrls.isNullOrEmpty()) {
                Glide.with(context)
                    .load(house.imageUrls[0])
                    .placeholder(R.drawable.ic_house)
                    .error(R.drawable.ic_house)
                    .centerCrop()
                    .into(binding.ivHouseImage)
            } else if (house.hasImages == true) {
                // 有图片但imageUrls为空，用占位图
                Glide.with(context)
                    .load(R.drawable.ic_house)
                    .centerCrop()
                    .into(binding.ivHouseImage)
            } else {
                binding.ivHouseImage.setImageResource(R.drawable.ic_house)
            }

            binding.root.setOnClickListener { onItemClick(house) }
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
