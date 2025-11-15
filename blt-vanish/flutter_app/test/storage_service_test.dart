import 'package:flutter_test/flutter_test.dart';
import 'package:selferase/services/storage_service.dart';
import 'package:selferase/models/user_data.dart';
import 'package:uuid/uuid.dart';

void main() {
  group('StorageService', () {
    late StorageService storageService;

    setUp(() {
      storageService = StorageService();
    });

    tearDown(() async {
      // Clean up after each test
      await storageService.clearAllData();
    });

    test('should encrypt and decrypt user data', () async {
      // Arrange
      await storageService.initialize();
      
      final userData = UserData(
        id: const Uuid().v4(),
        firstName: 'Test',
        lastName: 'User',
        emails: ['test@example.com'],
        phoneNumbers: ['555-0100'],
        addresses: [],
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      // Act
      await storageService.saveUserData(userData);
      final retrieved = await storageService.getUserData();

      // Assert
      expect(retrieved, isNotNull);
      expect(retrieved?.firstName, equals('Test'));
      expect(retrieved?.lastName, equals('User'));
      expect(retrieved?.emails.first, equals('test@example.com'));
    });

    test('should handle empty data gracefully', () async {
      // Arrange
      await storageService.initialize();

      // Act
      final userData = await storageService.getUserData();

      // Assert
      expect(userData, isNull);
    });

    test('should export and import data', () async {
      // Arrange
      await storageService.initialize();
      
      final userData = UserData(
        id: const Uuid().v4(),
        firstName: 'Export',
        lastName: 'Test',
        emails: ['export@example.com'],
        phoneNumbers: [],
        addresses: [],
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      await storageService.saveUserData(userData);

      // Act - Export
      final exportedData = await storageService.exportData();
      expect(exportedData, isNotEmpty);

      // Clear data
      await storageService.clearAllData();
      await storageService.initialize();

      // Act - Import
      await storageService.importData(exportedData);
      final imported = await storageService.getUserData();

      // Assert
      expect(imported, isNotNull);
      expect(imported?.firstName, equals('Export'));
      expect(imported?.lastName, equals('Test'));
    });

    test('should maintain data integrity across operations', () async {
      // Arrange
      await storageService.initialize();
      
      final testData = UserData(
        id: const Uuid().v4(),
        firstName: 'Integrity',
        lastName: 'Test',
        emails: ['integrity@example.com'],
        phoneNumbers: ['555-0123'],
        addresses: [
          Address(
            street: '123 Test St',
            city: 'Test City',
            state: 'TS',
            zipCode: '12345',
          ),
        ],
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      // Act
      await storageService.saveUserData(testData);
      final retrieved1 = await storageService.getUserData();
      
      // Modify and save again
      final modified = UserData(
        id: testData.id,
        firstName: 'Modified',
        lastName: testData.lastName,
        emails: testData.emails,
        phoneNumbers: testData.phoneNumbers,
        addresses: testData.addresses,
        createdAt: testData.createdAt,
        updatedAt: DateTime.now(),
      );
      
      await storageService.saveUserData(modified);
      final retrieved2 = await storageService.getUserData();

      // Assert
      expect(retrieved1?.firstName, equals('Integrity'));
      expect(retrieved2?.firstName, equals('Modified'));
      expect(retrieved2?.id, equals(testData.id));
      expect(retrieved2?.addresses.length, equals(1));
    });
  });
}
