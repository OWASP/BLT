import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/company_model.dart';

/// Popup page for viewing company details when a company
/// is clicked on the Company Scoreboard page.
class CompanyDetailPage extends StatefulWidget {
  final Company company;
  const CompanyDetailPage({
    Key? key,
    required this.company,
  }) : super(key: key);

  @override
  State<CompanyDetailPage> createState() => _CompanyDetailPageState();
}

class _CompanyDetailPageState extends State<CompanyDetailPage> {
  late Color companyColor;

  Widget buildOpenIssueList(Size size) {
    return Container(
      width: size.width,
      height: 0.3 * size.height,
      margin: EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        border: Border.all(color: Color(0xFF737373), width: 0.5),
        borderRadius: BorderRadius.circular(15),
      ),
      child: Center(
        child: Text(
          widget.company.openIssues > 0
              ? "Unable to get info"
              : "No open issues!",
          style: GoogleFonts.aBeeZee(
            textStyle: TextStyle(
              color: Color(0xFF737373),
            ),
          ),
        ),
      ),
    );
  }

  Widget buildClosedIssueList(Size size) {
    return Container(
      width: size.width,
      height: 0.3 * size.height,
      margin: EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(
        border: Border.all(color: Color(0xFF737373), width: 0.5),
        borderRadius: BorderRadius.circular(15),
      ),
      child: Center(
        child: Text(
          widget.company.closedIssues > 0
              ? "Unable to get info"
              : "No closed issues!",
          style: GoogleFonts.aBeeZee(
            textStyle: TextStyle(
              color: Color(0xFF737373),
            ),
          ),
        ),
      ),
    );
  }

  @override
  void initState() {
    companyColor = widget.company.valueColor ?? Color(0xFFDC4654);
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: companyColor,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
        title: Text(widget.company.companyName),
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF737373).withOpacity(0.125),
              Colors.transparent,
            ],
          ),
        ),
        width: size.width,
        height: size.height,
        child: GlowingOverscrollIndicator(
          color: companyColor,
          axisDirection: AxisDirection.down,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: size.width,
                  height: 0.25 * size.height,
                  decoration: BoxDecoration(
                    color: companyColor.withOpacity(0.5),
                    image: DecorationImage(
                      image: NetworkImage(
                        "https://storage.googleapis.com/bhfiles/" +
                            widget.company.logoLink,
                      ),
                      fit: BoxFit.cover,
                    ),
                    boxShadow: [
                      BoxShadow(blurRadius: 7.0, color: Colors.black)
                    ],
                  ),
                ),
                Container(
                  padding: EdgeInsets.fromLTRB(20, 10, 20, 20),
                  width: size.width,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      FittedBox(
                        child: Row(
                          children: [
                            Text(
                              widget.company.companyName,
                              style: GoogleFonts.ubuntu(
                                textStyle: TextStyle(
                                  color: companyColor,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 30,
                                ),
                              ),
                            ),
                            Text(
                              '  ${(widget.company.id != null) ? "#${widget.company.id}" : ""}',
                              style: GoogleFonts.ubuntu(
                                textStyle: TextStyle(
                                  color: Color(0xFF737373),
                                  fontSize: 12,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      SizedBox(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            vertical: 5.0,
                          ),
                          child: Text(
                            "Top tester: ${widget.company.topTester}",
                            style: GoogleFonts.aBeeZee(
                              textStyle: TextStyle(
                                color: Color(0xFF737373),
                                fontSize: 15,
                              ),
                            ),
                          ),
                        ),
                      ),
                      ButtonBar(
                        alignment: MainAxisAlignment.start,
                        children: [
                          TextButton.icon(
                            onPressed: () {},
                            icon: Icon(
                              Icons.email,
                              color: Colors.white,
                            ),
                            label: Text(
                              "Email",
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                            style: ButtonStyle(
                              backgroundColor: MaterialStateProperty.all(
                                companyColor,
                              ),
                            ),
                          ),
                          TextButton.icon(
                            onPressed: () {},
                            icon: Icon(
                              Icons.public,
                              color: Colors.white,
                            ),
                            label: Text(
                              "Site",
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                            style: ButtonStyle(
                              backgroundColor: MaterialStateProperty.all(
                                companyColor,
                              ),
                            ),
                          ),
                        ],
                      ),
                      Divider(
                        thickness: 2,
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: Column(
                    children: [
                      Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  Padding(
                                    padding: const EdgeInsets.all(5.0),
                                    child: Icon(
                                      Icons.lock_open_rounded,
                                      color: companyColor,
                                    ),
                                  ),
                                  Text(
                                    "Open Issues",
                                    style: GoogleFonts.ubuntu(
                                      textStyle: TextStyle(
                                        color: companyColor,
                                        fontSize: 17.5,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              Text("${widget.company.openIssues}")
                            ],
                          ),
                          Divider(
                            color: companyColor,
                            thickness: 2,
                          ),
                          buildOpenIssueList(size),
                        ],
                      ),
                      Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Row(
                                children: [
                                  Padding(
                                    padding: const EdgeInsets.all(5.0),
                                    child: Icon(
                                      Icons.lock_rounded,
                                      color: companyColor,
                                    ),
                                  ),
                                  Text(
                                    "Closed Issues",
                                    style: GoogleFonts.ubuntu(
                                      textStyle: TextStyle(
                                        color: companyColor,
                                        fontSize: 17.5,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              Text("${widget.company.closedIssues}")
                            ],
                          ),
                          Divider(
                            color: companyColor,
                            thickness: 2,
                          ),
                          buildClosedIssueList(size),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
