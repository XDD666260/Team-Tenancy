package com.example.tenancy.ui.home

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.example.tenancy.data.model.HouseItem
import com.example.tenancy.databinding.ItemHouseCardBinding

/**
 * 推荐房屋适配器（竖向列表）
 */
class RecommendHouseAdapter(
    private val onItemClick: (HouseItem) -> Unit
) : RecyclerView.Adapter<RecommendHouseAdapter.ViewHolder>() {

    private val items = mutableListOf<HouseItem>()

    fun submitList(list: List<HouseItem>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemHouseCardBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size

    inner class ViewHolder(
        private val binding: ItemHouseCardBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(house: HouseItem) {
            binding.tvHouseTitle.text = house.title ?: house.community ?: "Unknown"
            binding.tvHouseLayout.text = buildLayoutText(house)
            binding.tvHouseAddress.text = house.community ?: house.address ?: ""
            binding.tvHousePrice.text = formatPrice(house.totalPrice)+"万"
            binding.tvHouseArea.text = house.area?.let { String.format("%sm²", it) } ?: ""

            // 推荐列表不显示距离标签
            binding.tvDistanceTag.visibility = android.view.View.GONE

            binding.root.setOnClickListener { onItemClick(house) }
        }
    }

    private fun buildLayoutText(house: HouseItem): String {
        val rooms = house.rooms?.let { "${it}室" } ?: ""
        val halls = house.halls?.let { "${it}厅" } ?: ""
        val bathrooms = house.bathrooms?.let { "${it}卫" } ?: ""
        val layout = house.layout ?: ""
        return when {
            layout.isNotEmpty() -> "$layout · ${house.orientation ?: ""}"
            rooms.isNotEmpty() -> "$rooms$halls$bathrooms · ${house.orientation ?: ""}"
            else -> house.orientation ?: ""
        }.trim().trim('·').trim()
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
