import 'package:blt/src/pages/pages_import.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

/// The Landing page for unauthenticated users, or if a
/// user wants to try the guest mode of the app.
//ignore: must_be_immutable
class WelcomePage extends StatefulWidget {
  String? snackBarMessage;
  WelcomePage({Key? key, this.snackBarMessage}) : super(key: key);

  @override
  State<WelcomePage> createState() => _WelcomePageState();
}

class _WelcomePageState extends State<WelcomePage> {
  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (widget.snackBarMessage != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(widget.snackBarMessage!)),
        );
        widget.snackBarMessage = null;
      }
    });

    final Size size = MediaQuery.of(context).size;

    return Scaffold(
      body: Material(
        color: Colors.transparent,
        child: Stack(
          children: [
            buildBackground(size),
            Positioned(
              bottom: 0,
              child: Container(
                height: size.height * 0.5,
                width: size.width,
                decoration: BoxDecoration(
                  color: isDarkMode
                      ? Color.fromRGBO(42, 38, 38, 1)
                      : Theme.of(context).canvasColor,
                  boxShadow: [
                    BoxShadow(
                        spreadRadius: 10,
                        color: Colors.black.withOpacity(0.1),
                        blurRadius: 50)
                  ],
                  borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(50),
                      topRight: Radius.circular(50)),
                ),
                child: Padding(
                  padding: EdgeInsets.all(20),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        height: size.height * 0.03,
                      ),
                      buildLoginButton(size),
                      buildExploreButton(size),
                      buildSignUpRow(),
                      SizedBox(
                        height: size.height * 0.12,
                      ),
                      buildLanguageDropdown(context),
                    ],
                  ),
                ),
              ),
            )
          ],
        ),
      ),
    );
  }

  Widget buildBackground(Size size) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: size.width,
      height: size.height,
      color: isDarkMode ? Color.fromRGBO(34, 22, 23, 1) : Color(0xFFDC4654),
      child: Column(
        children: [
          SizedBox(
            width: size.width,
            height: size.height * 0.4,
            child: Padding(
              padding: EdgeInsets.symmetric(
                  horizontal: 0.15 * size.width, vertical: 0.1 * size.height),
              child: Center(
                child: SvgPicture.asset('assets/logo_white.svg',
                    fit: BoxFit.contain, height: 192.0),
              ),
            ),
          ),
          SizedBox(width: size.width, height: size.height * 0.6),
        ],
      ),
    );
  }

  Widget buildLoginButton(Size size) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 14),
      child: SizedBox(
        height: 60,
        width: 0.8 * size.width,
        child: TextButton.icon(
          onPressed: () =>
              Navigator.of(context).pushNamed(RouteManager.loginPage),
          icon: Icon(Icons.person, color: Colors.white),
          label: Text(AppLocalizations.of(context)!.login,
              style: GoogleFonts.ubuntu(
                  textStyle: TextStyle(color: Colors.white, fontSize: 20))),
          style: ButtonStyle(
            elevation: MaterialStateProperty.all(12),
            shadowColor:
                MaterialStateProperty.all(Colors.black.withOpacity(0.5)),
            shape: MaterialStateProperty.all<RoundedRectangleBorder>(
                RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15.0))),
            backgroundColor: MaterialStateProperty.all(Color(0xFFDC4654)),
          ),
        ),
      ),
    );
  }

  Widget buildExploreButton(Size size) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Consumer(
      builder: (BuildContext context, ref, Widget? child) {
        return SizedBox(
          height: 60,
          width: 0.8 * size.width,
          child: TextButton(
            onPressed: () async {
              await ref.read(authStateNotifier.notifier).guestLogin();
              Navigator.of(context).pushNamed(RouteManager.homePage);
            },
            child: Text(AppLocalizations.of(context)!.exploreAnonymously,
                style: GoogleFonts.ubuntu(
                    textStyle:
                        TextStyle(color: Color(0xFF737373), fontSize: 20))),
            style: ButtonStyle(
              elevation: MaterialStateProperty.all(12),
              shadowColor:
                  MaterialStateProperty.all(Colors.black.withOpacity(0.5)),
              shape: MaterialStateProperty.all<RoundedRectangleBorder>(
                RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(15.0),
                    side: BorderSide(color: Color(0xFF737373))),
              ),
              backgroundColor: MaterialStateProperty.all(
                isDarkMode
                    ? Color.fromRGBO(43, 42, 42, 1)
                    : Theme.of(context).canvasColor,
              ),
            ),
          ),
        );
      },
    );
  }

  Widget buildSignUpRow() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(AppLocalizations.of(context)!.newUserQuestion),
        TextButton(
            onPressed: () =>
                Navigator.of(context).pushNamed(RouteManager.signupPage),
            child: Text(AppLocalizations.of(context)!.signUp)),
      ],
    );
  }

  Widget buildLanguageDropdown(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Consumer(
      builder: (BuildContext context, WidgetRef ref, Widget? child) {
        final currentLanguage = ref.watch(languageProvider);
        return Container(
          padding: EdgeInsets.symmetric(horizontal: 20, vertical: 5),
          decoration: BoxDecoration(
            color: isDarkMode
                ? Color.fromRGBO(43, 42, 42, 1)
                : Theme.of(context).canvasColor.withOpacity(0.8),
            borderRadius: BorderRadius.circular(15),
            border: Border.all(color: Colors.grey.shade300),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: currentLanguage,
              icon: Icon(Icons.language, color: Colors.grey.shade600),
              items: [
                DropdownMenuItem(
                    value: 'en',
                    child: Row(children: [
                      Icon(Icons.flag, color: Colors.grey.shade600),
                      SizedBox(width: 8),
                      Text(
                        'English',
                        style: TextStyle(
                            color: isDarkMode ? Colors.white : Colors.black),
                      )
                    ])),
                DropdownMenuItem(
                    value: 'es',
                    child: Row(children: [
                      Icon(Icons.flag, color: Colors.grey.shade600),
                      SizedBox(width: 8),
                      Text(
                        'Español',
                        style: TextStyle(
                            color: isDarkMode ? Colors.white : Colors.black),
                      )
                    ])),
                DropdownMenuItem(
                    value: 'de',
                    child: Row(children: [
                      Icon(Icons.flag, color: Colors.grey.shade600),
                      SizedBox(width: 8),
                      Text(
                        'German',
                        style: TextStyle(
                            color: isDarkMode ? Colors.white : Colors.black),
                      )
                    ])),
                DropdownMenuItem(
                    value: 'hi',
                    child: Row(children: [
                      Icon(Icons.flag, color: Colors.grey.shade600),
                      SizedBox(width: 8),
                      Text(
                        'Hindi',
                        style: TextStyle(
                            color: isDarkMode ? Colors.white : Colors.black),
                      )
                    ])),
                DropdownMenuItem(
                    value: 'pt',
                    child: Row(children: [
                      Icon(Icons.flag, color: Colors.grey.shade600),
                      SizedBox(width: 8),
                      Text(
                        'Portuguese',
                        style: TextStyle(
                            color: isDarkMode ? Colors.white : Colors.black),
                      )
                    ])),
                DropdownMenuItem(
                    value: 'fr',
                    child: Row(children: [
                      Icon(Icons.flag, color: Colors.grey.shade600),
                      SizedBox(width: 8),
                      Text(
                        'french',
                        style: TextStyle(
                            color: isDarkMode ? Colors.white : Colors.black),
                      )
                    ])),
                DropdownMenuItem(
                    value: 'ja',
                    child: Row(children: [
                      Icon(Icons.flag, color: Colors.grey.shade600),
                      SizedBox(width: 8),
                      Text(
                        'Japanese',
                        style: TextStyle(
                            color: isDarkMode ? Colors.white : Colors.black),
                      )
                    ])),
                DropdownMenuItem(
                    value: 'zh',
                    child: Row(children: [
                      Icon(Icons.flag, color: Colors.grey.shade600),
                      SizedBox(width: 8),
                      Text(
                        'Chinese',
                        style: TextStyle(
                            color: isDarkMode ? Colors.white : Colors.black),
                      )
                    ])),
              ],
              onChanged: (newValue) =>
                  ref.read(languageProvider.notifier).changeLanguage(newValue!),
              dropdownColor: Theme.of(context).canvasColor,
              style: TextStyle(color: Colors.black, fontSize: 16),
            ),
          ),
        );
      },
    );
  }
}
