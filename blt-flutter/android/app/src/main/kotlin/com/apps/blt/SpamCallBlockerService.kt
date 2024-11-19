package com.apps.blt

import android.telecom.CallScreeningService
import android.telecom.Call
import android.util.Log
import org.greenrobot.eventbus.EventBus
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import android.net.Uri

class MessageEvent(val message: String) {}

class SpamCallBlockerService : CallScreeningService() {
    private val notificationManager = NotificationManagerImpl()

    override fun onCreate() {
        super.onCreate()
        Log.d("SpamCallBlockerService", "Service started")
    }

    override fun onScreenCall(callDetails: Call.Details) {
        Log.d("SpamCallBlockerService", "onScreenCall triggered")
        val phoneNumber = getPhoneNumber(callDetails)
        Log.d("SpamCallBlockerService", "Intercepted call from: $phoneNumber")
        var response = CallResponse.Builder()
        response = handlePhoneCall(response, phoneNumber)
        
        respondToCall(callDetails, response.build())
        logCallInterception(phoneNumber, response.build())
    }

    private fun handlePhoneCall(
        response: CallResponse.Builder,
        phoneNumber: String
    ): CallResponse.Builder {
        if (SpamNumberManager.isSpamNumber(phoneNumber)) {
            response.apply {
                setRejectCall(true)
                setDisallowCall(true)
                setSkipCallLog(false)
                displayToast(String.format("Rejected call from %s", phoneNumber))
            }
        } else {
            displayToast(String.format("Incoming call from %s", phoneNumber))
        }
        return response
    }

    private fun getPhoneNumber(callDetails: Call.Details): String {
        return callDetails.handle.toString().removeTelPrefix().parseCountryCode()
    }

    private fun displayToast(message: String) {
        notificationManager.showToastNotification(applicationContext, message)
        EventBus.getDefault().post(MessageEvent(message))
    }

    private fun logCallInterception(phoneNumber: String, response: CallResponse) {
        val currentTime = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
        val action = "action"
        val logMessage = "[$currentTime] $action call from $phoneNumber"
        Log.d("SpamCallBlockerService", logMessage)
    }

    fun String.removeTelPrefix() = this.replace("tel:", "")
    fun String.parseCountryCode(): String = Uri.decode(this)
}
