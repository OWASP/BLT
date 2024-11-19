package com.apps.blt

import android.content.Context
import android.os.Looper
import android.widget.Toast
interface NotificationManager {
    fun showToastNotification(context: Context, message: String)
}

class NotificationManagerImpl : NotificationManager {
    override fun showToastNotification(context: Context, message: String) {
        val t = Thread {
            try {
                Looper.prepare()
                Toast.makeText(context.applicationContext, message, Toast.LENGTH_LONG).show()
                Looper.loop()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
        t.start()
    }
}
