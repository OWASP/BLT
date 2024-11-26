import 'package:blt/src/pages/home/home_imports.dart';

/// Issues page for viewing all the issues posted via the website and app.
class IssuesPage extends ConsumerStatefulWidget {
  const IssuesPage({Key? key}) : super(key: key);

  @override
  IssuesPageState createState() => IssuesPageState();
}

ScrollController _scrollController = new ScrollController();

class IssuesPageState extends ConsumerState<IssuesPage>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  late String? paginatedUrl;

  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  @override
  void initState() {
    // paginatedUrl = IssueEndPoints.issues;

    animationController =
        AnimationController(duration: new Duration(seconds: 2), vsync: this);
    animationController.repeat();

    _scrollController.addListener(() async {
      if (_scrollController.position.pixels ==
          _scrollController.position.maxScrollExtent) {
        loadMoreIssues();
      }
    });
    super.initState();
  }

  @override
  void dispose() {
    animationController.dispose();
    super.dispose();
  }

  void loadMoreIssues() {
    paginatedUrl = ref.watch(issueListProvider.notifier).nxtUrl;
    if (paginatedUrl != null) {
      // Modified: Added a null check before using paginatedUrl
      ref.watch(issueListProvider.notifier).getMoreIssues(paginatedUrl!);
    } else {
      print(
          "No more items to load."); // Modified: Handle the case where paginatedUrl is null
    }
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    final issueState = ref.watch(issueListProvider);
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDarkMode
          ? Color.fromRGBO(34, 22, 23, 1)
          : Theme.of(context).canvasColor,
      body: RefreshIndicator(
        onRefresh: () async {
          ref.read(issueListProvider.notifier).refreshIssueList();
        },
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: EdgeInsets.symmetric(horizontal: 20),
                width: size.width,
                color: isDarkMode
                    ? Color.fromRGBO(34, 22, 23, 1)
                    : Theme.of(context).canvasColor,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
                      child: Text(
                        AppLocalizations.of(context)!.issues,
                        style: GoogleFonts.ubuntu(
                          textStyle: TextStyle(
                            color: Color(0xFF737373),
                            fontSize: 25,
                          ),
                        ),
                      ),
                    ),
                    Container(
                      padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
                      child: Text(
                        AppLocalizations.of(context)!.checkLatestIssues,
                        style: GoogleFonts.aBeeZee(
                          textStyle: TextStyle(
                            color: Color(0xFF737373),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                height: size.height * 0.8,
                padding: EdgeInsets.symmetric(horizontal: 20),
                child: issueState!.when(
                  data: (List<Issue>? issueList) {
                    if (issueList!.isEmpty) {
                      return Center(
                        child: Text(
                          "${AppLocalizations.of(context)!.notManyBugs}:) \n ${AppLocalizations.of(context)!.yay}",
                          textAlign: TextAlign.center,
                        ),
                      );
                    } else {
                      return ShowIssueList(
                        issueList: issueList,
                      );
                    }
                  },
                  error: (Object error, StackTrace? stackTrace) {
                    return Center(
                      child: Text(
                        AppLocalizations.of(context)!.somethingWentWrong,
                        style: TextStyle(fontSize: 18),
                      ),
                    );
                  },
                  loading: () {
                    return Center(
                      child: CircularProgressIndicator(
                        valueColor: animationController.drive(
                          ColorTween(
                            begin: Colors.blueAccent,
                            end: Colors.red,
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class ShowIssueList extends StatefulWidget {
  const ShowIssueList({super.key, required this.issueList, this.isTesting});
  final List<Issue> issueList;
  final bool? isTesting;

  @override
  State<ShowIssueList> createState() => _ShowIssueListState();
}

class _ShowIssueListState extends State<ShowIssueList> {
  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: _scrollController,
      itemCount: widget.issueList.length,
      itemBuilder: (context, index) {
        final currentIssue = widget.issueList[index];
        return IssueCard(
          isTesting: widget.isTesting,
          issue: currentIssue,
        );
      },
    );
  }
}
