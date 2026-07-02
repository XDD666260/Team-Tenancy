package com.example.littlepainter.ui.base

import android.os.Build
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.Window
import androidx.annotation.RequiresApi
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.fragment.app.Fragment
import androidx.viewbinding.ViewBinding
import java.lang.reflect.ParameterizedType

abstract class BaseFragment<T : ViewBinding> : Fragment() {
    //使用_binding在内部保存binding对象
    private lateinit var _binding: T

    //给外部提供一个属性访问这个binding对象
    val mBinding: T
        get() = _binding

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        _binding = initBinding()
        return _binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        initUI(savedInstanceState)
    }

    open fun initUI(savedInstanceState: Bundle?) {
        initKeyboardEvent()
    }

    private fun initBinding(): T {
        // 获取泛型类型
        val type = (javaClass.genericSuperclass as ParameterizedType).actualTypeArguments[0]
        val clazz = type as Class<*>

        // 查找inflate方法
        val method = clazz.getMethod("inflate", LayoutInflater::class.java)
        return method.invoke(null, layoutInflater) as T
    }
    private fun initKeyboardEvent(){
        mBinding.root.setOnClickListener {
            val insets=ViewCompat.getRootWindowInsets(mBinding.root)
            insets?.also {
                if (insets.isVisible(WindowInsetsCompat.Type.ime())){
                    mBinding.root.windowInsetsController?.hide(WindowInsetsCompat.Type.ime())
                }
            }
        }
    }


}