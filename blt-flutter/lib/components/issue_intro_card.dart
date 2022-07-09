import 'package:bugheist/data/models.dart';
import 'package:bugheist/routes/routing.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class IssueCard extends StatelessWidget {
  final Results result;

  const IssueCard({Key? key, required this.result}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Card(
      margin: EdgeInsets.all(10),
      elevation: 0,
      clipBehavior: Clip.antiAlias,
      color: Color(0xFF737373).withOpacity(0.15),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
      ),
      child: InkWell(
        onTap: () {
          Navigator.pushNamed(
            context,
            RouteManager.issueDetailPage,
            arguments: result,
          );
        },
        child: Container(
          height: 0.334 * size.height,
          child: Column(
            children: <Widget>[
              Container(
                width: size.width,
                height: 0.2 * size.height,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    image: DecorationImage(
                      image: NetworkImage(result.screenshot),
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
              ),
              Container(
                width: size.width,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Container(
                      padding: const EdgeInsets.only(top: 12),
                      child: Text(
                        "Issue #" + result.id,
                        overflow: TextOverflow.ellipsis,
                        softWrap: true,
                        style: GoogleFonts.ubuntu(
                          textStyle: TextStyle(
                            color: Color(0xFFDC4654),
                            fontSize: 17.5,
                          ),
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.only(top: 8, bottom: 12),
                      child: Text(
                        result.description.replaceAll("\n", " "),
                        overflow: TextOverflow.ellipsis,
                        softWrap: true,
                        style: GoogleFonts.aBeeZee(
                          textStyle: TextStyle(
                            fontSize: 12,
                            color: Color(0xFF737373),
                          ),
                        ),
                      ),
                    ),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Text(
                            result.createdOn.toLocal().day.toString() +
                                "/" +
                                result.createdOn.toLocal().month.toString() +
                                "/" +
                                result.createdOn.toLocal().year.toString(),
                            overflow: TextOverflow.ellipsis,
                            softWrap: true,
                            style: GoogleFonts.aBeeZee(
                              textStyle: TextStyle(
                                fontSize: 10,
                                color: Color(0xFFA3A3A3),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              )
            ],
          ),
        ),
      ),
    );
  }
}
