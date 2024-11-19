package com.apps.blt

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
