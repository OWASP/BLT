import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class SocialPage extends ConsumerStatefulWidget{
  const SocialPage({Key? key}) : super(key: key);

  @override
  _SocialPageState createState() => _SocialPageState();
}

class _SocialPageState extends ConsumerState<SocialPage> {
late InAppWebViewController webViewController;
late PullToRefreshController refreshController;


  @override
  Widget build(BuildContext context){
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
        title: Text("Social"),
        backgroundColor: Color(0xFFDC4654),
      ),
      body: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(child: InAppWebView(
                initialUrlRequest: URLRequest(url: Uri.parse("https://twitter.com/OWASP")),
                shouldOverrideUrlLoading: (controller, navigationAction) async{
                  return NavigationActionPolicy.CANCEL;
                },
              )),
            ],
        )
      );
    
  }
}