package com.example.tenancy.ui.home

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.example.tenancy.data.model.HouseWithDistance
import com.example.tenancy.databinding.ItemNearbyHouseCardBinding

/**
 * 就近房屋适配器（横向滚动）
 */
class NearbyHouseAdapter(
    private val onItemClick: (HouseWithDistance) -> Unit
) : RecyclerView.Adapter<NearbyHouseAdapter.ViewHolder>() {

    private val items = mutableListOf<HouseWithDistance>()

    fun submitList(list: List<HouseWithDistance>) {
        items.clear()
        items.addAll(list)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemNearbyHouseCardBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size

    inner class ViewHolder(
        private val binding: ItemNearbyHouseCardBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(item: HouseWithDistance) {
            val house = item.house
            binding.tvNearbyTitle.text = house.title ?: house.community ?: "Unknown"
            binding.tvNearbyLayout.text = buildLayoutText(house)
            binding.tvNearbyPrice.text = formatPrice(house.totalPrice)+"万"
            binding.tvNearbyArea.text = house.area?.let { String.format("%sm²", it) } ?: ""
            binding.tvNearbyDistanceTag.text = item.distanceText

            binding.root.setOnClickListener { onItemClick(item) }
        }
    }

    private fun buildLayoutText(house: com.example.tenancy.data.model.HouseItem): String {
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
