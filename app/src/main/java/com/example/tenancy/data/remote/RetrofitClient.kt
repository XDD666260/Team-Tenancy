package com.example.tenancy.data.remote

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Retrofit网络单例
 */
object RetrofitClient {

    private const val TAG = "RetrofitClient"

    // 模拟器用 10.0.2.2，真机用电脑局域网IP
    private const val BASE_URL = "https://stallion-pointy-ensure.ngrok-free.dev/"
    //private const val BASE_URL = "http://192.168.1.100:8000/"

    private val okHttpClient: OkHttpClient by lazy {
        val logging = HttpLoggingInterceptor { message ->
            Log.d(TAG, message)
        }.apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        OkHttpClient.Builder()
            .addInterceptor(logging)
            // ngrok免费隧道必须跳过浏览器警告页，否则所有请求被拦截
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .header("ngrok-skip-browser-warning", "true")
                    .build()
                chain.proceed(request)
            }
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .build()
    }

    private val retrofit: Retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val apiService: ApiService by lazy {
        retrofit.create(ApiService::class.java)
    }
}
