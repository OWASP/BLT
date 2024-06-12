import 'package:blt/src/pages/home/home_imports.dart';
import 'package:primer_progress_bar/primer_progress_bar.dart';

class CompanyDetailWithIssues extends ConsumerStatefulWidget {
  const CompanyDetailWithIssues({super.key, required this.company});
  final Company company;

  @override
  CompanyDetailWithIssuesState createState() => CompanyDetailWithIssuesState();
}

// ScrollController _scrollController = new ScrollController();

class CompanyDetailWithIssuesState
    extends ConsumerState<CompanyDetailWithIssues>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  late String paginatedUrl;
  late Color companyColor;
  List<Issue> openIssues = [], closedIssues = [];
  List<Segment> segments = [];
  bool loading = true;

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
    getIssuesByStatus();
    super.initState();
  }

  void getIssuesByStatus() async {
    setState(() {
      loading = true;
    });
    IssueData? response =
        await IssueApiClient.getIssueByStatus("open", widget.company.url!);
    openIssues = response!.issueList ?? [];
    response =
        await IssueApiClient.getIssueByStatus("closed", widget.company.url!);
    closedIssues = response!.issueList ?? [];

    // intialize the segments
    segments = [
      Segment(
        value: closedIssues.length,
        color: Color.fromARGB(255, 101, 205, 105),
        label: Text(
          "Closed",
        ),
      ),
      Segment(
        value: openIssues.length,
        color: Colors.deepOrange,
        label: Text(
          "Open",
        ),
      ),
    ];
    setState(() {
      loading = false;
    });
  }

  @override
  void dispose() {
    animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;
    final Company company = widget.company;

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
          company.companyName,
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          getIssuesByStatus();
        },
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: 20).copyWith(top: 12),
            child:
                Column(mainAxisAlignment: MainAxisAlignment.start, children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: SizedBox(
                  // width: size.width * 0.89,
                  height: size.height * 0.17,
                  child: Image.network(
                    company.logoLink,
                    fit: BoxFit.contain,
                  ),
                ),
              ),
              SizedBox(height: 8),
              Text(
                company.companyName,
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                    fontSize: 18,
                  ),
                ),
              ),
              SizedBox(height: 8),
              if (company.email != "") ...[
                Text(
                  company.email!,
                  style: GoogleFonts.ubuntu(
                    textStyle: TextStyle(
                      color: Color(0xFF737373),
                      fontSize: 16,
                    ),
                  ),
                ),
                SizedBox(height: 10),
              ],
              Container(
                width: double.infinity,
                height: 50,
                child: Builder(builder: (context) {
                  return TextButton(
                    onPressed: () async {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (context) => Scaffold(
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
                              centerTitle: true,
                              title: Text(
                                "Report Issue",
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                ),
                              ),
                            ),
                            body: ReportBug(
                              reportPageDefaults: ReportPageDefaults(),
                              company: company,
                            ),
                          ),
                        ),
                      );
                    },
                    child: Text(
                      "Report Issue",
                      style: GoogleFonts.ubuntu(
                        textStyle: TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                        ),
                      ),
                    ),
                    style: ButtonStyle(
                      shape: WidgetStateProperty.all<RoundedRectangleBorder>(
                        RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8.0),
                        ),
                      ),
                      backgroundColor: WidgetStateProperty.all(
                        isDarkMode
                            ? Color.fromRGBO(126, 33, 58, 1)
                            : Color(0xFFDC4654),
                      ),
                    ),
                  );
                }),
              ),
              // SizedBox(height: 10),
              // Container(
              //   width: double.infinity,
              //   height: 50,
              //   child: Builder(builder: (context) {
              //     return TextButton(
              //       child: Text(
              //         "Subscribe",
              //         style: GoogleFonts.ubuntu(
              //           textStyle: TextStyle(
              //             color: Colors.white,
              //             fontSize: 20,
              //           ),
              //         ),
              //       ),
              //       style: ButtonStyle(
              //         shape: WidgetStateProperty.all<RoundedRectangleBorder>(
              //           RoundedRectangleBorder(
              //             borderRadius: BorderRadius.circular(8.0),
              //           ),
              //         ),
              //         backgroundColor: WidgetStateProperty.all(
              //           isDarkMode
              //               ? Color.fromRGBO(126, 33, 58, 1)
              //               : Color(0xFFDC4654),
              //         ),
              //       ),
              //       onPressed: () async {},
              //     );
              //   }),
              // ),
              SizedBox(height: 20),
              // About Us Section: only if have a desc
              if (company.description != null) ...[
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    "About Us:",
                    style: GoogleFonts.ubuntu(
                      textStyle: TextStyle(
                        color: Color(0xFFDC4654),
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    "${company.description}",
                    style: GoogleFonts.aBeeZee(
                      textStyle: TextStyle(
                        color: Color(0xFF737373),
                      ),
                    ),
                    textAlign: TextAlign.justify,
                  ),
                ),
                SizedBox(height: 20),
              ],
              //  Progress Representation
              if (closedIssues.length != 0 || openIssues.length != 0) ...[
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    "Progress",
                    style: GoogleFonts.ubuntu(
                      textStyle: TextStyle(
                        color: Color(0xFFDC4654),
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                SizedBox(height: 20),
                PrimerProgressBar(
                  segments: segments,
                  legendEllipsisBuilder: DefaultLegendEllipsisBuilder(
                    segments: segments,
                    color: Colors.grey,
                    label: const Text("Other"),
                    valueLabelBuilder: (value) => Text("$value%"),
                  ),
                ),
                SizedBox(height: 20),
              ],
              // Open Issues list
              Container(
                padding: EdgeInsets.fromLTRB(0, 0, 0, 12),
                color: Theme.of(context).canvasColor,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            "Open Issues",
                            style: GoogleFonts.ubuntu(
                              textStyle: TextStyle(
                                color: Color(0xFFDC4654),
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          IconButton(
                            icon: Icon(
                              Icons.arrow_forward_ios_rounded,
                              color: Color(0xFFDC4654),
                            ),
                            onPressed: () {
                              Navigator.pushNamed(
                                context,
                                RouteManager.openIssues,
                                arguments: company,
                              );
                            },
                          ),
                        ]),
                    Text(
                      "Check all the open issues from ${company.companyName}!",
                      style: GoogleFonts.aBeeZee(
                        textStyle: TextStyle(
                          color: Color(0xFF737373),
                        ),
                      ),
                    ),
                    if (!loading)
                      Container(
                        // height: 0.3 * size.height,
                        padding: const EdgeInsets.fromLTRB(0, 20, 0, 10),
                        child: InkWell(
                          onTap: () {
                            Navigator.pushNamed(
                              context,
                              RouteManager.openIssues,
                              arguments: company,
                            );
                          },
                          child: ListView.builder(
                            padding: EdgeInsets.zero,
                            physics: NeverScrollableScrollPhysics(),
                            itemCount:
                                (openIssues.length < 3 ? openIssues.length : 3),
                            shrinkWrap: true,
                            itemBuilder: (context, index) {
                              return ListTile(
                                shape: RoundedRectangleBorder(
                                  borderRadius: index == 0
                                      ? BorderRadius.only(
                                          topLeft: Radius.circular(10),
                                          topRight: Radius.circular(15),
                                        )
                                      : index == 2
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
                                            ? Color(0xFFFFD700)
                                                .withOpacity(0.42)
                                            : Colors.white,
                                // leading: buildAvatar(leaderList[index].image),
                                title: Text(
                                  openIssues[index].title,
                                  style: GoogleFonts.ubuntu(
                                    textStyle: TextStyle(
                                      color: isDarkMode
                                          ? Colors.white
                                          : Color(0xFFDC4654),
                                    ),
                                  ),
                                  maxLines: 6,
                                ),
                                subtitle: Text(
                                  "${openIssues[index].created!.day}/${openIssues[index].created!.month}/${openIssues[index].created!.year}",
                                  style: GoogleFonts.aBeeZee(
                                    textStyle: TextStyle(
                                      color: isDarkMode
                                          ? Colors.grey[400]
                                          : Color(0xFF737373),
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                                trailing: Text(
                                  "# " + (index + 1).toString(),
                                  style: GoogleFonts.ubuntu(
                                    textStyle: TextStyle(
                                      color: isDarkMode
                                          ? Colors.grey[400]
                                          : Color(0xFF737373),
                                      fontSize: 15,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                    if (loading)
                      Center(
                        child: CircularProgressIndicator(
                          valueColor: animationController.drive(
                            ColorTween(
                              begin: Colors.blueAccent,
                              end: Colors.red,
                            ),
                          ),
                        ),
                      ),

                    SizedBox(height: 10),
                    // Closed Issues list
                    Container(
                      padding: EdgeInsets.fromLTRB(0, 0, 0, 12),
                      color: Theme.of(context).canvasColor,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  "Closed Issues",
                                  style: GoogleFonts.ubuntu(
                                    textStyle: TextStyle(
                                      color: Color(0xFFDC4654),
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                IconButton(
                                  icon: Icon(
                                    Icons.arrow_forward_ios_rounded,
                                    color: Color(0xFFDC4654),
                                  ),
                                  onPressed: () {
                                    Navigator.pushNamed(
                                      context,
                                      RouteManager.closedIssues,
                                      arguments: company,
                                    );
                                  },
                                ),
                              ]),
                          Text(
                            "Check all the closed issues from ${company.companyName}!",
                            style: GoogleFonts.aBeeZee(
                              textStyle: TextStyle(
                                color: Color(0xFF737373),
                              ),
                            ),
                          ),
                          if (!loading)
                            Container(
                              // height: 0.3 * size.height,
                              padding: const EdgeInsets.fromLTRB(0, 20, 0, 10),
                              child: InkWell(
                                onTap: () {
                                  Navigator.pushNamed(
                                      context, RouteManager.closedIssues,
                                      arguments: company);
                                },
                                child: ListView.builder(
                                  padding: EdgeInsets.zero,
                                  physics: NeverScrollableScrollPhysics(),
                                  itemCount: (closedIssues.length < 3
                                      ? closedIssues.length
                                      : 3),
                                  shrinkWrap: true,
                                  itemBuilder: (context, index) {
                                    return ListTile(
                                      shape: RoundedRectangleBorder(
                                        borderRadius: index == 0
                                            ? BorderRadius.only(
                                                topLeft: Radius.circular(10),
                                                topRight: Radius.circular(15),
                                              )
                                            : index == 2
                                                ? BorderRadius.only(
                                                    bottomLeft:
                                                        Radius.circular(10),
                                                    bottomRight:
                                                        Radius.circular(10),
                                                  )
                                                : BorderRadius.only(
                                                    topLeft: Radius.circular(0),
                                                  ),
                                      ),
                                      tileColor: index == 2
                                          ? Color(0xFFC9AE5D).withOpacity(0.42)
                                          : index == 1
                                              ? Color(0xFFADD8E6)
                                                  .withOpacity(0.42)
                                              : index == 0
                                                  ? Color(0xFFFFD700)
                                                      .withOpacity(0.42)
                                                  : Colors.white,
                                      // leading: buildAvatar(leaderList[index].image),
                                      title: Text(
                                        closedIssues[index].title,
                                        style: GoogleFonts.ubuntu(
                                          textStyle: TextStyle(
                                            color: isDarkMode
                                                ? Colors.white
                                                : Color(0xFFDC4654),
                                          ),
                                        ),
                                        maxLines: 6,
                                      ),
                                      subtitle: Text(
                                        "${closedIssues[index].created!.day}/${closedIssues[index].created!.month}/${closedIssues[index].created!.year}",
                                        style: GoogleFonts.aBeeZee(
                                          textStyle: TextStyle(
                                            color: isDarkMode
                                                ? Colors.grey[400]
                                                : Color(0xFF737373),
                                            fontSize: 12,
                                          ),
                                        ),
                                      ),
                                      trailing: Text(
                                        "# " + (index + 1).toString(),
                                        style: GoogleFonts.ubuntu(
                                          textStyle: TextStyle(
                                            color: isDarkMode
                                                ? Colors.grey[400]
                                                : Color(0xFF737373),
                                            fontSize: 15,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                    );
                                  },
                                ),
                              ),
                            ),
                          if (loading)
                            Center(
                              child: CircularProgressIndicator(
                                valueColor: animationController.drive(
                                  ColorTween(
                                    begin: Colors.blueAccent,
                                    end: Colors.red,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}
