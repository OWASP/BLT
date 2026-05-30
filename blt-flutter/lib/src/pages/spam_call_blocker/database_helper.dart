import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class DatabaseHelper {
  static Database? _database;
  
  // Create a singleton pattern
  static Future<Database> get database async {
    if (_database != null) return _database!;
    
    // If the database doesn't exist, create it
    _database = await _initDB();
    return _database!;
  }
  
  // Initialize the database
  static Future<Database> _initDB() async {
    String path = join(await getDatabasesPath(), 'spam_numbers.db');
    
    return await openDatabase(
      path,
      onCreate: (db, version) {
        return db.execute(
          'CREATE TABLE numbers(id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT)',
        );
      },
      version: 1,
    );
  }
  
  // Insert a number into the database
  static Future<void> insertNumber(String number) async {
    final db = await database;
    await db.insert(
      'numbers',
      {'number': number},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }
  
  // Get all numbers from the database
  static Future<List<String>> getNumbers() async {
    final db = await database;
    final List<Map<String, dynamic>> maps = await db.query('numbers');
    
    return List.generate(maps.length, (i) {
      return maps[i]['number'] as String;
    });
  }
  
  // Delete a number from the database
  static Future<void> deleteNumber(String number) async {
    final db = await database;
    await db.delete(
      'numbers',
      where: 'number = ?',
      whereArgs: [number],
    );
  }
}
