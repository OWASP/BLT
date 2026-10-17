import 'package:blt/src/pages/pages_import.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:blt/src/pages/sizzle/sizzle_state_provider.dart';
import 'package:blt/src/pages/sizzle/sizzle_timer.dart';
import 'dart:async';
import 'package:awesome_notifications/awesome_notifications.dart'; //Added for awesome notifications
import 'package:local_notifier/local_notifier.dart';

class SizzleHome extends ConsumerStatefulWidget {
  const SizzleHome({Key? key}) : super(key: key);

  @override
  _SizzleHomeState createState() => _SizzleHomeState();
}

class _SizzleHomeState extends ConsumerState<SizzleHome>
    with WidgetsBindingObserver {
  String? selectedIssueUrl; // Added to track selected issue's URL
  bool isTimerRunning = false; // Added to track the timer state
  int? timeLogId; // Added to store the ID returned when the timer starts
  String? selectedIssueId; // Added to track selected issue's ID
  String apiBaseUrl = GeneralEndPoints
      .apiBaseUrl; // Updated to use the correct apiBaseUrl variable
  Timer? _timer; //Added for managing the timer

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    AwesomeNotifications().isNotificationAllowed().then((isAllowed) {
      if (!isAllowed) {
        AwesomeNotifications().requestPermissionToSendNotifications();
      }
    });

    _initializeNotifications(); //Initialize awesome notifications
  }

  @override
  void dispose() async {
    WidgetsBinding.instance.removeObserver(this);
    _cancelTimer(); //Cancel the timer when disposing
    if (isTimerRunning) {
      await stopTimer(); // Await the stopTimer to ensure the request completes before disposing
    }
    super.dispose();
  }

  void _initializeNotifications() {
    if (Platform.isMacOS || Platform.isWindows || Platform.isLinux) {
      _initializeDesktopNotifications();
    } else {
      AwesomeNotifications().initialize(
        null, //Notification icon
        [
          NotificationChannel(
            channelKey: 'sizzle_timer_channel',
            channelName: 'Sizzle Timer Notifications',
            channelDescription:
                'Notifications for Sizzle Timer', //Added channel description
            defaultColor: Color(0xFFFD5D00),
            importance: NotificationImportance.High,
            channelShowBadge: true,
          )
        ],
        channelGroups: [
          NotificationChannelGroup(
            channelGroupKey: 'sizzle_timer_group',
            channelGroupName: 'sizzle Timer Group', //Added channel group name
          )
        ],
        debug: true,
      );
    }
  }

  Future<void> _showNotification() async {
    if (Platform.isMacOS || Platform.isWindows || Platform.isLinux) {
      await _showDesktopNotification();
    } else {
      AwesomeNotifications().createNotification(
        content: NotificationContent(
          id: 14,
          channelKey: 'sizzle_timer_channel',
          title: 'Timer Stopped',
          body: 'The timer has stopped. Are you still working?',
          notificationLayout: NotificationLayout.Default,
        ),
      );
    }
  }

  void _initializeDesktopNotifications() async {
    await localNotifier.setup(
      appName: 'Sizzle Timer', // Set your app name
      shortcutPolicy:
          ShortcutPolicy.requireCreate, // Relevant mainly for Windows
    );
  }

  Future<void> _showDesktopNotification() async {
    LocalNotification notification = LocalNotification(
      title: 'Timer Stopped',
      body: 'The timer has stopped. Are you still working?',
    );

    await notification.show();
  }

  @override
  Widget build(BuildContext context) {
    final username = ref.watch(usernameProvider);
    final ThemeData theme = Theme.of(context);
    bool isDarkMode = theme.brightness == Brightness.dark;

    Future<bool> launchConfirmationDialog(BuildContext context) async {
      return await showDialog<bool>(
            context: context,
            builder: (BuildContext context) {
              return AlertDialog(
                title: const Text('Warning'),
                content: const Text(
                    'This process will stop your tracking. Do you want to continue?'),
                actions: <Widget>[
                  TextButton(
                    onPressed: () {
                      Navigator.pop(
                          context, false); // Close the dialog and return false
                    },
                    child: const Text('Cancel'),
                  ),
                  TextButton(
                    onPressed: () {
                      Navigator.pop(
                          context, true); // Close the dialog and return true
                    },
                    child: const Text('Yes'),
                  ),
                ],
              );
            },
          ) ??
          false; // Return false if the dialog is dismissed without a selection
    }

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (bool didPop, Object? result) async {
        if (isTimerRunning) {
          WidgetsBinding.instance.addPostFrameCallback((_) async {
            bool isPop = await launchConfirmationDialog(context);
            if (isPop) {
              await stopTimer();
            }
          });
        }
        if (!didPop && !isTimerRunning) {
          Navigator.of(context).pop();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: isTimerRunning
              ? Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                        '#$selectedIssueId'), // Show issue ID when timer is running
                    TimerWidget(), // Display the timer in the AppBar
                  ],
                )
              : Text('Welcome $username'),
        ),
        body: isTimerRunning
            ? Center(
                child: Container(
                  color: theme
                      .scaffoldBackgroundColor, // Set the background color to match the theme
                  alignment: Alignment.center,
                  child: Text(
                    'Sizzle is running. Click on stop to continue.',
                    style: TextStyle(
                      fontSize: 20, // Increase the font size
                      fontWeight: FontWeight.bold, // Make the text bold
                      color: isDarkMode
                          ? Colors.white
                          : Colors.black, // Adjust text color based on theme
                    ),
                    textAlign: TextAlign.center, // Center the text
                  ),
                ),
              )
            : FutureBuilder(
                future: _fetchIssues(
                    username!), // Updated to call the newly added _fetchIssues method
                builder: (context, AsyncSnapshot<List<dynamic>> snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return Center(
                        child:
                            CircularProgressIndicator()); // Minor adjustment to the loading indicator placement
                  } else if (snapshot.hasError) {
                    return Center(
                        child: Text(
                            'Error: ${snapshot.error}')); // Minor adjustment to error message display
                  } else if (snapshot.data == null || snapshot.data!.isEmpty) {
                    return Center(
                        child: Text(
                            'Please assign an issue for you.')); // Slightly modified the no-data message
                  } else {
                    return ListView.builder(
                      itemCount: snapshot.data!.length,
                      itemBuilder: (context, index) {
                        var issue = snapshot.data![index];
                        bool isSelected = issue['html_url'] ==
                            selectedIssueUrl; // Added check to see if the issue is selected

                        return Card(
                          color: isSelected
                              ? isDarkMode
                                  ? Color.fromRGBO(100, 20, 40,
                                      1) // Dark mode selected background
                                  : Color
                                      .fromRGBO(180, 70, 70,
                                          1) // Light mode selected background
                              : isDarkMode
                                  ? Color.fromRGBO(126, 33, 58,
                                      1) // Original dark mode background color
                                  : Color(
                                      0xFFDC4654), // Original light mode background color
                          child: ListTile(
                            title: Text(issue['title'],
                                style: TextStyle(color: Colors.white)),
                            subtitle: Text(
                                'Repo: ${issue['repository_url'].split('/').last}\n'
                                'ID: ${issue['number']}\n'
                                'Created: ${issue['created_at']}',
                                style: TextStyle(color: Colors.white70)),
                            onTap: () {
                              setState(() {
                                selectedIssueUrl = isSelected
                                    ? null
                                    : issue[
                                        'html_url']; // Added logic to select/deselect issue
                                selectedIssueId = isSelected
                                    ? null
                                    : issue['number']
                                        .toString(); // Track the selected issue's ID
                              });
                            },
                          ),
                        );
                      },
                    );
                  }
                },
              ),
        floatingActionButton: FloatingActionButton(
          onPressed: isTimerRunning
              ? stopTimer
              : startTimer, // Added logic to start/stop the timer
          child: Icon(isTimerRunning
              ? Icons.stop
              : Icons.play_arrow), // Updated icon based on timer state
          backgroundColor: isDarkMode ? Colors.black : Colors.white,
        ),
      ),
    );
  }

  Future<void> startTimer() async {
    if (selectedIssueUrl == null) return;

    selectedIssueId = selectedIssueUrl!.split('/').last;

    final response = await http.post(
      Uri.parse('$apiBaseUrl' +
          'timelogs/start/'), // Updated to use the correct $apiBaseUrl variable
      body: json.encode({
        "github_issue_url": selectedIssueUrl,
      }),
      headers: {
        'Content-Type': 'application/json',
        'Authorization':
            'Token ${currentUser?.token}', // Added Authorization header with auth token
      },
    );

    if (response.statusCode == 201) {
      final data = json.decode(response.body);
      if (mounted) {
        setState(() {
          timeLogId = data['id']; // Store the returned time log ID
          isTimerRunning =
              true; // Update the state to indicate the timer is running
          _startCountdownTimer(); //Start the countdown for 5 minutes
        });
      }
    } else {
      // Added error handling for failed timer start
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to start timer')),
        );
      }
    }
  }

  void _startCountdownTimer() {
    _cancelTimer(); //Cancel any existing timer
    _timer = Timer(Duration(minutes: 30), () async {
      await stopTimer(); //Automatically stop the timer after 5 minutes
      await _showNotification(); //Show a notification to remind the user
    });
  }

  void _cancelTimer() {
    _timer?.cancel(); //Cancel the timer
    _timer = null;
  }

  Future<void> stopTimer() async {
    if (timeLogId == null) return;

    final response = await http.post(
      Uri.parse('$apiBaseUrl' +
          'timelogs/$timeLogId/stop/'), // Updated to use the correct $apiBaseUrl variable
      headers: {
        'Content-Type': 'application/json',
        'Authorization':
            'Token ${currentUser?.token}', // Added Authorization header with auth token
      },
    );

    if (response.statusCode == 200) {
      if (mounted) {
        setState(() {
          isTimerRunning =
              false; // Update the state to indicate the timer has stopped
          timeLogId = null; // Clear the time log ID
          selectedIssueId = null; // Clear the selected issue ID
          _cancelTimer(); //Cancel the countdown timer
        });
      }
    } else {
      // Added error handling for failed timer stop
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to stop timer')),
        );
      }
    }
  }

  Future<List<dynamic>> _fetchIssues(String username) async {
    final response = await http.get(
      Uri.parse(
          'https://api.github.com/search/issues?q=assignee:$username+state:open'),
    );

    if (response.statusCode == 200) {
      return json.decode(response.body)['items'];
    } else {
      throw Exception('Failed to load issues from GitHub');
    }
  }
}
