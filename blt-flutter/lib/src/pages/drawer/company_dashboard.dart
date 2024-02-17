import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';

class CompanyDashBoardPage extends ConsumerStatefulWidget {
  const CompanyDashBoardPage({Key? key}) : super(key: key);

  @override
  ConsumerState<ConsumerStatefulWidget> createState() =>
      _CompanyDashBoardPageState();
}

class _CompanyDashBoardPageState extends ConsumerState<CompanyDashBoardPage> {
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
          1 > 0
              ? AppLocalizations.of(context)!.unableToGetInfo
              : AppLocalizations.of(context)!.noOpenIssues,
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
    companyColor = Color(0xFFDC4654);
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Scaffold(
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        backgroundColor: companyColor,
        child: Icon(
          Icons.add,
        ),
      ),
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
        title: Text("BLT"),
        actions: [
          IconButton(
            onPressed: () {},
            icon: Icon(
              Icons.edit,
            ),
          )
        ],
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
          color: Colors.redAccent,
          axisDirection: AxisDirection.down,
          child: SingleChildScrollView(
            child: Column(
              children: [
                Container(
                  width: size.width,
                  height: 0.25 * size.height,
                  decoration: BoxDecoration(
                    color: companyColor.withOpacity(0.5),
                    image: DecorationImage(
                      image: AssetImage("assets/logo.png"),
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
                              "BLT",
                              style: GoogleFonts.ubuntu(
                                textStyle: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 30,
                                  color: companyColor,
                                ),
                              ),
                            ),
                            Text(
                              '#9999',
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
                      Container(
                        child: Column(
                          children: [
                            Column(
                              children: [
                                Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceBetween,
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
                                          AppLocalizations.of(context)!
                                              .activeHunts,
                                          style: GoogleFonts.ubuntu(
                                            textStyle: TextStyle(
                                              fontSize: 17.5,
                                              color: companyColor,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    Text("0")
                                  ],
                                ),
                                Divider(
                                  thickness: 2,
                                  color: companyColor,
                                ),
                                buildOpenIssueList(size),
                              ],
                            ),
                          ],
                        ),
                      ),
                      Container(
                        child: Column(
                          children: [
                            Column(
                              children: [
                                Row(
                                  mainAxisAlignment:
                                      MainAxisAlignment.spaceBetween,
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
                                          AppLocalizations.of(context)!.payouts,
                                          style: GoogleFonts.ubuntu(
                                            textStyle: TextStyle(
                                              fontSize: 17.5,
                                              color: companyColor,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    Text("0")
                                  ],
                                ),
                                Divider(
                                  thickness: 2,
                                  color: companyColor,
                                ),
                                buildOpenIssueList(size),
                              ],
                            ),
                          ],
                        ),
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
