import 'package:blt/src/pages/pages_import.dart';

class BugHuntDescriptionPage extends StatefulWidget {
  const BugHuntDescriptionPage({super.key, required this.hunt});
  final BugHunt hunt;

  @override
  State<BugHuntDescriptionPage> createState() => _BugHuntDescriptionPageState();
}

class _BugHuntDescriptionPageState extends State<BugHuntDescriptionPage>
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
          widget.hunt.name,
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
          ),
        ),
      ),
      body: Stack(
        children: [
          SingleChildScrollView(
            child: Stack(
              children: [
                Column(
                  children: [
                    SizedBox(
                      height: size.height * 0.16,
                      width: size.width,
                      child: (widget.hunt.banner != "")
                          ? ClipRRect(
                              borderRadius: BorderRadius.only(
                                  bottomLeft: Radius.circular(8),
                                  bottomRight: Radius.circular(8)),
                              child: CachedNetworkImage(
                                imageUrl: GeneralEndPoints.apiBaseUrl +
                                    "media/" +
                                    widget.hunt.banner!,
                                fit: BoxFit.cover,
                              ),
                            )
                          : Container(
                              decoration: BoxDecoration(
                                color: Colors.grey[300],
                                borderRadius: BorderRadius.only(
                                    bottomLeft: Radius.circular(8),
                                    bottomRight: Radius.circular(8)),
                              ),
                            ),
                    ),
                    Padding(
                      padding: EdgeInsets.symmetric(horizontal: 20),
                      child: Column(
                        children: [
                          SizedBox(height: size.height * 0.04),
                          Container(
                            padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
                            child: Text(
                              widget.hunt.name,
                              style: GoogleFonts.ubuntu(
                                textStyle: TextStyle(
                                  color: Color(0xFFDC4654),
                                  // color: Color(0xFF737373),
                                  fontSize: 25,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                          if (widget.hunt.description != "") ...[
                            SectionAnsData(
                              title: "Description",
                              details: Text(
                                widget.hunt.description!,
                                style: GoogleFonts.aBeeZee(
                                  textStyle: TextStyle(
                                    color: Color(0xFF737373),
                                  ),
                                ),
                              ),
                            ),
                          ],
                          SectionAnsData(
                            title: "Schedule",
                            details: Align(
                              alignment: Alignment.centerLeft,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Icon(
                                        Icons.calendar_month,
                                        color: Color(0xFF737373),
                                      ),
                                      SizedBox(width: 5),
                                      Text(
                                        'Starts on : ${monthsInYear[widget.hunt.startsOn?.month]} ${widget.hunt.startsOn?.day} ${widget.hunt.startsOn?.year}',
                                        overflow: TextOverflow.ellipsis,
                                        softWrap: true,
                                        style: GoogleFonts.aBeeZee(
                                          textStyle: TextStyle(
                                            fontSize: 14,
                                            color: Color(0xFF737373),
                                          ),
                                        ),
                                      ),
                                      // Text('${widget.hunt.startsOn}'),
                                    ],
                                  ),
                                  SizedBox(height: size.height * 0.006),
                                  Row(
                                    children: [
                                      Icon(
                                        Icons.calendar_month,
                                        color: Color(0xFF737373),
                                      ),
                                      SizedBox(width: 5),
                                      Text(
                                        'Ends on : ${monthsInYear[widget.hunt.endsOn?.month]} ${widget.hunt.endsOn?.day} ${widget.hunt.endsOn?.year}',
                                        overflow: TextOverflow.ellipsis,
                                        softWrap: true,
                                        style: GoogleFonts.aBeeZee(
                                          textStyle: TextStyle(
                                            fontSize: 14,
                                            color: Color(0xFF737373),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                          SizedBox(height: size.height * 0.07)
                        ],
                      ),
                    )
                  ],
                ),
                Positioned(
                  top: size.height * 0.1,
                  left: size.width * 0.385,
                  child: CircleAvatar(
                    backgroundColor: Colors.grey[500],
                    radius: size.height * 0.054,
                    child: CircleAvatar(
                      backgroundImage: NetworkImage(
                        GeneralEndPoints.apiBaseUrl +
                            "media/" +
                            widget.hunt.logo!,
                      ),
                      radius: size.height * 0.05,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Positioned(
            bottom: 0,
            child: Container(
              width: size.width,
              decoration: BoxDecoration(
                  color: isDarkMode
                      ? Color.fromRGBO(34, 22, 23, 1)
                      : Theme.of(context).canvasColor,
                  boxShadow: [
                    BoxShadow(
                      offset: Offset(0, 1),
                      color: const Color.fromRGBO(158, 158, 158, 1),
                      spreadRadius: 0.2,
                      blurRadius: 10,
                    )
                  ]),
              padding: EdgeInsets.all(9).copyWith(left: 20, right: 20),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Text(
                        'Prize : ',
                        style: GoogleFonts.ubuntu(
                          textStyle: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF737373),
                          ),
                        ),
                      ),
                      Text(
                        '\$${widget.hunt.prize}',
                        style: GoogleFonts.ubuntu(
                          textStyle: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 20,
                            color: Colors.green,
                          ),
                        ),
                      ),
                    ],
                  ),
                  TextButton(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text("Coming Soon !!")));
                    },
                    child: Text(
                      "Participate",
                      style: GoogleFonts.ubuntu(
                        textStyle: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
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
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class SectionAnsData extends StatelessWidget {
  const SectionAnsData({super.key, required this.title, required this.details});
  final String title;
  final Widget details;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          "$title :",
          style: GoogleFonts.ubuntu(
            textStyle: TextStyle(
              color: Color(0xFFDC4654),
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        SizedBox(height: 10),
        details,
        SizedBox(height: 20),
      ],
    );
  }
}
