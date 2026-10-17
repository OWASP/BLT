import './components_import.dart';

/// The search bar of app for searching issues based on keyword.
class BugHuntSearchDelegate extends SearchDelegate {
  @override
  List<Widget>? buildActions(BuildContext context) {
    return [
      IconButton(
        onPressed: () {
          query != '' ? (query = '') : Navigator.of(context).pop();
        },
        icon: Icon(
          Icons.clear,
          color: Color(0xFFDC4654),
        ),
      ),
    ];
  }

  @override
  Widget? buildLeading(BuildContext context) {
    return IconButton(
      icon: Icon(
        Icons.arrow_back_ios_new_rounded,
        color: Color(0xFFDC4654),
      ),
      onPressed: () {
        Navigator.of(context).pop();
      },
    );
  }

  @override
  Widget buildResults(BuildContext context) {
    Future _getObj =
        BugHuntApiClient.searchBugHunts(client: null, search: query);

    ScrollController _scrollController = new ScrollController();

    return FutureBuilder(
      future: _getObj,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.done) {
          if (snapshot.hasError) {
            return Center(
              child: Text(
                'Something went wrong!',
                style: TextStyle(fontSize: 18),
              ),
            );
          } else if (snapshot.hasData) {
            return ListView.builder(
              padding: EdgeInsets.symmetric(horizontal: 20),
              itemCount: snapshot.data.length,
              controller: _scrollController,
              itemBuilder: (context, index) {
                return BugHuntListTile(
                  hunt: snapshot.data[index],
                );
              },
            );
          }
        }
        return Center(
          child: CircularProgressIndicator(),
        );
      },
    );
  }

  @override
  Widget buildSuggestions(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Container(
      width: size.width,
      height: size.height,
      child: Center(
        child: Text(
          'Search a Bug Hunt!',
          style: GoogleFonts.ubuntu(
            textStyle: TextStyle(
              color: Color(0xFF737373),
              fontSize: 20,
            ),
          ),
        ),
      ),
    );
  }
}
