import 'package:flutter/material.dart';

class LoadingLoginFresh extends StatelessWidget {
  final String textLoading;
  final Color colorText;
  final double elevation;

  final Color backgroundColor;

  LoadingLoginFresh(
      {this.textLoading, this.colorText, this.backgroundColor, this.elevation});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SizedBox(
        height: 80,
        width: 150,
        child: Card(
          elevation: this.elevation,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10.0),
          ),
          color: Color(0xFFF3F3F5),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.center,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              new Center(
                child: new SizedBox(
                  height: 30.0,
                  width: 30.0,
                  child: new CircularProgressIndicator(
                    value: null,
                    strokeWidth: 2.0,
                    valueColor:
                        AlwaysStoppedAnimation<Color>(this.backgroundColor),
                  ),
                ),
              ),
              new Container(
                margin: const EdgeInsets.only(top: 5.0),
                child: new Center(
                  child: new Text(
                    this.textLoading,
                    style: new TextStyle(color: this.colorText),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
