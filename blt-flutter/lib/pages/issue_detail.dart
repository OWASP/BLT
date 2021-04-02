import 'package:flutter/material.dart';
import '../data/models.dart';

class ArticleOnePage extends StatelessWidget {
  static final String path = "lib/src/pages/blog/article1.dart";
  final Results issue;

  ArticleOnePage({
    required this.issue,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SingleChildScrollView(
        child: Column(
          children: <Widget>[
            Stack(
              children: <Widget>[
                SafeArea(
                  child: Container(
                    height: 300,
                    width: double.infinity,
                    child: Hero(
                      tag: issue.screenshot,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          image: DecorationImage(
                            image: NetworkImage(
                              issue.screenshot,
                            ),
                            fit: BoxFit.fitWidth,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                Positioned(
                  top: 15,
                  child: SafeArea(
                    child: RawMaterialButton(
                      onPressed: () => Navigator.pop(context),
                      elevation: 5,
                      fillColor: Colors.white,
                      child: Icon(
                        Icons.arrow_left_rounded,
                        size: 50,
                      ),
                      shape: CircleBorder(),
                    ),
                  ),
                ),
                // Positioned(
                //   bottom: 20.0,
                //   left: 20.0,
                //   right: 20.0,
                //   child: Row(
                //     children: <Widget>[
                //       Icon(
                //         Icons.slideshow,
                //         color: Colors.white,
                //       ),
                //       SizedBox(width: 10.0),
                //       Text(
                //         "Technology",
                //         style: TextStyle(color: Colors.white),
                //       )
                //     ],
                //   ),
                // )
              ],
            ),
            Padding(
              padding:
                  const EdgeInsets.only(left: 16.0, right: 16.0, bottom: 16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  // Row(
                  //   children: <Widget>[
                  //     Expanded(
                  //       child: Text("Oct 21, 2017"),
                  //     ),
                  //     IconButton(
                  //       icon: Icon(Icons.share),
                  //       onPressed: () {},
                  //     )
                  //   ],
                  // ),
                  // Text(
                  //   "testing",
                  // ),
                  Divider(),
                  SizedBox(
                    height: 10.0,
                  ),
                  // Row(
                  //   children: <Widget>[
                  //     Icon(Icons.favorite_border),
                  //     SizedBox(
                  //       width: 5.0,
                  //     ),
                  //     Text("20.2k"),
                  //     SizedBox(
                  //       width: 16.0,
                  //     ),
                  //     Icon(Icons.comment),
                  //     SizedBox(
                  //       width: 5.0,
                  //     ),
                  //     Text("2.2k"),
                  //   ],
                  // ),
                  // SizedBox(
                  //   height: 10.0,
                  // ),
                  Text(
                    issue.description,
                    textAlign: TextAlign.justify,
                  )
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
