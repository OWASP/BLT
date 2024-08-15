import 'package:blt/src/pages/pages_import.dart';
import 'package:blt/src/pages/sizzle/sizzle_state_provider.dart';
import 'package:http/http.dart' as http;

// Define a provider for storing the username

class SizzleLogin extends ConsumerStatefulWidget {
  const SizzleLogin({Key? key}) : super(key: key);

  @override
  _SizzleLoginState createState() => _SizzleLoginState();
}

class _SizzleLoginState extends ConsumerState<SizzleLogin> {
  final TextEditingController _usernameController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Optionally preload data or perform initial checks
  }

  void _saveUsername() async {
    final String username = _usernameController.text
        .trim(); // Trim to remove any leading/trailing spaces

    if (username.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Username cannot be empty!'),
      ));
      return;
    }

    final response =
        await http.get(Uri.parse('https://api.github.com/users/$username'));

    if (response.statusCode == 200) {
      // User exists on GitHub
      ref.read(usernameProvider.notifier).state = username;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Username saved successfully!'),
      ));
    } else if (response.statusCode == 404) {
      // User does not exist on GitHub
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Username does not exist on GitHub.'),
      ));
    } else {
      // Other issues (network error, server error, etc.)
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Failed to verify username. Please try again.'),
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final storedUsername = ref.watch(usernameProvider);

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      extendBodyBehindAppBar: true,
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          Container(
            width: size.width,
            height: size.height,
            color:
                isDarkMode ? Color.fromRGBO(34, 22, 23, 1) : Color(0xFFDC4654),
          ),
          Positioned(
            bottom: 0,
            child: Container(
              width: size.width,
              height: size.height * 0.65,
              decoration: BoxDecoration(
                color: isDarkMode
                    ? Color.fromRGBO(42, 38, 38, 1)
                    : Theme.of(context).canvasColor,
                boxShadow: [
                  BoxShadow(
                    spreadRadius: 10,
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 50,
                  )
                ],
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(50),
                  topRight: Radius.circular(50.0),
                ),
              ),
              child: Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: size.width * 0.1),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (storedUsername == null) ...[
                        TextField(
                          controller: _usernameController,
                          decoration: InputDecoration(
                            labelText: 'Enter GitHub Username',
                            border: OutlineInputBorder(),
                          ),
                        ),
                        SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: _saveUsername,
                          style: ButtonStyle(
                            elevation: WidgetStateProperty.all(8),
                            shadowColor: WidgetStateProperty.all(
                              Colors.black.withOpacity(0.5),
                            ),
                            shape:
                                WidgetStateProperty.all<RoundedRectangleBorder>(
                              RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(15.0),
                              ),
                            ),
                            backgroundColor: WidgetStateProperty.all(
                              isDarkMode
                                  ? Color.fromRGBO(83, 49, 52, 1)
                                  : Color(0xFFDC4654),
                            ),
                          ),
                          child: Text(
                            'Add Username',
                            style: TextStyle(color: Colors.white),
                          ),
                        ),
                      ] else ...[
                        Text(
                          'Welcome back, $storedUsername!',
                          style: GoogleFonts.ubuntu(
                              fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                        SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: () {
                            Navigator.pushNamed(
                                context, RouteManager.sizzleHome);
                          },
                          style: ButtonStyle(
                            backgroundColor: WidgetStateProperty.all(
                              isDarkMode
                                  ? Color.fromRGBO(10, 37, 157, 1)
                                  : Color.fromARGB(255, 5, 143, 255),
                            ),
                          ),
                          child: Text('Start Work',
                              style: TextStyle(color: Colors.white)),
                        ),
                        SizedBox(height: 10),
                        ElevatedButton(
                          onPressed: () {
                            // Add your logic for logging out here
                            ref.read(usernameProvider.notifier).state =
                                null; // Clear the username
                            Navigator.of(context)
                                .pop(); // Optionally navigate back or to another screen
                          },
                          style: ButtonStyle(
                            backgroundColor: WidgetStateProperty.all(
                              isDarkMode
                                  ? Color.fromRGBO(83, 49, 52, 1)
                                  : Color(0xFFDC4654),
                            ),
                          ),
                          child: Text('Logout Sizzle',
                              style: TextStyle(color: Colors.white)),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
