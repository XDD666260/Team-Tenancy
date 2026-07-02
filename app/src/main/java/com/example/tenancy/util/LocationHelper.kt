package com.example.tenancy.util

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.google.android.gms.common.ConnectionResult
import com.google.android.gms.common.GoogleApiAvailability
import com.google.android.gms.location.*
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

object LocationHelper {

    private const val TAG = "LocationHelper"
    private const val TIMEOUT_MS = 10_000L

    private var fusedLocationClient: FusedLocationProviderClient? = null

    private fun getFusedClient(context: Context): FusedLocationProviderClient {
        if (fusedLocationClient == null) {
            fusedLocationClient = LocationServices.getFusedLocationProviderClient(context.applicationContext)
        }
        return fusedLocationClient!!
    }

    /**
     * 获取用户位置（带超时）
     * 优先 FusedLocationProvider，不可用时自动 fallback 到 LocationManager
     */
    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocation(context: Context): Location? {
        val appContext = context.applicationContext

        // 检查 Google Play Services 是否可用
        val gpsAvailable = isGooglePlayServicesAvailable(appContext)
        Log.d(TAG, "Google Play Services available: $gpsAvailable")

        if (gpsAvailable) {
            val fusedResult = tryFusedLocation(appContext)
            if (fusedResult != null) {
                Log.d(TAG, "Got location from FusedLocationProvider")
                return fusedResult
            }
            Log.d(TAG, "FusedLocationProvider returned null, falling back")
        } else {
            Log.d(TAG, "Google Play Services unavailable, using LocationManager directly")
        }

        val nativeResult = tryNativeLocation(appContext)
        if (nativeResult != null) {
            Log.d(TAG, "Got location from LocationManager")
            return nativeResult
        }

        Log.w(TAG, "All location providers failed")
        return null
    }

    private fun isGooglePlayServicesAvailable(context: Context): Boolean {
        return try {
            val result = GoogleApiAvailability.getInstance()
                .isGooglePlayServicesAvailable(context)
            result == ConnectionResult.SUCCESS
        } catch (e: Exception) {
            Log.w(TAG, "Error checking Play Services: ${e.message}")
            false
        }
    }

    // ===== FusedLocationProvider =====

