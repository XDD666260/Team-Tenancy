package com.example.tenancy.ui.map

import android.annotation.SuppressLint
import android.os.Bundle
import android.util.Base64
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.webkit.ConsoleMessage
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.tenancy.R
import com.example.tenancy.databinding.FragmentMapBinding
import com.google.android.material.chip.Chip
import kotlinx.coroutines.launch

class MapFragment : Fragment() {

    companion object {
        private const val TAG = "MapFragment"
    }

    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!

    private val viewModel: MapViewModel by viewModels()

    private var isWebViewReady = false
    private var pendingPointsB64: String? = null
    private var pendingDistrictsB64: String? = null
    private var pendingFilter: String? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentMapBinding.inflate(inflater, container, false)
        return binding.root
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        setupWebView()
        observeState()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val wv = binding.webView
        wv.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            setGeolocationEnabled(true)
            mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
        }

        wv.addJavascriptInterface(AndroidBridge(), "Android")

        wv.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                Log.d(TAG, "WebView page finished, ready to flush data")
                isWebViewReady = true
                flushPendingData()
            }

            override fun onReceivedError(
                view: WebView?,
                errorCode: Int,
                description: String?,
                failingUrl: String?
            ) {
                Log.e(TAG, "WebView error: $errorCode $description $failingUrl")
            }
        }

        wv.webChromeClient = object : WebChromeClient() {
            override fun onConsoleMessage(msg: ConsoleMessage?): Boolean {
                msg?.let {
                    Log.d("MapWebView", "[${it.messageLevel()}] ${it.message()}")
                }
                return true
            }
        }

        wv.loadUrl("file:///android_asset/map.html")
    }

    private fun flushPendingData() {
        val pointsB64 = pendingPointsB64
        val districtsB64 = pendingDistrictsB64

        if (pointsB64 == null && districtsB64 == null) {
            Log.d(TAG, "flushPendingData: no pending data to push")
            return
        }

        val wv = binding.webView

        districtsB64?.let { b64 ->
            Log.d(TAG, "Pushing districts via Base64, length=${b64.length}")
            wv.evaluateJavascript("loadDistrictsB64('$b64')", null)
        }

        pointsB64?.let { b64 ->
            Log.d(TAG, "Pushing points via Base64, length=${b64.length}")
            wv.evaluateJavascript("loadPointsB64('$b64')", null)
        }

        pendingFilter?.let { district ->
            val escaped = district.replace("'", "\\'")
            wv.evaluateJavascript("filterByDistrict('$escaped')", null)
        }

        pendingPointsB64 = null
        pendingDistrictsB64 = null
        pendingFilter = null
    }

    private fun encodeB64(s: String): String {
        return Base64.encodeToString(s.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)
    }

    private fun observeState() {
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                viewModel.uiState.collect { state ->
                    binding.progressBar.visibility = if (state.isLoading) View.VISIBLE else View.GONE

                    val statsText = getString(
                        R.string.map_stats_format, state.totalCount, state.coordinateCount
                    )
                    binding.tvStats.text = statsText
                    Log.d(TAG, "Stats: total=${state.totalCount}, coords=${state.coordinateCount}, pointsJsonLen=${state.pointsJson.length}")

                    if (state.districts.isNotEmpty()) {
                        updateDistrictChips(state.districts, state.selectedDistrict)
                    }

                    if (state.error != null) {
                        Toast.makeText(requireContext(), state.error, Toast.LENGTH_SHORT).show()
                        Log.e(TAG, "Error: ${state.error}")
                    }

                    pushDataToWebView(state.pointsJson, state.districtsJson, state.selectedDistrict)
                }
            }
        }
    }

    private fun updateDistrictChips(districts: List<String>, selected: String?) {
        val chipGroup = binding.chipGroup
        if (chipGroup.childCount > 0 && chipGroup.childCount == districts.size + 1) {
            updateChipSelection(selected)
            return
        }

        chipGroup.removeAllViews()

        val allChip = Chip(requireContext()).apply {
            text = getString(R.string.map_all_district)
            isCheckable = true
            isChecked = selected.isNullOrBlank()
            setOnClickListener { viewModel.filterByDistrict(null) }
        }
        chipGroup.addView(allChip)

        districts.forEach { district ->
            val chip = Chip(requireContext()).apply {
                text = district
                isCheckable = true
                isChecked = district == selected
                setOnClickListener { viewModel.filterByDistrict(district) }
            }
            chipGroup.addView(chip)
        }
    }

    private fun updateChipSelection(selected: String?) {
        val chipGroup = binding.chipGroup
        for (i in 0 until chipGroup.childCount) {
            val chip = chipGroup.getChildAt(i) as? Chip ?: continue
            if (i == 0) {
                chip.isChecked = selected.isNullOrBlank()
            } else {
                chip.isChecked = chip.text == selected
            }
        }
    }

    private fun pushDataToWebView(pointsJson: String, districtsJson: String, filter: String?) {
        val wv = binding.webView
        val pointsB64 = encodeB64(pointsJson)
        val districtsB64 = encodeB64(districtsJson)

        if (isWebViewReady) {
            wv.evaluateJavascript("loadDistrictsB64('$districtsB64')", null)

            if (!filter.isNullOrBlank()) {
                val escaped = filter.replace("'", "\\'")
                wv.evaluateJavascript("filterByDistrict('$escaped')", null)
            }

            wv.evaluateJavascript("loadPointsB64('$pointsB64')", null)
        } else {
            pendingPointsB64 = pointsB64
            pendingDistrictsB64 = districtsB64
            pendingFilter = filter
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        binding.webView.destroy()
        _binding = null
    }

    inner class AndroidBridge {
        @JavascriptInterface
        fun onPointClick(json: String) {}
    }
}