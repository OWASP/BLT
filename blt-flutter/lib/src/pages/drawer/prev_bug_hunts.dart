import 'package:blt/src/pages/drawer/drawer_imports.dart';

class PreviousBugHunts extends ConsumerStatefulWidget {
  const PreviousBugHunts({Key? key}) : super(key: key);

  @override
  _PreviousBugHuntsState createState() => _PreviousBugHuntsState();
}

ScrollController _scrollController = new ScrollController();

class _PreviousBugHuntsState extends ConsumerState<PreviousBugHunts>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  @override
  void initState() {
    animationController =
        AnimationController(duration: new Duration(seconds: 2), vsync: this);
    animationController.repeat();
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;
    final bugHuntList = ref.watch(prevBugHuntListProvider);

    return Scaffold(
      backgroundColor: isDarkMode
          ? Color.fromRGBO(34, 22, 23, 1)
          : Theme.of(context).canvasColor,
      appBar: AppBar(
        backgroundColor:
            isDarkMode ? Color.fromRGBO(58, 21, 31, 1) : Color(0xFFDC4654),
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
          "Previous Bug Hunts",
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
          ),
        ),
        // actions: [
        //   IconButton(
        //     icon: Icon(
        //       Icons.search,
        //       color: Colors.white,
        //     ),
        //     onPressed: () {
        //       showSearch(
        //         context: context,
        //         delegate: BugHuntSearchDelegate(),
        //       );
        //     },
        //   ),
        // ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.read(prevBugHuntListProvider.notifier).refreshPrevBugHuntList();
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
                        "Previous Bug Hunts",
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
                        "Check out the list of awesome Previous Bug Hunts going on. Maybe try to participate in them too?",
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
                child: bugHuntList!.when(
                  data: (List<BugHunt>? bugHuntsList) {
                    if (bugHuntsList!.isEmpty) {
                      return Center(
                        child: Text(
                          "No Previous Bug Hunts found !!",
                          textAlign: TextAlign.center,
                        ),
                      );
                    } else {
                      return ListView.separated(
                        controller: _scrollController,
                        itemCount: bugHuntsList.length,
                        shrinkWrap: true,
                        physics: NeverScrollableScrollPhysics(),
                        itemBuilder: (context, index) {
                          final hunt = bugHuntsList[index];
                          // if (widget.isTest != null && widget.isTest == true) {
                          //   return ListTile(
                          //     title: Text(company.companyName),
                          //     subtitle: Text('${company.lastModified}'),
                          //   );
                          // }
                          return BugHuntListTile(hunt: hunt);
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
