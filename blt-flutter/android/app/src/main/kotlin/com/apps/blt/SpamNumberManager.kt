package com.apps.blt

import kotlin.collections.mutableSetOf

object SpamNumberManager {
    private val spamNumbers = mutableSetOf<String>()

    fun updateSpamList(numbers: List<String>) {
        spamNumbers.clear()
        spamNumbers.addAll(numbers)
    }

    fun isSpamNumber(number: String): Boolean {
        return spamNumbers.contains(number)
    }
}
