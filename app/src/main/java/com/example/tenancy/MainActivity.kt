package com.example.tenancy

import android.os.Bundle
import android.view.MenuItem
import android.view.View
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.ActionBarDrawerToggle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.GravityCompat
import androidx.drawerlayout.widget.DrawerLayout
import com.example.tenancy.ui.chart.ChartFragment
import com.example.tenancy.ui.filter.FilterFragment
import com.example.tenancy.ui.home.HomeFragment
import com.example.tenancy.ui.map.MapFragment
import com.google.android.material.navigation.NavigationView

class MainActivity : AppCompatActivity() {

    private lateinit var drawerLayout: DrawerLayout
    private lateinit var navigationView: NavigationView
    private lateinit var mainContent: View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        drawerLayout = findViewById(R.id.drawerLayout)
        navigationView = findViewById(R.id.navigationView)
        mainContent = findViewById(R.id.mainContent)
        val toolbar = findViewById<com.google.android.material.appbar.MaterialToolbar>(R.id.toolbar)

        // 取消遮罩层变灰
        drawerLayout.setScrimColor(android.graphics.Color.TRANSPARENT)

        // DrawerToggle
        val toggle = ActionBarDrawerToggle(
            this,
            drawerLayout,
            toolbar,
            R.string.navigation_drawer_open,
            R.string.navigation_drawer_close
        )
        drawerLayout.addDrawerListener(toggle)
        toggle.syncState()

        // 主界面平移 + 缩小：侧边栏滑动时同步动画
        drawerLayout.addDrawerListener(object : DrawerLayout.SimpleDrawerListener() {

            private var pivotInitialized = false

            override fun onDrawerSlide(drawerView: View, slideOffset: Float) {
                if (!pivotInitialized && mainContent.width > 0) {
                    mainContent.pivotX = mainContent.width / 2f
                    mainContent.pivotY = mainContent.height / 2f
                    pivotInitialized = true
                }

                val drawerWidth = drawerView.width
                mainContent.translationX = drawerWidth * slideOffset
                val scale = 1f - (0.2f * slideOffset)
                mainContent.scaleX = scale
                mainContent.scaleY = scale
            }
        })

        // 加载 HomeFragment 到 contentFrame
        if (savedInstanceState == null) {
            navigationView.setCheckedItem(R.id.nav_home)
            supportFragmentManager.beginTransaction()
                .replace(R.id.contentFrame, HomeFragment())
                .commit()
        }

        // 侧边栏菜单点击
        navigationView.setNavigationItemSelectedListener { menuItem: MenuItem ->
            drawerLayout.closeDrawer(GravityCompat.START)
            when (menuItem.itemId) {
                R.id.nav_home -> {
                    supportFragmentManager.beginTransaction()
                        .replace(R.id.contentFrame, HomeFragment())
                        .commit()
                    true
                }
                R.id.nav_map -> {
                    supportFragmentManager.beginTransaction()
                        .replace(R.id.contentFrame, MapFragment())
                        .commit()
                    true
                }
                R.id.nav_chart -> {
                    supportFragmentManager.beginTransaction()
                        .replace(R.id.contentFrame, ChartFragment())
                        .commit()
                    true
                }
                R.id.nav_filter -> {
                    supportFragmentManager.beginTransaction()
                        .replace(R.id.contentFrame, FilterFragment())
                        .commit()
                    true
                }
                R.id.nav_about ->
                    Toast.makeText(this, "About Us", Toast.LENGTH_SHORT).show()
                R.id.nav_feedback ->
                    Toast.makeText(this, "Send Feedbacks", Toast.LENGTH_SHORT).show()
            }
            true
        }

        // 返回键处理
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (drawerLayout.isDrawerOpen(GravityCompat.START)) {
                    drawerLayout.closeDrawer(GravityCompat.START)
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })
    }
}
