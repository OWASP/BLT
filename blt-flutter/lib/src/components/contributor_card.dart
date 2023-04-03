import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

class ContributorCard extends StatelessWidget {
  final Map<String, String> contributor;

  const ContributorCard({Key? key, required this.contributor})
      : super(key: key);

  @override
  Widget build(BuildContext context) {
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
                height: 480.0,
                child: Stack(
                  children: [
                    Column(
                      children: [
                        Container(
                          decoration: BoxDecoration(
                            color: Color(0xFFDC4654),
                            borderRadius: BorderRadius.only(
                              topLeft: Radius.circular(20),
                              topRight: Radius.circular(20),
                            ),
                          ),
                          height: 80,
                        ),
                        Container(
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.only(
                              bottomLeft: Radius.circular(20),
                              bottomRight: Radius.circular(20),
                            ),
                          ),
                          height: 400,
                        ),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          height: 45.0,
                        ),
                        Row(
                          children: [
                            SizedBox(
                              width: 32.0,
                            ),
                            CircleAvatar(
                              backgroundColor: Colors.white,
                              radius: 35.0,
                              child: Hero(
                                tag: "image${contributor["id"]}",
                                child: CircleAvatar(
                                  radius: 32,
                                  backgroundImage:
                                      NetworkImage(contributor["img"]!),
                                ),
                              ),
                            ),
                            SizedBox(
                              width: 16.0,
                            ),
                            Container(
                              height: 64.0,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  SizedBox(
                                    height: 8.0,
                                  ),
                                  Hero(
                                    tag: "name${contributor["id"]}",
                                    child: Material(
                                      color: Colors.transparent,
                                      child: Text(
                                        contributor["name"]!,
                                        style: GoogleFonts.aBeeZee(
                                          textStyle: TextStyle(
                                            color: Colors.white,
                                          ),
                                          fontWeight: FontWeight.bold,
                                          fontSize: 18.0,
                                        ),
                                      ),
                                    ),
                                  ),
                                  Spacer(),
                                  Text(
                                    contributor["repository"]!,
                                    style: GoogleFonts.aBeeZee(
                                      textStyle: TextStyle(
                                        color: Color(0xFF737373),
                                      ),
                                      fontWeight: FontWeight.bold,
                                      fontSize: 14.0,
                                    ),
                                  ),
                                  SizedBox(
                                    height: 8.0,
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        SizedBox(
                          height: 32.0,
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 32.0),
                          child: Text(
                            contributor["short_description"]!,
                            style: GoogleFonts.aBeeZee(
                              textStyle: TextStyle(
                                color: Color(0xFF737373),
                              ),
                              fontSize: 14.0,
                            ),
                          ),
                        ),
                        SizedBox(
                          height: 16.0,
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 32.0),
                          child: Text(
                            contributor["long_description"]!,
                            style: GoogleFonts.aBeeZee(
                              textStyle: TextStyle(
                                color: Color(0xFF737373),
                              ),
                              fontSize: 14.0,
                            ),
                          ),
                        ),
                        SizedBox(
                          height: 16.0,
                        ),
                        Row(
                          children: [
                            SizedBox(
                              width: 32.0,
                            ),
                            Icon(
                              Icons.location_pin,
                              color: Color(0xFF737373),
                              size: 28.0,
                            ),
                            SizedBox(
                              width: 4.0,
                            ),
                            Text(
                              contributor["location"]!,
                              style: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  color: Color(0xFF737373),
                                ),
                                fontSize: 14.0,
                              ),
                            ),
                          ],
                        ),
                        Spacer(),
                        Row(
                          children: [
                            SizedBox(
                              width: 24.0,
                            ),
                            IconButton(
                              onPressed: () async {
                                Uri site = Uri.parse(contributor["twitter"]!);
                                try {
                                  await launchUrl(site,
                                      mode: LaunchMode.externalApplication);
                                } catch (e) {}
                              },
                              icon: SvgPicture.asset(
                                "assets/twitter.svg",
                                height: 64.0,
                              ),
                            ),
                            IconButton(
                              onPressed: () async {
                                Uri site = Uri.parse(contributor["linkedin"]!);
                                try {
                                  await launchUrl(site,
                                      mode: LaunchMode.externalApplication);
                                } catch (e) {}
                              },
                              icon: SvgPicture.asset(
                                "assets/linkedin.svg",
                                height: 64.0,
                              ),
                            ),
                            IconButton(
                              onPressed: () async {
                                Uri site = Uri.parse(contributor["website"]!);
                                try {
                                  await launchUrl(site,
                                      mode: LaunchMode.externalApplication);
                                } catch (e) {}
                              },
                              icon: SvgPicture.asset(
                                "assets/website.svg",
                                height: 64.0,
                              ),
                            ),
                            IconButton(
                              onPressed: () async {
                                await Clipboard.setData(ClipboardData(text: contributor["bch_addr"]!));
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text("Bitcoin cash address copied to clipboard!"),
                                  ),
                                );
                              },
                              icon: SvgPicture.asset(
                                "assets/bitcoin.svg",
                                height: 64.0,
                              ),
                            ),
                          ],
                        ),
                        SizedBox(
                          height: 32.0,
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
