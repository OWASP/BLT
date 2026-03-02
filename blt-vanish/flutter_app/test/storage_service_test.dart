import 'package:flutter_test/flutter_test.dart';
import 'package:selferase/services/storage_service.dart';
import 'package:selferase/models/user_data.dart';
import 'package:selferase/models/monitor_entry.dart';
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

    group('MonitorEntry', () {
      test('should save and retrieve monitor entries', () async {
        // Arrange
        await storageService.initialize();
        final now = DateTime.now();

        final entry = MonitorEntry(
          id: const Uuid().v4(),
          keyword: 'John Doe',
          type: MonitorType.keyword,
          isActive: true,
          createdAt: now,
          updatedAt: now,
        );

        // Act
        await storageService.saveMonitorEntry(entry);
        final entries = await storageService.getMonitorEntries();

        // Assert
        expect(entries.length, equals(1));
        expect(entries.first.keyword, equals('John Doe'));
        expect(entries.first.type, equals(MonitorType.keyword));
        expect(entries.first.isActive, isTrue);
      });

      test('should update existing monitor entry', () async {
        // Arrange
        await storageService.initialize();
        final now = DateTime.now();
        final id = const Uuid().v4();

        final entry = MonitorEntry(
          id: id,
          keyword: 'test keyword',
          type: MonitorType.personalInfo,
          isActive: true,
          createdAt: now,
          updatedAt: now,
        );

        await storageService.saveMonitorEntry(entry);

        // Act - update the entry
        final updated = entry.copyWith(isActive: false, updatedAt: DateTime.now());
        await storageService.saveMonitorEntry(updated);
        final entries = await storageService.getMonitorEntries();

        // Assert - should still be one entry, but updated
        expect(entries.length, equals(1));
        expect(entries.first.id, equals(id));
        expect(entries.first.isActive, isFalse);
      });

      test('should delete a monitor entry', () async {
        // Arrange
        await storageService.initialize();
        final now = DateTime.now();

        final entry1 = MonitorEntry(
          id: const Uuid().v4(),
          keyword: 'entry one',
          type: MonitorType.keyword,
          isActive: true,
          createdAt: now,
          updatedAt: now,
        );
        final entry2 = MonitorEntry(
          id: const Uuid().v4(),
          keyword: 'entry two',
          type: MonitorType.takedown,
          isActive: true,
          createdAt: now,
          updatedAt: now,
        );

        await storageService.saveMonitorEntry(entry1);
        await storageService.saveMonitorEntry(entry2);

        // Act
        await storageService.deleteMonitorEntry(entry1.id);
        final entries = await storageService.getMonitorEntries();

        // Assert
        expect(entries.length, equals(1));
        expect(entries.first.keyword, equals('entry two'));
      });

      test('should return empty list when no monitor entries', () async {
        // Arrange
        await storageService.initialize();

        // Act
        final entries = await storageService.getMonitorEntries();

        // Assert
        expect(entries, isEmpty);
      });

      test('should include monitor entries in export/import', () async {
        // Arrange
        await storageService.initialize();
        final now = DateTime.now();

        final entry = MonitorEntry(
          id: const Uuid().v4(),
          keyword: 'export test',
          type: MonitorType.takedown,
          isActive: true,
          createdAt: now,
          updatedAt: now,
          notes: 'test notes',
        );

        await storageService.saveMonitorEntry(entry);

        // Act - export
        final exported = await storageService.exportData();
        expect(exported, isNotEmpty);

        // Clear and reimport
        await storageService.clearAllData();
        await storageService.initialize();
        await storageService.importData(exported);

        final entries = await storageService.getMonitorEntries();

        // Assert
        expect(entries.length, equals(1));
        expect(entries.first.keyword, equals('export test'));
        expect(entries.first.type, equals(MonitorType.takedown));
        expect(entries.first.notes, equals('test notes'));
      });
    });
  });
}
