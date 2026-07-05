package com.example.tenancy.ui.filter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.tenancy.R

class ImagePagerAdapter(
    private val context: android.content.Context,
    private val imageUrls: List<String>
) : RecyclerView.Adapter<ImagePagerAdapter.ViewHolder>() {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val imageView = ImageView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            scaleType = ImageView.ScaleType.CENTER_CROP
        }
        return ViewHolder(imageView)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val url = imageUrls[position]
        Glide.with(context)
            .load(url)
            .placeholder(R.drawable.ic_house)
            .error(R.drawable.ic_house)
            .centerCrop()
            .into(holder.imageView)
    }

    override fun getItemCount(): Int = imageUrls.size

    class ViewHolder(val imageView: ImageView) : RecyclerView.ViewHolder(imageView)
}
