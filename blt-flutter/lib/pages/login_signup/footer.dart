import 'package:flutter/material.dart';

class LoginFreshFooter extends StatelessWidget {
  final String text;
  final String logo;

  final Color textColor;

  final Function funFooterLogin;

  LoginFreshFooter({
    Key? key,
    required this.text,
    required this.logo,
    required this.funFooterLogin,
    required this.textColor,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Center(
        child: GestureDetector(
      onTap: funFooterLogin(),
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Row(
          mainAxisSize: MainAxisSize.max,
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Align(
              alignment: FractionalOffset.bottomCenter,
              child: Text(
                this.text + '  ',
                style: TextStyle(
                  color: this.textColor,
                  fontSize: 13,
                ),
              ),
            ),
            Image.asset(
              this.logo,
              width: 120,
            ),
          ],
        ),
      ),
    ));
  }
}
