import 'package:blt/src/pages/pages_import.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:blt/src/pages/sizzle/sizzle_state_provider.dart';

class SizzleHome extends ConsumerWidget {
  const SizzleHome({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final username = ref.watch(usernameProvider);
    final ThemeData theme = Theme.of(context);
    bool isDarkMode = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: Text('Welcome $username'),
      ),
      body: FutureBuilder(
        future: _fetchIssues(username!),
        builder: (context, AsyncSnapshot<List<dynamic>> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(
                child:
                    CircularProgressIndicator()); // Centered loading indicator
          } else if (snapshot.hasError) {
            return Center(
                child:
                    Text('Error: ${snapshot.error}')); // Centered error message
          } else if (snapshot.data == null || snapshot.data!.isEmpty) {
            return Center(
                child: Text(
                    'Please assign an issue for you.')); // Message for no data
          } else {
            return ListView.builder(
              itemCount: snapshot.data!.length,
              itemBuilder: (context, index) {
                var issue = snapshot.data![index];
                return Card(
                  color: isDarkMode
                      ? Color.fromRGBO(126, 33, 58, 1)
                      : Color(0xFFDC4654),
                  child: ListTile(
                    title: Text(issue['title'],
                        style: TextStyle(color: Colors.white)),
                    subtitle: Text(
                        'Repo: ${issue['repository_url'].split('/').last}\n'
                        'ID: ${issue['number']}\n'
                        'Created: ${issue['created_at']}',
                        style: TextStyle(color: Colors.white70)),
                    onTap: () {
                      // Placeholder for selecting an issue
                    },
                  ),
                );
              },
            );
          }
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Function to start work on selected issues
        },
        child: Icon(Icons.play_arrow),
        backgroundColor: isDarkMode ? Colors.black : Colors.white,
      ),
    );
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
