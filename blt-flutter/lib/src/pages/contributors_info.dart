import 'package:blt/src/pages/pages_import.dart';

class ContributorsInfoPage extends StatefulWidget {
  const ContributorsInfoPage({super.key, required this.project});
  final Project project;

  @override
  State<ContributorsInfoPage> createState() => _ContributorsInfoPageState();
}

class _ContributorsInfoPageState extends State<ContributorsInfoPage> {
  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;
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
          "Contributors",
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
          ),
        ),
      ),
      body: SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
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
                        "${widget.project.name} Contributors",
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
                        "Check out the awesome contributors we have. Maybe contribute and become a contributor too?",
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
              SizedBox(height: size.height * 0.008),
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 4,
                  crossAxisSpacing: size.width * 0.05,
                  childAspectRatio: size.height * 0.001,
                  mainAxisSpacing: size.height * 0.01,
                ),
                itemCount: widget.project.contributors?.length,
                itemBuilder: (context, index) => Ink(
                  child: InkWell(
                    onTap: () {
                      Navigator.of(context).push(
                        new PageRouteBuilder(
                          opaque: false,
                          barrierDismissible: true,
                          pageBuilder: (BuildContext context, _, __) {
                            return ContributorCard(
                              contributor: widget.project.contributors![index],
                            );
                          },
                        ),
                      );
                    },
                    child: Ink(
                      child: Column(
                        children: [
                          Hero(
                            tag:
                                "image${widget.project.contributors?[index].image}",
                            child: CircleAvatar(
                              backgroundImage: NetworkImage(
                                widget.project.contributors![index].image,
                              ),
                              radius: size.height * 0.027,
                            ),
                          ),
                          SizedBox(height: 2),
                          Text(
                            widget.project.contributors![index].name,
                            maxLines: 2,
                            textAlign: TextAlign.center,
                            style: GoogleFonts.aBeeZee(
                              textStyle: TextStyle(
                                color: Color(0xFF737373),
                              ),
                            ),
                          )
                        ],
                      ),
                    ),
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

class ContributorCard extends StatefulWidget {
  final Contributors contributor;

  const ContributorCard({Key? key, required this.contributor})
      : super(key: key);

  @override
  State<ContributorCard> createState() => _ContributorCardState();
}

class _ContributorCardState extends State<ContributorCard> {
  // bool loading = true;
  // void getContributorInfo() async {
  //   setState(() {
  //     loading = true;
  //   });
  //   contributor = await GithubApis.getContributorsInfoFromID(
  //     widget.contributor.id,
  //   );
  //   print(contributor);
  //   setState(() {
  //     loading = false;
  //   });
  // }

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;
    return GestureDetector(
      onTap: () {
        Navigator.of(context).pop();
      },
      child: Scaffold(
        backgroundColor: Colors.black.withOpacity(0.2),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32.0),
            child: Container(
                decoration: BoxDecoration(
                    borderRadius: BorderRadius.all(
                      Radius.circular(20),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.grey,
                        blurRadius: 15.0,
                      ),
                    ]),
                height: size.height * 0.23,
                child: Stack(
                  children: [
                    Row(
                      children: [
                        Container(
                          decoration: BoxDecoration(
                            color: isDarkMode
                                ? Color.fromRGBO(58, 21, 31, 1)
                                : Color(0xFFDC4654),
                            borderRadius: BorderRadius.only(
                              topLeft: Radius.circular(20),
                              bottomLeft: Radius.circular(20),
                            ),
                          ),
                          width: size.width * 0.2,
                        ),
                        Container(
                          decoration: BoxDecoration(
                            color: isDarkMode
                                ? Color.fromRGBO(34, 22, 23, 1)
                                : Theme.of(context).canvasColor,
                            borderRadius: BorderRadius.only(
                              bottomRight: Radius.circular(20),
                              topRight: Radius.circular(20),
                            ),
                          ),
                          width: size.width * 0.64,
                        ),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          height: size.height * 0.058,
                        ),
                        Row(
                          children: [
                            SizedBox(
                              width: size.width * 0.09,
                            ),
                            CircleAvatar(
                              backgroundColor: Colors.white,
                              radius: 43.0,
                              child: Hero(
                                tag: "image${widget.contributor.image}",
                                child: CircleAvatar(
                                  radius: 40,
                                  backgroundImage: CachedNetworkImageProvider(
                                    widget.contributor.image,
                                  ),
                                ),
                              ),
                            ),
                            SizedBox(
                              width: size.width * 0.05,
                            ),
                            Container(
                              // height: size.height * 0.2,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Hero(
                                    tag: "name${widget.contributor.name}",
                                    child: Material(
                                      color: Colors.transparent,
                                      child: Text(
                                        widget.contributor.name,
                                        style: GoogleFonts.aBeeZee(
                                          textStyle: TextStyle(
                                            color: Colors.red,
                                          ),
                                          fontWeight: FontWeight.bold,
                                          fontSize: 18.0,
                                        ),
                                      ),
                                    ),
                                  ),
                                  Text(
                                    '${widget.contributor.contributions} contributions',
                                    style: GoogleFonts.aBeeZee(
                                      textStyle: TextStyle(
                                        color: Colors.red,
                                      ),
                                      fontWeight: FontWeight.w500,
                                      fontSize: 16.0,
                                    ),
                                  ),
                                  IconButton(
                                    onPressed: () async {
                                      Uri site = Uri.parse(
                                          "https://github.com/${widget.contributor.name}");
                                      try {
                                        await launchUrl(site,
                                            mode:
                                                LaunchMode.externalApplication);
                                      } catch (e) {}
                                    },
                                    icon: SvgPicture.asset(
                                      "assets/GitHub.svg",
                                      height: 35,
                                      colorFilter: isDarkMode
                                          ? ColorFilter.mode(
                                              Color.fromARGB(
                                                  255, 212, 212, 212),
                                              BlendMode.srcIn)
                                          : null,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                )),
          ),
        ),
      ),
    );
  }
}
