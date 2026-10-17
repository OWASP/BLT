import 'package:blt/src/pages/home/home_imports.dart';

class CompanyScoreboardPage extends ConsumerStatefulWidget {
  const CompanyScoreboardPage({super.key});

  @override
  CompanyScoreboardPageState createState() => CompanyScoreboardPageState();
}

ScrollController _scrollController = new ScrollController();

class CompanyScoreboardPageState extends ConsumerState<CompanyScoreboardPage>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  late String paginatedUrl;
  late Color companyColor;

  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  @override
  void initState() {
    // paginatedUrl = IssueEndPoints.issues;
    companyColor = Color(0xFFDC4654);

    animationController =
        AnimationController(duration: new Duration(seconds: 2), vsync: this);
    animationController.repeat();

    // _scrollController.addListener(() async {
    //   if (_scrollController.position.pixels ==
    //       _scrollController.position.maxScrollExtent) {
    //     loadMoreIssues();
    //   }
    // });
    super.initState();
  }

  CircleAvatar buildLogo(String partUrl) {
    try {
      if (partUrl == "")
        return CircleAvatar(
          foregroundColor: Colors.transparent,
          radius: 20,
          child: Icon(
            Icons.account_circle_outlined,
            color: Color(0xFFDC4654),
            size: 40,
          ),
        );
      else
        return CircleAvatar(
          foregroundImage: CachedNetworkImageProvider(
            "https://storage.googleapis.com/bhfiles/" + partUrl,
          ),
          radius: 20,
        );
    } on Exception {
      return CircleAvatar(
        foregroundColor: Colors.transparent,
        backgroundColor: Colors.transparent,
        child: Icon(
          Icons.account_circle_outlined,
          color: Colors.white,
          size: 20,
        ),
      );
    }
  }

  @override
  void dispose() {
    animationController.dispose();
    super.dispose();
  }

  void loadMoreIssues() {
    // paginatedUrl = ref.watch(companyListProvider.notifier).nxtUrl!;
    ref.watch(companyScoreboardProvider.notifier);
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;
    final issueState = ref.watch(companyScoreboardProvider);

    return Scaffold(
      backgroundColor: isDarkMode
          ? Color.fromRGBO(34, 22, 23, 1)
          : Theme.of(context).canvasColor,
      appBar: AppBar(
        backgroundColor: companyColor,
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
          "Company Leaderboard",
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.read(companiesListProvider.notifier).refreshCompanyList();
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
                        "Company Leaderboard",
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
                        "Check out the list of awesome companies out here. Maybe try to fix there issues too?",
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
                // height: size.height * 0.8,
                padding: EdgeInsets.symmetric(horizontal: 20),
                child: issueState!.when(
                  data: (List<Company>? companyList) {
                    if (companyList!.isEmpty) {
                      return Center(
                        child: Text(
                          "No companies found !!",
                          textAlign: TextAlign.center,
                        ),
                      );
                    } else {
                      return ListView.separated(
                        controller: _scrollController,
                        itemCount: (companyList.length < 100)
                            ? companyList.length
                            : 100,
                        shrinkWrap: true,
                        physics: NeverScrollableScrollPhysics(),
                        itemBuilder: (context, index) {
                          final company = companyList[index];
                          return ListTile(
                            onTap: () async {
                              Navigator.pushNamed(
                                context,
                                RouteManager.companyDetailPageWithIssues,
                                arguments: Company(
                                    company.id,
                                    company.companyName,
                                    company.description,
                                    company.email,
                                    company.url,
                                    company.hexcolor,
                                    company.openIssues,
                                    company.closedIssues,
                                    company.issueCount,
                                    company.lastModified,
                                    (company.logoLink != "")
                                        ? "https://storage.googleapis.com/bhfiles/" +
                                            company.logoLink
                                        : "",
                                    company.topTester,
                                    company.twitter,
                                    company.facebook,
                                    company.isActive),
                              );
                            },
                            shape: RoundedRectangleBorder(
                              borderRadius: index == 0
                                  ? BorderRadius.only(
                                      topLeft: Radius.circular(10),
                                      topRight: Radius.circular(15),
                                    )
                                  : index ==
                                          ((companyList.length < 100)
                                                  ? companyList.length
                                                  : 100) -
                                              1
                                      ? BorderRadius.only(
                                          bottomLeft: Radius.circular(10),
                                          bottomRight: Radius.circular(10),
                                        )
                                      : BorderRadius.only(
                                          topLeft: Radius.circular(0),
                                        ),
                            ),
                            tileColor: index == 2
                                ? Color(0xFFC9AE5D).withOpacity(0.42)
                                : index == 1
                                    ? Color(0xFFADD8E6).withOpacity(0.42)
                                    : index == 0
                                        ? Color(0xFFFFD700).withOpacity(0.42)
                                        : Colors.white,
                            leading: buildLogo(company.logoLink),
                            title: Text(
                              company.companyName,
                              style: GoogleFonts.ubuntu(
                                textStyle: TextStyle(
                                  color: Color(0xFFDC4654),
                                ),
                              ),
                              maxLines: 6,
                            ),
                            subtitle: Text(
                              "Total issue count: ${company.issueCount}",
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  color: Color(0xFF737373),
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            trailing: Text(
                              "# ${index + 1}",
                              style: GoogleFonts.ubuntu(
                                textStyle: TextStyle(
                                  color: Color(0xFF737373),
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          );
                        },
                        separatorBuilder: (BuildContext context, int index) {
                          return SizedBox(height: 10);
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
