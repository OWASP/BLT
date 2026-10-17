import './components_import.dart';

class BugHuntListTile extends StatelessWidget {
  const BugHuntListTile({super.key, required this.hunt});
  final BugHunt hunt;

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return Card(
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
            RouteManager.bugHuntDescPageHunt,
            arguments: hunt,
          );
        },
        child: Container(
          height: 0.205 * size.height,
          child: Padding(
            padding: const EdgeInsets.all(12.0),
            child: Row(
              children: <Widget>[
                Expanded(
                  flex: 1,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: CachedNetworkImage(
                      imageUrl:
                          GeneralEndPoints.apiBaseUrl + "media/" + hunt.logo!,
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
                Expanded(
                  flex: 2,
                  child: Padding(
                    padding: const EdgeInsets.only(
                      top: 5.0,
                      bottom: 5.0,
                      left: 12.0,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          hunt.name,
                          overflow: TextOverflow.ellipsis,
                          softWrap: true,
                          style: GoogleFonts.ubuntu(
                            textStyle: TextStyle(
                              color: Color(0xFFDC4654),
                              fontSize: 18,
                            ),
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: size.height * 0.01),
                        Row(
                          children: [
                            Icon(
                              Icons.calendar_month,
                              color: Color.fromARGB(255, 70, 70, 70),
                            ),
                            SizedBox(width: 5),
                            Text(
                              'Starts on : ${monthsInYear[hunt.startsOn?.month]} ${hunt.startsOn?.day} ${hunt.startsOn?.year}',
                              overflow: TextOverflow.ellipsis,
                              softWrap: true,
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF737373),
                                ),
                              ),
                            ),
                            // Text('${hunt.startsOn}'),
                          ],
                        ),
                        SizedBox(height: size.height * 0.006),
                        Row(
                          children: [
                            Icon(
                              Icons.calendar_month,
                              color: Color.fromARGB(255, 70, 70, 70),
                            ),
                            SizedBox(width: 5),
                            Text(
                              'Ends on : ${monthsInYear[hunt.endsOn?.month]} ${hunt.endsOn?.day} ${hunt.endsOn?.year}',
                              overflow: TextOverflow.ellipsis,
                              softWrap: true,
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF737373),
                                ),
                              ),
                            ),
                            // Text('${hunt.startsOn}'),
                          ],
                        ),
                        SizedBox(height: size.height * 0.003),
                        Row(
                          children: [
                            Icon(
                              Icons.link_outlined,
                              color: Color.fromARGB(255, 70, 70, 70),
                            ),
                            SizedBox(width: 5),
                            GestureDetector(
                              onTap: () {
                                launchUrl(Uri.parse(hunt.url));
                              },
                              child: Text(
                                '${hunt.url}',
                                overflow: TextOverflow.ellipsis,
                                softWrap: true,
                                style: GoogleFonts.aBeeZee(
                                  textStyle: TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.blue[500],
                                  ),
                                ),
                              ),
                            ),
                            // Text('${hunt.startsOn}'),
                          ],
                        ),
                        SizedBox(height: size.height * 0.003),
                        Row(
                          children: [
                            Text(
                              ' \$ ',
                              overflow: TextOverflow.ellipsis,
                              softWrap: true,
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                  color: Color.fromARGB(255, 70, 70, 70),
                                ),
                              ),
                            ),
                            SizedBox(width: 5),
                            Text(
                              '${hunt.prize}',
                              overflow: TextOverflow.ellipsis,
                              softWrap: true,
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF737373),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                )
              ],
            ),
          ),
        ),
      ),
    );
  }
}
