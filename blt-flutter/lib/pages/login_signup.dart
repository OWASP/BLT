import 'dart:async';

import 'package:bugheist/providers/auth.dart';
import 'package:bugheist/providers/user_provider.dart';
import 'package:bugheist/routes/routing.dart';
import 'package:flutter/material.dart';
import 'package:bugheist/config/login_signup_structure.dart';
import 'package:bugheist/pages/login_signup/fresh.dart';
import 'package:bugheist/pages/login_signup/reset_password.dart';
import 'package:bugheist/pages/login_signup/signup.dart';
import 'package:bugheist/pages/login_signup/user_password.dart';
import 'package:bugheist/data/login_model.dart';
import 'package:provider/provider.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';
import '../providers/auth.dart';

class LoginSignUp extends StatefulWidget {
  const LoginSignUp({Key? key}) : super(key: key);

  @override
  LoginSignUpState createState() => LoginSignUpState();
}

class LoginSignUpState extends State<LoginSignUp> {
  late StreamSubscription _intentDataStreamSubscription;
  late List<SharedMediaFile> _sharedFiles;
  //late String _sharedText;
  final _messangerKey = GlobalKey<ScaffoldMessengerState>();
  @override
  void initState() {
    super.initState();
    // For sharing images coming from outside the app while the app is in the memory
    _intentDataStreamSubscription = ReceiveSharingIntent.getMediaStream()
        .listen((List<SharedMediaFile> value) {
      setState(() {
        print(_sharedFiles);
        _sharedFiles = value;
      });
    }, onError: (err) {
      print("getIntentDataStream error: $err");
    });

    // For sharing images coming from outside the app while the app is closed
    ReceiveSharingIntent.getInitialMedia().then((List<SharedMediaFile> value) {
      setState(() {
        _sharedFiles = value;
      });
    });

    // For sharing or opening urls/text coming from outside the app while the app is in the memory
    _intentDataStreamSubscription =
        ReceiveSharingIntent.getTextStream().listen((String value) {
      setState(() {
        print('detected a link here 1');
        print(value);
        //_sharedText = value;
      });
    }, onError: (err) {
      print("getLinkStream error: $err");
    });

    // For sharing or opening urls/text coming from outside the app while the app is closed
    ReceiveSharingIntent.getInitialText().then((value) {
      setState(() {
        print('detected text here:');
        print(value);
        //_sharedText = value;
      });
    });
  }

  @override
  void dispose() {
    _intentDataStreamSubscription.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    //Future<User> getUserData() => UserPreferences().getUser();
    //AuthProvider auth = Provider.of<AuthProvider>(context);

    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => UserProvider()),
      ],
      child: MaterialApp(
        scaffoldMessengerKey: _messangerKey,
        debugShowCheckedModeBanner: false,
        onGenerateRoute: RouteManager.generateRoute,
        title: 'BugHeist',
        theme: ThemeData(
          primarySwatch: Colors.red,
          primaryColor: Colors.white,
          visualDensity: VisualDensity.adaptivePlatformDensity,
          primaryTextTheme: TextTheme(
            headline1: TextStyle(
                fontSize: 72.0,
                fontWeight: FontWeight.bold,
                color: Colors.black),
            headline6: TextStyle(color: Colors.black),
            button: TextStyle(
              color: Colors.black,
            ),
          ),
        ),
        home: Scaffold(
          body: buildLoginFresh(),
        ),
      ),
    );
  }

  LoginFresh buildLoginFresh() {
    List<LoginFreshTypeLoginModel> listLogin = [
      LoginFreshTypeLoginModel(
          callFunction: (BuildContext _buildContext) {},
          logo: TypeLogo.facebook),
      LoginFreshTypeLoginModel(
        callFunction: (BuildContext _buildContext) {},
        logo: TypeLogo.google,
      ),
      LoginFreshTypeLoginModel(
          callFunction: (BuildContext _buildContext) {}, logo: TypeLogo.apple),
      LoginFreshTypeLoginModel(
        callFunction: (BuildContext _buildContext) {
          Navigator.of(_buildContext).push(MaterialPageRoute(
            builder: (_buildContext) => widgetLoginFreshUserAndPassword(),
          ));
        },
        logo: TypeLogo.userPassword,
      ),
    ];

    return LoginFresh(
      pathLogo: 'assets/logo_white.png',
      isExploreApp: true,
      functionExploreApp: () {},
      isFooter: false,
      widgetFooter: this.widgetFooter(),
      typeLoginModel: listLogin,
      isSignUp: true,
      widgetSignUp: this.widgetLoginFreshSignUp(),
      backgroundColor: Color(0xFFDC4654),
      cardColor: Color(0xFFF3F3F5),
      keyWord: LoginFreshWords(),
      textColor: Color(0xFF0F2E48),
    );
  }

  Widget widgetLoginFreshUserAndPassword() {
    //AuthProvider auth = Provider.of<AuthProvider>(context);

    return LoginFreshUserAndPassword(
      callLogin: (
        BuildContext _context,
        Function isRequest,
      ) {
        isRequest(true);
        Future.delayed(
          Duration(seconds: 4),
          () {
            isRequest(false);
          },
        );
      },
      logo: 'assets/logo_white.png',
      loginFreshWords: LoginFreshWords(),
      isFooter: true,
      widgetFooter: this.widgetFooter(),
      isResetPassword: true,
      widgetResetPassword: this.widgetResetPassword(),
      isSignUp: true,
      signUp: this.widgetLoginFreshSignUp(),
      textColor: Color(0xFF0F2E48),
      backgroundColor: Color(0xFFE7004C),
    );
  }

  Widget widgetResetPassword() {
    return LoginFreshResetPassword(
      logo: 'assets/logo_white.png',
      funResetPassword:
          (BuildContext _context, Function isRequest, String email) {
        isRequest(true);

        Future.delayed(Duration(seconds: 2), () {
          isRequest(false);
        });
      },
      loginFreshWords: LoginFreshWords(),
      isFooter: true,
      widgetFooter: this.widgetFooter(),
      textColor: Color(0xFF0F2E48),
      backgroundColor: Color(0xFFE7004C),
    );
  }

  Widget widgetFooter() {
    return Container();
    // return Row(
    //   children: <Widget>[
    //     Expanded(
    //       child: LoginFreshFooter(
    //         logo: 'assets/logo.png',
    //         text: 'BugHeist',
    //         textColor: Color(0xFF42A5F5),
    //         funFooterLogin: () {},
    //       ),
    //     ),
    //   ],
    // );
    // return LoginFreshFooter(
    //   logo: 'assets/logo.png',
    //   text: 'BugHeist',
    //   textColor: Color(0xFF42A5F5),
    //   funFooterLogin: () {},
    // );
  }

  Widget widgetLoginFreshSignUp() {
    return LoginFreshSignUp(
      isFooter: true,
      widgetFooter: this.widgetFooter(),
      loginFreshWords: LoginFreshWords(),
      logo: 'assets/logo_white.png',
      funSignUp: (BuildContext _context, Function isRequest) {
        isRequest(true);
        Future.delayed(
          Duration(seconds: 4),
          () {
            isRequest(false);
          },
        );
      },
      textColor: Color(0xFF0F2E48),
      backgroundColor: Color(0xFFE7004C),
    );
  }
}
