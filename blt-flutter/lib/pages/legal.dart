import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

class LegalPage extends StatelessWidget {
  const LegalPage({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
        title: Text("Terms of Service"),
        backgroundColor: Color(0xFFDC4654),
        // toolbarHeight: 0.1 * size.width,
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              padding: EdgeInsets.fromLTRB(0, 36, 0, 24),
              child: Image.asset(
                'assets/bugheist_logo.png',
                width: 169.42,
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 24),
              child: Text(
                "By using the BugHeist app, you agree to the following terms and conditions and privacy policy. ",
                style: GoogleFonts.aBeeZee(
                  textStyle: TextStyle(
                    color: Color(0xFF737373),
                  ),
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
              alignment: Alignment.centerLeft,
              child: Text(
                "Terms and Conditions",
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFFDC4654),
                    fontSize: 15,
                  ),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Container(
              height: 800,
              padding: EdgeInsets.fromLTRB(10, 0, 10, 24),
              child: FutureBuilder(
                  future: rootBundle.loadString("assets/TnC.md"),
                  builder:
                      (BuildContext context, AsyncSnapshot<String> snapshot) {
                    if (snapshot.hasData) {
                      return Markdown(
                        data: snapshot.data!,
                        padding: EdgeInsets.all(0),
                        styleSheet: MarkdownStyleSheet.fromTheme(
                          ThemeData(
                            textTheme: TextTheme(
                              bodyText2: GoogleFonts.aBeeZee(
                                textStyle: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF737373),
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    }

                    return Center(
                      child: CircularProgressIndicator(),
                    );
                  }),
            ),
            // child: Text(
            //   "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam imperdiet libero sit amet eros dictum porta. Mauris eget enim id justo mollis suscipit. Mauris nisl leo, pulvinar sed lobortis vel, dapibus quis ligula. In et diam tellus. Vestibulum ut convallis orci. Sed nec sapien at lectus ultricies tristique. Fusce sit amet congue felis. In varius pellentesque nulla, dignissim consequat ante hendrerit non. Proin sed vehicula turpis. Praesent ac libero vel urna efficitur interdum. Nam tristique placerat lorem eget condimentum. Pellentesque pellentesque lacinia pretium. Vestibulum sagittis urna ut eros eleifend rhoncus. Proin vel metus orci. Sed pellentesque nisi lacus. ",
            //   style: GoogleFonts.aBeeZee(),
            // ),

            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
              alignment: Alignment.centerLeft,
              child: Text(
                "Privacy Policy",
                style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(
                    color: Color(0xFFDC4654),
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(0, 0, 0, 36),
              child: Text(
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam imperdiet libero sit amet eros dictum porta. Mauris eget enim id justo mollis suscipit. Mauris nisl leo, pulvinar sed lobortis vel, dapibus quis ligula. In et diam tellus. Vestibulum ut convallis orci. Sed nec sapien at lectus ultricies tristique. Fusce sit amet congue felis. In varius pellentesque nulla, dignissim consequat ante hendrerit non. Proin sed vehicula turpis. Praesent ac libero vel urna efficitur interdum. Nam tristique placerat lorem eget condimentum. Pellentesque pellentesque lacinia pretium. Vestibulum sagittis urna ut eros eleifend rhoncus. Proin vel metus orci. Sed pellentesque nisi lacus. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam imperdiet libero sit amet eros dictum porta. Mauris eget enim id justo mollis suscipit. Mauris nisl leo, pulvinar sed lobortis vel, dapibus quis ligula. In et diam tellus. Vestibulum ut convallis orci. Sed nec sapien at lectus ultricies tristique. Fusce sit amet congue felis. In varius pellentesque nulla, dignissim consequat ante hendrerit non. Proin sed vehicula turpis. Praesent ac libero vel urna efficitur interdum. Nam tristique placerat lorem eget condimentum. Pellentesque pellentesque lacinia pretium. Vestibulum sagittis urna ut eros eleifend rhoncus. Proin vel metus orci. Sed pellentesque nisi lacus. ",
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
    );
  }
}
