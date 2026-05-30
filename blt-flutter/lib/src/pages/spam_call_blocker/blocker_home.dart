import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'database_helper.dart'; // Your DatabaseHelper class for SQLite operations

class SpamCallBlockerPage extends StatefulWidget {
  @override
  _SpamCallBlockerPageState createState() => _SpamCallBlockerPageState();
}

class _SpamCallBlockerPageState extends State<SpamCallBlockerPage> {
  final List<String> _numbers = [];
  final TextEditingController _controller = TextEditingController();
  static const platform = MethodChannel('com.apps.blt/channel'); // MethodChannel for native communication

  @override
  void initState() {
    super.initState();
    _loadNumbers();
  }

  Future<void> _loadNumbers() async {
    try {
      final numbers = await DatabaseHelper.getNumbers();
      setState(() {
        _numbers.clear();
        _numbers.addAll(numbers);
      });
      _sendSpamListToNative(); 
    } catch (e) {
      _showError("Failed to load numbers: $e");
    }
  }

  Future<void> _addNumber() async {
    final newNumber = _controller.text.trim();
    if (newNumber.isEmpty || !_validatePhoneNumber(newNumber)) {
      _showError("Please enter a valid phone number.");
      return;
    }

    if (_numbers.contains(newNumber)) {
      _showError("This number is already in the list.");
      return;
    }

    setState(() {
      _numbers.add(newNumber);
      _controller.clear();
    });

    try {
      await DatabaseHelper.insertNumber(newNumber);
      _sendSpamListToNative();
    } catch (e) {
      _showError("Failed to add number: $e");
    }
  }

  Future<void> _removeNumber(String number) async {
    setState(() {
      _numbers.remove(number);
    });

    try {
      await DatabaseHelper.deleteNumber(number);
      _sendSpamListToNative();
    } catch (e) {
      _showError("Failed to remove number: $e");
    }
  }

  Future<void> _sendSpamListToNative() async {
    try {
      var response = await platform.invokeMethod('updateSpamList', {
        'numbers': _numbers,
      });
      print(response);
    } catch (e) {
      _showError("Failed to update spam list on the native side: $e");
    }
  }

  bool _validatePhoneNumber(String number) {
    final regex = RegExp(r'^\+?[0-9]{10,15}$'); // Allows country code (e.g., +91)
    return regex.hasMatch(number);
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Spam Call Blocker'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            // Input Field for Adding Numbers
            TextField(
              controller: _controller,
              decoration: InputDecoration(
                labelText: 'Enter number',
                border: OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: Icon(Icons.add),
                  onPressed: _addNumber,
                ),
              ),
              keyboardType: TextInputType.phone,
            ),
            SizedBox(height: 20),
            Expanded(
              child: _numbers.isEmpty
                  ? Center(child: Text("No numbers added."))
                  : ListView.builder(
                      itemCount: _numbers.length,
                      itemBuilder: (context, index) {
                        return ListTile(
                          title: Text(
                            _numbers[index],
                            style: TextStyle(fontSize: 16),
                          ),
                          trailing: IconButton(
                            icon: Icon(Icons.remove_circle, color: Colors.red),
                            onPressed: () => _removeNumber(_numbers[index]),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
