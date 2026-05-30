//
//  SpamManager.swift
//  Shared
//
//  Created by Krrish Sehgal on 21/11/24.
//

import Foundation

public class SpamNumberManager {
    // Public initializer to allow usage outside the module
    public init() {}

    // Public shared instance
    public static let shared = SpamNumberManager()
    
    // Use Set<String> for unique phone numbers
    public var spamNumbers: Set<String> = []

    // Update spam list and save it to shared container
    public func updateSpamList(_ numbers: [String]) {
        spamNumbers.removeAll()
        spamNumbers.formUnion(numbers)
        print("Spam list updated: \(spamNumbers)")

        saveSpamList()
    }

    // Save the updated spam list to the shared container
    private func saveSpamList() {
        guard let fileURL = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: "group.com.apps.blt.shared")?.appendingPathComponent("spamNumbers.json") else {
            print("Failed to get file URL for shared container.")
            return
        }
        
        do {
            let data = try JSONEncoder().encode(Array(spamNumbers)) // Convert Set to Array for encoding
            try data.write(to: fileURL)
            print("Spam list saved successfully.")
        } catch {
            print("Error saving spam list: \(error)")
        }
    }

    // Load the spam list from the shared container
    public func loadSpamList() {
        print("in load spam list");
        guard let fileURL = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: "group.com.apps.blt.shared")?.appendingPathComponent("spamNumbers.json") else {
            print("Failed to get file URL for shared container.")
            return
        }
        
        do {
            let data = try Data(contentsOf: fileURL)
            let savedNumbers = try JSONDecoder().decode([String].self, from: data)
            spamNumbers = Set(savedNumbers) // Convert back to Set
            print("Spam list loaded successfully.")
        } catch {
            print("Error loading spam list: \(error)")
        }
    }

    // Check if a number is in the spam list
    public func isSpamNumber(_ number: String) -> Bool {
        return spamNumbers.contains(number)
    }
}
