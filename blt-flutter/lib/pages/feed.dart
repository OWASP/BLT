import 'package:bugheist/global/variables.dart';
import 'package:bugheist/util/api/user_api.dart';
import 'package:flutter/material.dart';

class Feed extends StatefulWidget {
  const Feed({Key? key}) : super(key: key);

  @override
  _FeedState createState() => _FeedState();
}

class _FeedState extends State<Feed> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: InkWell(
          onTap: () {
            UserApiClient.getUserInfo(currentUser!);
          },
          child: Text('Feed Page'),
        ),
      ),
    );
  }
}