    @SuppressLint("MissingPermission")
    private suspend fun tryFusedLocation(context: Context): Location? {
        return suspendCancellableCoroutine { continuation ->
            val handler = Handler(Looper.getMainLooper())
            var resumed = false

            fun resumeOnce(location: Location?) {
                if (!resumed && continuation.isActive) {
                    resumed = true
                    continuation.resume(location)
                }
            }

            val timeoutRunnable = Runnable {
                Log.d(TAG, "FusedLocationProvider timed out")
                resumeOnce(null)
            }
            handler.postDelayed(timeoutRunnable, TIMEOUT_MS)

            try {
                val client = getFusedClient(context)

                client.lastLocation.addOnCompleteListener { task ->
                    if (resumed) return@addOnCompleteListener
                    try {
                        if (task.isSuccessful) {
                            val location = task.result
                            if (location != null) {
                                handler.removeCallbacks(timeoutRunnable)
                                resumeOnce(location)
                                return@addOnCompleteListener
                            }
                        } else {
                            Log.w(TAG, "lastLocation task failed: ${task.exception?.message}")
                        }
                        // 失败或为空 → 请求新鲜定位
                        requestFreshFusedLocation(client, handler, timeoutRunnable, ::resumeOnce)
                    } catch (e: Exception) {
                        Log.w(TAG, "FusedLocation addOnCompleteListener error: ${e.message}")
                        handler.removeCallbacks(timeoutRunnable)
                        resumeOnce(null)
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "FusedLocationProvider init error: ${e.message}")
                handler.removeCallbacks(timeoutRunnable)
                resumeOnce(null)
            }

            continuation.invokeOnCancellation {
                handler.removeCallbacks(timeoutRunnable)
            }
        }
    }

    @SuppressLint("MissingPermission")
    private fun requestFreshFusedLocation(
        client: FusedLocationProviderClient,
        handler: Handler,
        timeoutRunnable: Runnable,
        resume: (Location?) -> Unit
    ) {
        try {
            val locationRequest = LocationRequest.Builder(
                Priority.PRIORITY_HIGH_ACCURACY, 5000
            ).setMinUpdateIntervalMillis(3000).build()

            val callback = object : LocationCallback() {
                override fun onLocationResult(result: LocationResult) {
                    handler.removeCallbacks(timeoutRunnable)
                    client.removeLocationUpdates(this)
                    resume(result.lastLocation)
                }

                override fun onLocationAvailability(availability: LocationAvailability) {
                    if (!availability.isLocationAvailable) {
                        Log.d(TAG, "FusedLocation reports unavailable")
                        handler.removeCallbacks(timeoutRunnable)
                        client.removeLocationUpdates(this)
                        resume(null)
                    }
                }
            }

            client.requestLocationUpdates(locationRequest, callback, Looper.getMainLooper())
        } catch (e: Exception) {
            Log.w(TAG, "requestFreshFusedLocation failed: ${e.message}")
            handler.removeCallbacks(timeoutRunnable)
            resume(null)
        }
    }

    // ===== 原生 LocationManager =====

    @SuppressLint("MissingPermission")
    private suspend fun tryNativeLocation(context: Context): Location? {
        return suspendCancellableCoroutine { continuation ->
            val handler = Handler(Looper.getMainLooper())
            var resumed = false

            fun resumeOnce(location: Location?) {
                if (!resumed && continuation.isActive) {
                    resumed = true
                    continuation.resume(location)
                }
            }

            val timeoutRunnable = Runnable {
                Log.d(TAG, "LocationManager timed out")
                resumeOnce(null)
            }
            handler.postDelayed(timeoutRunnable, TIMEOUT_MS)

            val locationManager =
                context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager
            if (locationManager == null) {
                handler.removeCallbacks(timeoutRunnable)
                resumeOnce(null)
                return@suspendCancellableCoroutine
            }

            // 收集可用 provider
            val candidates = mutableListOf<String>()
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                candidates.add(LocationManager.GPS_PROVIDER)
            }
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                candidates.add(LocationManager.NETWORK_PROVIDER)
            }
            if (candidates.isEmpty()) {
                candidates.addAll(locationManager.getProviders(true))
            }

            if (candidates.isEmpty()) {
                Log.d(TAG, "No location providers enabled")
                handler.removeCallbacks(timeoutRunnable)
                resumeOnce(null)
                return@suspendCancellableCoroutine
            }

            // 先查 lastKnownLocation
            for (provider in candidates) {
                try {
                    val lastKnown = locationManager.getLastKnownLocation(provider)
                    if (lastKnown != null) {
                        handler.removeCallbacks(timeoutRunnable)
                        resumeOnce(lastKnown)
                        return@suspendCancellableCoroutine
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "getLastKnownLocation($provider) failed: ${e.message}")
                }
            }

            // 请求实时更新
            val bestProvider = candidates.first()
            Log.d(TAG, "Requesting updates from $bestProvider")

            val listener = object : LocationListener {
                override fun onLocationChanged(location: Location) {
                    handler.removeCallbacks(timeoutRunnable)
                    try { locationManager.removeUpdates(this) } catch (_: Exception) {}
                    resumeOnce(location)
                }
                @Deprecated("Deprecated in Java")
                override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
                override fun onProviderEnabled(provider: String) {}
                override fun onProviderDisabled(provider: String) {}
            }

            try {
                locationManager.requestLocationUpdates(
                    bestProvider, 3000L, 10f, listener, Looper.getMainLooper()
                )
            } catch (e: Exception) {
                Log.w(TAG, "requestLocationUpdates failed: ${e.message}")
                handler.removeCallbacks(timeoutRunnable)
                resumeOnce(null)
            }

            continuation.invokeOnCancellation {
                handler.removeCallbacks(timeoutRunnable)
                try { locationManager.removeUpdates(listener) } catch (_: Exception) {}
            }
        }
    }
}
