import 'package:blt/src/pages/home/home_imports.dart';

class CompanyListPage extends ConsumerStatefulWidget {
  const CompanyListPage({super.key});

  @override
  CompanyListPageState createState() => CompanyListPageState();
}

ScrollController _scrollController = new ScrollController();

class CompanyListPageState extends ConsumerState<CompanyListPage>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  late String paginatedUrl;
  late Color companyColor;

  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  @override
  void initState() {
    paginatedUrl = IssueEndPoints.issues;
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

  @override
  void dispose() {
    animationController.dispose();
    super.dispose();
  }

  // void loadMoreIssues() {
  //   // paginatedUrl = ref.watch(companyListProvider.notifier).nxtUrl!;
  //   ref.watch(companiesListProvider.notifier);
  // }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;
    final issueState = ref.watch(companiesListProvider);

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
          "Companies",
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
                        "Companies",
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
                          "${AppLocalizations.of(context)!.notManyBugs}:) \n ${AppLocalizations.of(context)!.yay}",
                          textAlign: TextAlign.center,
                        ),
                      );
                    } else {
                      return ListView.separated(
                        controller: _scrollController,
                        itemCount: companyList.length,
                        shrinkWrap: true,
                        physics: NeverScrollableScrollPhysics(),
                        itemBuilder: (context, index) {
                          final company = companyList[index];
                          return CompanyListElement(
                            company: company,
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

class CompanyListElement extends StatelessWidget {
  const CompanyListElement({super.key, required this.company});
  final Company company;

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return GestureDetector(
      onTap: () {
        Navigator.of(context).pushNamed(
          RouteManager.companyDetailPageWithIssues,
          arguments: company,
        );
      },
      child: Container(
        width: size.width * 0.9,
        decoration: BoxDecoration(
          color: Colors.grey[350],
          borderRadius: BorderRadius.circular(10),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: SizedBox(
                  height: 80,
                  width: 120,
                  child: Image.network(
                    company.logoLink,
                    fit: BoxFit.cover,
                    alignment: Alignment.center,
                  ),
                ),
              ),
              SizedBox(height: 8),
              Text(
                company.companyName,
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color.fromARGB(255, 95, 95, 95),
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}
