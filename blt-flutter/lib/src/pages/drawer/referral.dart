import 'package:blt/src/pages/pages_import.dart';
import 'package:flutter/material.dart';

/// Page for allowing users to send referrals to their friends.
class ReferralPage extends StatefulWidget {
  const ReferralPage({Key? key}) : super(key: key);

  @override
  State<ReferralPage> createState() => _ReferralPageState();
}

class _ReferralPageState extends State<ReferralPage> {
  late TextEditingController _emailController;

  @override
  void initState() {
    super.initState();
    _emailController = TextEditingController();
  }

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

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
        title: Text(AppLocalizations.of(context)!.invite),
        backgroundColor:
            isDarkMode ? Color.fromRGBO(58, 21, 31, 1) : Color(0xFFDC4654),
      ),
      body: SingleChildScrollView(
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: 20),
          width: size.width,
          color: Theme.of(context).canvasColor,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
                    child: Text(
                      AppLocalizations.of(context)!.inviteYourFriends,
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
                      AppLocalizations.of(context)!.inviteFriendsDescription,
                      style: GoogleFonts.aBeeZee(
                        textStyle: TextStyle(
                          color: Color(0xFF737373),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              Container(
                width: size.width,
                child: Column(
                  children: [
                    Icon(
                      Icons.group,
                      color: isDarkMode
                          ? Color.fromRGBO(126, 33, 58, 1)
                          : Color(0xFFDC4654),
                      size: 250,
                    ),
                    Container(
                      padding: EdgeInsets.symmetric(vertical: 36),
                      width: size.width,
                      child: TextFormField(
                        controller: _emailController,
                        decoration: InputDecoration(
                          hintText: AppLocalizations.of(context)!.email,
                          prefixIcon: Icon(Icons.mail),
                          filled: true,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10.0),
                          ),
                          fillColor: Colors.white.withOpacity(0.35),
                        ),
                      ),
                    ),
                    Container(
                      margin: EdgeInsets.only(bottom: 20),
                      width: size.width,
                      height: 50,
                      child: TextButton(
                        onPressed: () async {},
                        child: Text(
                          AppLocalizations.of(context)!.invite,
                          style: GoogleFonts.ubuntu(
                            textStyle: TextStyle(
                              color: Colors.white,
                              fontSize: 17.5,
                            ),
                          ),
                        ),
                        style: ButtonStyle(
                          elevation: WidgetStateProperty.all(8),
                          shadowColor: WidgetStateProperty.all(
                            Colors.black.withOpacity(0.5),
                          ),
                          shape:
                              WidgetStateProperty.all<RoundedRectangleBorder>(
                            RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(15.0),
                            ),
                          ),
                          backgroundColor: WidgetStateProperty.all(
                            isDarkMode
                                ? Color.fromRGBO(126, 33, 58, 1)
                                : Color(0xFFDC4654),
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
      ),
    );
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }
}
