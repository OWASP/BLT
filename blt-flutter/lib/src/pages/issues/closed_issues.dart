import 'package:blt/src/pages/home/home_imports.dart';
import 'package:blt/src/util/brand.dart';

/// Issues page for viewing all the Closed issues for a company posted via the website and app.
class ClosedIssuesPage extends ConsumerStatefulWidget {
  const ClosedIssuesPage({required this.company, Key? key});
  final Company company;

  @override
  ClosedIssuesPageState createState() => ClosedIssuesPageState();
}

ScrollController _scrollController = new ScrollController();

class ClosedIssuesPageState extends ConsumerState<ClosedIssuesPage>
    with TickerProviderStateMixin {
  late AnimationController animationController;

  late var closedIssuesListProvider = StateNotifierProvider<
      IssueByStatusListProvider, AsyncValue<List<Issue>?>?>((ref) {
    return IssueByStatusListProvider(
        ref.read, 'closed', widget.company.url ?? "");
  });
  // late String paginatedUrl;

  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  @override
  void initState() {
    // paginatedUrl =
    //     IssueEndPoints.issues + "/?status=open&domain=${widget.company.url}";

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
    // paginatedUrl = ref
    //     .watch(
    //         closedIssuesListProvider({"url": widget.company.url ?? ""}).notifier)
    //     .nxtUrl!;
    ref
        .watch(closedIssuesListProvider.notifier)
        .getMoreIssues("closed", widget.company.url ?? "");
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;

    final issueState = ref.watch(closedIssuesListProvider);
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDarkMode
          ? BLTColors.darkBackground
          : Theme.of(context).canvasColor,
      appBar: AppBar(
        backgroundColor: BLTColors.primary,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: Colors.white,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
        title: Text(
          "Closed Issues",
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.read(closedIssuesListProvider.notifier).refreshIssueList();
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
                    ? BLTColors.darkBackground
                    : Theme.of(context).canvasColor,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
                      child: Text(
                        "Closed Issues",
                        style: BLTFonts.system(
                          textStyle: TextStyle(
                            color: BLTColors.textMuted,
                            fontSize: 25,
                          ),
                        ),
                      ),
                    ),
                    Container(
                      padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
                      child: Text(
                        "Check out the closed issues found and reported by ${widget.company.companyName}. Maybe find a fix too?",
                        style: BLTFonts.system(
                          textStyle: TextStyle(
                            color: BLTColors.textMuted,
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
                      return ListView.builder(
                        controller: _scrollController,
                        itemCount: issueList.length,
                        itemBuilder: (context, index) {
                          final currentIssue = issueList[index];
                          if (currentIssue.screenshotsLink!.isEmpty) {
                            return Container();
                          }
                          return IssueCard(
                            issue: currentIssue,
                          );
                        },
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
                            end: BLTColors.primary,
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
